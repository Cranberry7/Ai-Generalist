import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def evaluate_and_merge(phase2_json_path: str, image_dir: str, output_path: str) -> bool:
    """
    Reads the AI-generated JSON. Validates image integrity, synthesizes diagnostic paragraphs,
    and flags any explicit diagnostic conflicts between visual and thermal domains.
    """
    
    if not os.path.exists(phase2_json_path):
        logger.error(f"Cannot find AI extracted data at {phase2_json_path}")
        return False
        
    try:
        with open(phase2_json_path, 'r', encoding='utf-8') as f:
            diagnostic_data = json.load(f)
            
        logger.info("Initializing Logic Engine heuristics...")
        
        # We will mutate the document and write it back out as a final payload
        observations = diagnostic_data.get("observations", [])
        
        for obs in observations:
            area_name = obs.get("area_name", "Unknown Area")
            v_findings = obs.get("visual_findings", [])
            t_findings = obs.get("thermal_findings", [])
            images = obs.get("associated_images", [])

            # 1. Synthesis: Build a unified finding paragraph
            unified_summary = []
            if v_findings:
                unified_summary.append("Visual Findings: " + "; ".join(v_findings))
            else:
                unified_summary.append("Visual Findings: None noted or data missing.")
                
            if t_findings:
                unified_summary.append("Thermal Findings: " + "; ".join(t_findings))
            else:
                unified_summary.append("Thermal Findings: No thermal scan data available for this specific area.")
                
            obs["unified_diagnostic_statement"] = " | ".join(unified_summary)
            
            # 2. Conflict Flags: Programmatic checking
            # (e.g. Visual says Normal but Thermal says overheated)
            conflict_detected = False
            conflict_reason = ""
            
            v_text = (" ".join(v_findings)).lower()
            t_text = (" ".join(t_findings)).lower()
            
            visual_normal_keywords = ["normal", "good", "clear", "no anomalies", "no issues"]
            thermal_issue_keywords = ["hotspot", "elevated", "anomaly", "overheating", "high temp", "abnormal"]
            
            is_visual_normal = any(kw in v_text for kw in visual_normal_keywords)
            has_thermal_issue = any(kw in t_text for kw in thermal_issue_keywords)
            
            if is_visual_normal and has_thermal_issue:
                conflict_detected = True
                conflict_reason = "Visual findings imply normal conditions, but thermal scan detected elevated temperatures or anomalies. Manual verification recommended."
                
            obs["conflict_detected"] = conflict_detected
            if conflict_detected:
                obs["conflict_reason"] = conflict_reason
                
            # 3. File System Integrity Validation
            # Ensure the document assembler doesn't crash on broken AI image mappings
            valid_images = []
            for img_ref in images:
                filename = img_ref.get("image_filename", "")
                full_path = os.path.join(image_dir, filename)
                
                if os.path.exists(full_path):
                    # Attach the absolute path explicitly for the document assembler later
                    img_ref["absolute_path"] = full_path
                    valid_images.append(img_ref)
                else:
                    logger.warning(f"Engine Warning: AI referenced an image '{filename}' that does not exist in temp_images. Dropping reference for Document Assembly safety.")
                    
            obs["associated_images"] = valid_images

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(diagnostic_data, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Phase 3 Logic Engine completed successfully. Vetted payload saved to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Logic Engine Failure: {str(e)}")
        return False
