import os
import argparse
import logging
from pathlib import Path

# Load dotenv to check if user supplied keys
from dotenv import load_dotenv

from ingestion.extractor import extract_pdf_assets
from ai_layer.extractor import extract_structured_data
from logic_engine.merger import evaluate_and_merge
from document_assembly.generator import generate_docx_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_phase1(base_dir: str, visual_pdf_in: str, thermal_pdf_in: str):
    logger.info("Starting Phase 1: Data Ingestion & Asset Extraction")
    
    input_dir = os.path.join(base_dir, "data", "input")
    output_dir = os.path.join(base_dir, "data", "output")
    image_dir = os.path.join(output_dir, "temp_images")
    output_json = os.path.join(output_dir, "phase1_extracted_data.json")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Use provided paths or fallback to the data/input directory hardcodes for convenience
    visual_pdf = visual_pdf_in if visual_pdf_in else os.path.join(input_dir, "Sample Report.pdf")
    thermal_pdf = thermal_pdf_in if thermal_pdf_in else os.path.join(input_dir, "Thermal Images.pdf")
    
    if not os.path.exists(visual_pdf) or not os.path.exists(thermal_pdf):
        logger.error(f"Missing input files. Please ensure both PDFs exist: {visual_pdf} & {thermal_pdf}")
        return
        
    visual_data = extract_pdf_assets(visual_pdf, image_dir, "visual")
    thermal_data = extract_pdf_assets(thermal_pdf, image_dir, "thermal")
    
    final_output = {
        "visual_inspection": visual_data,
        "thermal_inspection": thermal_data
    }
    
    import json
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)
    logger.info(f"Phase 1 complete! Data saved to {output_json}")

def process_phase2(base_dir: str):
    logger.info("Starting Phase 2: Multimodal Structured API Extraction")
    
    output_dir = os.path.join(base_dir, "data", "output")
    phase1_json = os.path.join(output_dir, "phase1_extracted_data.json")
    image_dir = os.path.join(output_dir, "temp_images")
    phase2_json = os.path.join(output_dir, "phase2_ai_extracted.json")

    load_dotenv(os.path.join(base_dir, ".env"))
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "YOUR_KEY_HERE":
        logger.error("No valid GEMINI_API_KEY found. Create a .env file and add your key.")
        return
        
    success = extract_structured_data(api_key, phase1_json, image_dir, phase2_json)
    if success:
        logger.info(f"Phase 2 complete! AI structured data saved to {phase2_json}")
    else:
        logger.error("Phase 2 failed.")

def process_phase3(base_dir: str):
    logger.info("Starting Phase 3: Logic Engine & Quality Assurance")
    
    output_dir = os.path.join(base_dir, "data", "output")
    phase2_json = os.path.join(output_dir, "phase2_ai_extracted.json")
    image_dir = os.path.join(output_dir, "temp_images")
    phase3_payload = os.path.join(output_dir, "phase3_final_payload.json")
    
    evaluate_and_merge(phase2_json, image_dir, phase3_payload)

def process_phase4(base_dir: str):
    logger.info("Starting Phase 4: Document Assembly & Generation")
    
    output_dir = os.path.join(base_dir, "data", "output")
    phase3_payload = os.path.join(output_dir, "phase3_final_payload.json")
    final_docx = os.path.join(output_dir, "Detailed_Diagnostic_Report.docx")
    
    generate_docx_report(phase3_payload, final_docx)

def main():
    parser = argparse.ArgumentParser(description="AI Applied Builder Pipeline.")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4], help="Which pipeline phase to execute specifically")
    parser.add_argument("--all", action="store_true", help="Run the entire pipeline end-to-end (Phases 1-4)")
    parser.add_argument("--visual", type=str, default="", help="Absolute or relative path to the Visual PDF Report")
    parser.add_argument("--thermal", type=str, default="", help="Absolute or relative path to the Thermal PDF Report")
    
    args = parser.parse_args()
    
    if not args.phase and not args.all:
        logger.error("You must specify either --phase [1-4] or --all to run the pipeline.")
        return
        
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if args.phase == 1 or args.all:
        process_phase1(base_dir, args.visual, args.thermal)
    if args.phase == 2 or args.all:
        process_phase2(base_dir)
    if args.phase == 3 or args.all:
        process_phase3(base_dir)
    if args.phase == 4 or args.all:
        process_phase4(base_dir)

if __name__ == "__main__":
    main()
