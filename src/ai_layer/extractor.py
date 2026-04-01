import os
import json
import logging
import time
from typing import List
from pydantic import BaseModel, Field

# google-genai SDK
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# --- PYDANTIC SCHEMAS ---
class ImageReference(BaseModel):
    image_filename: str = Field(description="The exact filename of the image from the provided manifest (e.g. 'visual_page_3_img_1.png')")
    description: str = Field(description="Brief AI-generated description of what the image shows")
    relevance: str = Field(description="Why this image is relevant to the observation")

class Observation(BaseModel):
    area_name: str = Field(description="Name of the physical area, room, or system being inspected")
    visual_findings: List[str] = Field(description="List of text findings from the visual report")
    thermal_findings: List[str] = Field(description="List of findings or temperature anomalies from the thermal report")
    associated_images: List[ImageReference] = Field(description="Relevant image filenames belonging to this specific area")

class ProjectInfo(BaseModel):
    client_name: str = Field(description="Name of the client or unavailable")
    date: str = Field(description="Date of the inspection or unavailable")
    address: str = Field(description="Address of the property or unavailable")

class DetailedDiagnosticReport(BaseModel):
    project_info: ProjectInfo = Field(description="Extracted metadata like Client Name, Date, Address")
    observations: List[Observation] = Field(description="List of all area-wise and component observations extracted")
    missing_info: List[str] = Field(description="Information required for a DDR that appears to be missing or incomplete")


def extract_structured_data(api_key: str, extracted_json_path: str, image_dir: str, output_json: str) -> bool:
    """
    Reads the Phase 1 JSON and the exported images,
    pushes them as a multimodal context to Gemini 1.5 Pro,
    and requests structured JSON mapped to our universal Pydantic schema.
    """
    
    if not os.path.exists(extracted_json_path):
        logger.error(f"Cannot find Phase 1 data at {extracted_json_path}")
        return False
        
    client = genai.Client(api_key=api_key)
    
    try:
        with open(extracted_json_path, 'r', encoding='utf-8') as f:
            phase1_data = json.load(f)
            
        logger.info("Loaded Phase 1 JSON. Preparing Multimodal Context...")
        
        # 1. Gather all unique image paths
        # To avoid passing thousands of irrelevant icons if they exist, 
        # we just list what we have, upload them to Gemini, and give it the manifest.
        all_image_paths = []
        for dataset in phase1_data.values():
            for page in dataset:
                all_image_paths.extend(page.get("images", []))
                
        # Optional safeguard: Filter out very small images (likely icons/logos)
        # 15 KB is a safe threshold; actual inspection photos will be much larger.
        valid_image_paths = []
        for img_path in all_image_paths:
            if os.path.exists(img_path):
                file_size_kb = os.path.getsize(img_path) / 1024
                if file_size_kb > 15.0:
                    valid_image_paths.append(img_path)
        
        logger.info(f"Filtered down to {len(valid_image_paths)} valid inspection photos. Processing locally...")
            
        # 2. Build Text Prompt with Inline Downsampled Images
        # We completely bypass the slow `client.files.upload` process. Instead, we insert highly compressed 
        # PIL Images directly into the prompt sequence. The SDK will bundle them locally into a single payload.
        from PIL import Image
        
        # Start our multimodal array
        contents = []
        
        # Add the system instructions first
        prompt_instruction = f"""
        You are a Senior Diagnostic Inspector and AI Analyzer. 
        You have been given the raw text contents of two inspection documents (Visual and Thermal).
        You will see images attached inline shortly after this text. Each image is labelled with its exact filename.
        
        RAW TEXT DATA MAPPING:
        {json.dumps(phase1_data, indent=2)}
        
        INSTRUCTIONS:
        1. Analyze all text and all uploaded photos thoroughly.
        2. Identify each distinct "Area" or "Component" (e.g. Master Bedroom, Living Room, HVAC Unit).
        3. Extract the visual anomalies and thermal readings/anomalies for each Area.
        4. Match the exact image filenames strictly back to the Area observations they depict (ignoring irrelevant templates).
        5. Map everything into the strict JSON schema provided.
        """
        contents.append(prompt_instruction)
        
        for img_path in valid_image_paths:
            try:
                img = Image.open(img_path)
                # Resizing drops the payload size drastically (50KB instead of 2MB per image) 
                # This ensures we easily stay under the 20MB single-request HTTP payload limit!
                img.thumbnail((400, 400))
                
                # Append the image and its textual name binding inline
                contents.append(img)
                contents.append(f"Image Filename above: {os.path.basename(img_path)}")
            except Exception as e:
                pass
                
        logger.info("Local processing complete. Sending unified payload to Gemini 1.5 Pro...")

        # 3. Request structured completion
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DetailedDiagnosticReport,
                temperature=0.0,
            ),
        )

        structured_output = response.text
        
        # 4. Save output
        with open(output_json, 'w', encoding='utf-8') as f:
            f.write(json.dumps(json.loads(structured_output), indent=4))
            
        logger.info(f"Phase 2 AI Extraction successful! Saved to {output_json}")
        
    except Exception as e:
        logger.error(f"An error occurred during AI extraction: {e}")
        return False
                
    return True
