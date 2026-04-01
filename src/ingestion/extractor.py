import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Set

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)

def _extract_page_text(page: "fitz.Page") -> str:
    """Extracts and cleans text from a single PDF page."""
    return page.get_text("text").strip()


def _save_extracted_image(doc: "fitz.Document", xref: int, image_path: str, seen_hashes: Set[str]) -> bool:
    """Extracts an image given its xref, handles colorspace, checks duplicates, and saves it."""
    try:
        pix = fitz.Pixmap(doc, xref)
        if pix.n - pix.alpha > 3:
            pix = fitz.Pixmap(fitz.csRGB, pix)
            
        # 🚨 Deduplication Strategy: Hash the raw pixel bytes
        # Extremely common for PDFs to repeat a large background gradient or header image 50 times.
        # Hashing guarantees if the image is visually identical to a previous one, we skip it.
        img_hash = hashlib.md5(pix.samples).hexdigest()
        
        if img_hash in seen_hashes:
            return False
            
        seen_hashes.add(img_hash)
        pix.save(image_path)
        return True
    except Exception as img_e:
        logger.warning(f"Failed to process image xref {xref}: {str(img_e)}")
        return False


def _extract_page_images(doc: "fitz.Document", page_num: int, output_dir: str, doc_prefix: str, seen_hashes: Set[str]) -> List[str]:
    """Extracts all meaningful embedded images from a specific page."""
    page = doc[page_num]
    image_list = page.get_images(full=True)
    saved_paths = []
    
    for img_index, img_info in enumerate(image_list):
        xref = img_info[0]
        width = img_info[2]
        height = img_info[3]
        
        # 🚨 DIMENSION FILTER: Ignore lines, background tiles, and tiny logos
        if width < 200 or height < 200:
            continue
            
        image_filename = f"{doc_prefix}_page_{page_num + 1}_img_{img_index + 1}.png"
        image_path = os.path.join(output_dir, image_filename)
        
        success = _save_extracted_image(doc, xref, image_path, seen_hashes)
        if success:
            saved_paths.append(image_path)
            
    return saved_paths


def extract_pdf_assets(pdf_path: str, output_image_dir: str, doc_prefix: str) -> List[Dict[str, Any]]:
    """
    Extracts text and embedded images from a given PDF.
    """
    if not fitz:
        logger.error("PyMuPDF is not installed. Please run: pip install pymupdf")
        return []

    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        return []

    Path(output_image_dir).mkdir(parents=True, exist_ok=True)
    extracted_data = []
    
    # Track MD5 hashes at the document level
    seen_image_hashes: Set[str] = set()

    try:
        doc = fitz.open(pdf_path)
        logger.info(f"Successfully opened {pdf_path} ({len(doc)} pages)")
        
        for page_num in range(len(doc)):
            page_text = _extract_page_text(doc[page_num])
            saved_images = _extract_page_images(doc, page_num, output_image_dir, doc_prefix, seen_image_hashes)
            
            extracted_data.append({
                "page_number": page_num + 1,
                "text": page_text,
                "images": saved_images
            })
            
    except Exception as e:
        logger.error(f"An error occurred while processing {pdf_path}: {str(e)}")
    
    return extracted_data
