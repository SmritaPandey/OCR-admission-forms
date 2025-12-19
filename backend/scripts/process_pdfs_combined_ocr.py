"""
Process all PDFs using Combined Tesseract + Google Vision OCR approach
Based on: https://programminghistorian.org/en/lessons/ocr-with-google-vision-and-tesseract

This script implements both methods from the article:
- Method I: Create new PDF with regions stacked vertically, then OCR with Google Vision
- Method II: Use Tesseract regions to extract words from Google Vision JSON response

Processes all PDFs in data/samples/pdfs/ and generates training data.
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import io

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from google.cloud import vision
from google.cloud import storage
try:
    from tesserocr import PyTessBaseAPI
    TESSEROCR_AVAILABLE = True
except ImportError:
    TESSEROCR_AVAILABLE = False
    print("Warning: tesserocr not available. Using pytesseract fallback for region detection.")

from backend.config import settings
from backend.utils.file_handler import load_all_pdf_pages
from backend.utils.ai_form_parser import AIFormParser


class CombinedOCREngine:
    """
    Combined OCR Engine implementing both methods from the Programming Historian article.
    Uses Tesseract for layout detection and Google Vision for character recognition.
    """
    
    def __init__(self, use_cloud_storage: bool = False, bucket_name: Optional[str] = None):
        """
        Initialize the combined OCR engine.
        
        Args:
            use_cloud_storage: If True, upload PDFs to Google Cloud Storage for processing
            bucket_name: Google Cloud Storage bucket name (required if use_cloud_storage=True)
        """
        self.use_cloud_storage = use_cloud_storage
        self.bucket_name = bucket_name
        
        # Initialize Google Vision client
        self.vision_client = None
        self.storage_client = None
        self.bucket = None
        
        if use_cloud_storage and bucket_name:
            try:
                self.storage_client = storage.Client()
                self.bucket = self.storage_client.get_bucket(bucket_name)
            except Exception as e:
                print(f"Warning: Could not initialize Cloud Storage: {e}")
                print("Falling back to local processing...")
                use_cloud_storage = False
        
        try:
            # Check for credentials
            if settings.GOOGLE_APPLICATION_CREDENTIALS:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
            
            self.vision_client = vision.ImageAnnotatorClient()
        except Exception as e:
            print(f"Warning: Could not initialize Google Vision client: {e}")
            print("Make sure GOOGLE_APPLICATION_CREDENTIALS is set or credentials are configured.")
            self.vision_client = None
        
        # Initialize form parsers
        self.ai_parser = AIFormParser()
    
    def get_tesseract_regions(self, image: Image.Image) -> List[Dict[str, int]]:
        """
        Use Tesseract to identify text regions in the image.
        Returns list of region dictionaries with x, y, w, h coordinates.
        """
        try:
            if TESSEROCR_AVAILABLE:
                # Use tesserocr for better region detection
                with PyTessBaseAPI() as api:
                    api.SetImage(image)
                    try:
                        regions = api.GetRegions()
                        # Convert to list of dictionaries
                        region_list = []
                        for (im, box) in regions:
                            region_list.append({
                                'x': box['x'],
                                'y': box['y'],
                                'w': box['w'],
                                'h': box['h']
                            })
                        if region_list:
                            return region_list
                    except AttributeError:
                        # GetRegions might not be available in all tesserocr versions
                        pass
            
            # Fallback: Use pytesseract to get word-level data and cluster into regions
            data = pytesseract.image_to_data(
                image,
                config='--psm 6',  # Uniform block of text
                output_type=pytesseract.Output.DICT
            )
            
            # Group words into regions based on proximity
            words_with_coords = []
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                if text and int(data['conf'][i]) > 0:
                    words_with_coords.append({
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'w': data['width'][i],
                        'h': data['height'][i]
                    })
            
            if not words_with_coords:
                # Fallback: return full image as single region
                width, height = image.size
                return [{'x': 0, 'y': 0, 'w': width, 'h': height}]
            
            # Cluster words into regions
            regions = self._cluster_words_into_regions(words_with_coords, image.size)
            return regions
            
        except Exception as e:
            print(f"Error getting Tesseract regions: {e}")
            # Fallback: return full image as single region
            width, height = image.size
            return [{'x': 0, 'y': 0, 'w': width, 'h': height}]
    
    def _cluster_words_into_regions(self, words: List[Dict], image_size: Tuple[int, int]) -> List[Dict[str, int]]:
        """
        Cluster words into regions based on proximity.
        Simple approach: group words by vertical proximity (for columns).
        """
        if not words:
            return []
        
        # Sort words by y-coordinate (top to bottom)
        sorted_words = sorted(words, key=lambda w: (w['y'], w['x']))
        
        regions = []
        current_region_words = [sorted_words[0]]
        
        # Threshold for vertical spacing (pixels)
        vertical_threshold = 30
        
        for word in sorted_words[1:]:
            last_word = current_region_words[-1]
            vertical_gap = word['y'] - (last_word['y'] + last_word['h'])
            
            if vertical_gap < vertical_threshold:
                current_region_words.append(word)
            else:
                # Finalize current region
                regions.append(self._words_to_region(current_region_words))
                current_region_words = [word]
        
        # Add last region
        if current_region_words:
            regions.append(self._words_to_region(current_region_words))
        
        return regions
    
    def _words_to_region(self, words: List[Dict]) -> Dict[str, int]:
        """Convert a list of words into a bounding box region"""
        if not words:
            return {'x': 0, 'y': 0, 'w': 0, 'h': 0}
        
        min_x = min(w['x'] for w in words)
        min_y = min(w['y'] for w in words)
        max_x = max(w['x'] + w['w'] for w in words)
        max_y = max(w['y'] + w['h'] for w in words)
        
        return {
            'x': max(0, min_x - 5),  # Add small padding
            'y': max(0, min_y - 5),
            'w': max_x - min_x + 10,
            'h': max_y - min_y + 10
        }
    
    def add_padding(self, pil_img: Image.Image, n_pixels: int = 5, colour: str = "white") -> Image.Image:
        """Add padding to an image"""
        width, height = pil_img.size
        new_width = width + n_pixels * 2
        new_height = height + n_pixels * 2
        img_pad = Image.new(pil_img.mode, (new_width, new_height), colour)
        img_pad.paste(pil_img, (n_pixels, n_pixels))
        return img_pad
    
    def method_one_combined_ocr(self, image: Image.Image) -> Dict[str, Any]:
        """
        Method I: Create new image with regions stacked vertically, then OCR with Google Vision.
        This method rearranges text regions vertically to avoid layout issues.
        """
        if not self.vision_client:
            raise Exception("Google Vision client not initialized")
        
        try:
            # Step 1: Get text regions from Tesseract
            regions = self.get_tesseract_regions(image)
            
            if not regions:
                # Fallback: use full image
                width, height = image.size
                regions = [{'x': 0, 'y': 0, 'w': width, 'h': height}]
            
            # Step 2: Extract and pad each region
            region_images = []
            for region in regions:
                # Crop region from image
                x, y, w, h = region['x'], region['y'], region['w'], region['h']
                region_img = image.crop((x, y, x + w, y + h))
                
                # Add padding
                region_img = self.add_padding(region_img, n_pixels=5, colour="white")
                region_images.append(region_img)
            
            # Step 3: Stack regions vertically
            total_height = sum(img.size[1] for img in region_images)
            max_width = max(img.size[0] for img in region_images) if region_images else image.size[0]
            
            stacked_image = Image.new('RGB', (max_width, total_height), color="white")
            current_y = 0
            
            for region_img in region_images:
                stacked_image.paste(region_img, (0, current_y))
                current_y += region_img.size[1]
            
            # Step 4: OCR stacked image with Google Vision
            img_byte_arr = io.BytesIO()
            stacked_image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            vision_image = vision.Image(content=img_byte_arr.getvalue())
            response = self.vision_client.document_text_detection(image=vision_image)
            
            if response.full_text_annotation:
                full_text = response.full_text_annotation.text
                confidence = 0.95  # Google Vision is typically very accurate
            else:
                full_text = ""
                confidence = 0.0
            
            return {
                "raw_text": full_text.strip(),
                "confidence": confidence * 100,
                "method": "method_one",
                "regions_detected": len(regions)
            }
            
        except Exception as e:
            raise Exception(f"Method I OCR error: {str(e)}")
    
    def method_two_combined_ocr(self, image: Image.Image) -> Dict[str, Any]:
        """
        Method II: Use Tesseract regions to extract words from Google Vision JSON response.
        This method preserves the original layout while using Google Vision's superior character recognition.
        """
        if not self.vision_client:
            raise Exception("Google Vision client not initialized")
        
        try:
            # Step 1: Get text regions from Tesseract
            tesseract_regions = self.get_tesseract_regions(image)
            page_width, page_height = image.size
            
            if not tesseract_regions:
                # Fallback: use full image
                tesseract_regions = [{'x': 0, 'y': 0, 'w': page_width, 'h': page_height}]
            
            # Step 2: Get word-level data from Google Vision
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            vision_image = vision.Image(content=img_byte_arr.getvalue())
            response = self.vision_client.document_text_detection(image=vision_image)
            
            if not response.full_text_annotation:
                return {
                    "raw_text": "",
                    "confidence": 0.0,
                    "method": "method_two"
                }
            
            # Step 3: Extract words with coordinates from Google Vision
            full_text_annotation = response.full_text_annotation
            page = full_text_annotation.pages[0] if full_text_annotation.pages else None
            
            if not page:
                return {
                    "raw_text": full_text_annotation.text if full_text_annotation.text else "",
                    "confidence": 0.0,
                    "method": "method_two"
                }
            
            # Normalize coordinates (Google Vision uses normalized 0-1 coordinates)
            gv_width = page.width
            gv_height = page.height
            
            # Step 4: Match Google Vision words to Tesseract regions
            region_texts = []
            all_confidences = []
            
            for region in tesseract_regions:
                # Convert Tesseract pixel coordinates to normalized coordinates
                x1 = region['x'] / page_width
                y1 = region['y'] / page_height
                x2 = (region['x'] + region['w']) / page_width
                y2 = (region['y'] + region['h']) / page_height
                
                # Find words in this region
                region_words = []
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            # Get word bounding box (normalized)
                            vertices = word.bounding_box.vertices
                            if not vertices:
                                continue
                            
                            word_min_x = min(v.x / gv_width for v in vertices if v.x is not None)
                            word_max_x = max(v.x / gv_width for v in vertices if v.x is not None)
                            word_min_y = min(v.y / gv_height for v in vertices if v.y is not None)
                            word_max_y = max(v.y / gv_height for v in vertices if v.y is not None)
                            
                            # Check if word is in region (with small tolerance)
                            tolerance = 0.01
                            if (word_min_x + tolerance >= x1 and word_max_x - tolerance <= x2 and
                                word_min_y + tolerance >= y1 and word_max_y - tolerance <= y2):
                                
                                # Extract word text
                                word_text = ''.join([symbol.text for symbol in word.symbols])
                                region_words.append({
                                    'text': word_text,
                                    'x': word_min_x,
                                    'y': word_min_y,
                                    'confidence': word.confidence if hasattr(word, 'confidence') else 0.95
                                })
                
                # Sort words by position (top to bottom, left to right)
                region_words.sort(key=lambda w: (w['y'], w['x']))
                
                # Build text for this region
                region_text = ' '.join([w['text'] for w in region_words])
                if region_text:
                    region_texts.append(region_text)
                    confidences = [w['confidence'] for w in region_words]
                    all_confidences.extend(confidences)
            
            # Combine all region texts
            combined_text = '\n'.join(region_texts) if region_texts else full_text_annotation.text
            
            # Calculate average confidence
            avg_confidence = (sum(all_confidences) / len(all_confidences) * 100 
                            if all_confidences else 90.0)
            
            return {
                "raw_text": combined_text.strip(),
                "confidence": round(avg_confidence, 2),
                "method": "method_two",
                "regions_detected": len(tesseract_regions)
            }
            
        except Exception as e:
            raise Exception(f"Method II OCR error: {str(e)}")
    
    def process_pdf(self, pdf_path: str, method: str = "method_two") -> Dict[str, Any]:
        """
        Process a PDF file using combined OCR.
        
        Args:
            pdf_path: Path to PDF file
            method: "method_one" or "method_two" (default: method_two)
        
        Returns:
            Dictionary with OCR results for all pages
        """
        try:
            # Convert PDF to images
            try:
                pages = convert_from_path(pdf_path, dpi=300)
            except Exception as e:
                # Fallback: try using PyMuPDF if poppler is not available
                try:
                    import fitz
                    pdf_doc = fitz.open(pdf_path)
                    pages = []
                    for page_num in range(len(pdf_doc)):
                        page = pdf_doc[page_num]
                        mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
                        pix = page.get_pixmap(matrix=mat, alpha=False)
                        img_data = pix.tobytes("png")
                        pages.append(Image.open(io.BytesIO(img_data)))
                    pdf_doc.close()
                except ImportError:
                    raise Exception(f"Unable to get page count. Is poppler installed and in PATH? Error: {e}")
            
            if not pages:
                raise ValueError(f"No pages found in PDF: {pdf_path}")
            
            results = {
                "pdf_path": pdf_path,
                "total_pages": len(pages),
                "method": method,
                "pages": [],
                "combined_text": [],
                "all_confidences": []
            }
            
            # Process each page
            for page_num, page_image in enumerate(pages, 1):
                try:
                    if method == "method_one":
                        page_result = self.method_one_combined_ocr(page_image)
                    else:
                        page_result = self.method_two_combined_ocr(page_image)
                    
                    results["pages"].append({
                        "page_number": page_num,
                        "raw_text": page_result.get("raw_text", ""),
                        "confidence": page_result.get("confidence", 0.0),
                        "regions_detected": page_result.get("regions_detected", 0)
                    })
                    
                    if page_result.get("raw_text"):
                        results["combined_text"].append(
                            f"\n--- Page {page_num} ---\n{page_result['raw_text']}"
                        )
                    
                    if page_result.get("confidence"):
                        results["all_confidences"].append(page_result["confidence"])
                        
                except Exception as e:
                    print(f"Error processing page {page_num} of {pdf_path}: {e}")
                    results["pages"].append({
                        "page_number": page_num,
                        "error": str(e),
                        "raw_text": "",
                        "confidence": 0.0
                    })
            
            # Calculate overall statistics
            results["full_text"] = "\n".join(results["combined_text"])
            results["avg_confidence"] = (
                sum(results["all_confidences"]) / len(results["all_confidences"])
                if results["all_confidences"] else 0.0
            )
            
            return results
            
        except Exception as e:
            raise Exception(f"Error processing PDF {pdf_path}: {str(e)}")


def create_training_labels_from_blank_form(blank_form_path: str, ocr_engine: CombinedOCREngine) -> Dict[str, Any]:
    """
    Use the blank form to identify field keys (labels) and their positions.
    This creates a template for labeling filled forms.
    """
    print(f"\nProcessing blank form: {blank_form_path}")
    
    try:
        # Process blank form
        blank_result = ocr_engine.process_pdf(blank_form_path, method="method_two")
        
        # Extract field labels from blank form
        # The blank form should contain field labels like "Name:", "Date of Birth:", etc.
        blank_text = blank_result.get("full_text", "")
        
        # Use AI parser to identify field names
        field_template = {}
        ai_parser = AIFormParser()
        
        # Try to extract field labels from the blank form text
        for field_name, aliases in ai_parser.field_mappings.items():
            for alias in aliases:
                # Look for field label in text (e.g., "Name:", "Student Name:", etc.)
                import re
                pattern = rf'\b{re.escape(alias)}\s*[:]?\s*'
                if re.search(pattern, blank_text, re.IGNORECASE):
                    field_template[field_name] = {
                        "label": alias,
                        "aliases": aliases,
                        "found_in_blank_form": True
                    }
                    break
        
        return {
            "blank_form_path": blank_form_path,
            "field_template": field_template,
            "blank_form_text": blank_text,
            "total_fields_found": len(field_template)
        }
        
    except Exception as e:
        print(f"Error processing blank form: {e}")
        return {
            "blank_form_path": blank_form_path,
            "error": str(e),
            "field_template": {}
        }


def label_filled_form(filled_form_result: Dict[str, Any], field_template: Dict[str, Any]) -> Dict[str, Any]:
    """
    Label a filled form using the template from the blank form.
    Extracts key-value pairs based on field positions and labels.
    """
    try:
        filled_text = filled_form_result.get("full_text", "")
        ai_parser = AIFormParser()
        
        # Extract fields using the template
        labeled_fields = []
        
        for field_name, field_info in field_template.items():
            label = field_info.get("label", field_name)
            aliases = field_info.get("aliases", [label])
            
            # Try to extract value after the label
            for alias in aliases:
                import re
                # Pattern: "Label: Value" or "Label Value"
                pattern = rf'{re.escape(alias)}\s*[:]?\s*([^\n]+)'
                match = re.search(pattern, filled_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value:
                        cleaned_value = ai_parser._clean_value(value, field_name)
                        labeled_fields.append({
                            "field_name": field_name,
                            "value": cleaned_value,
                            "label": alias,
                            "confidence": 0.9,
                            "extracted_from": "template_matching"
                        })
                        break
        
        # Also try AI parser as fallback
        parsed_data = ai_parser.parse_from_text(filled_text)
        for field_name, value in parsed_data.items():
            # Only add if not already found
            if not any(f["field_name"] == field_name for f in labeled_fields):
                labeled_fields.append({
                    "field_name": field_name,
                    "value": value,
                    "label": field_name,
                    "confidence": 0.85,
                    "extracted_from": "ai_parser"
                })
        
        return {
            "form_path": filled_form_result.get("pdf_path", ""),
            "fields": labeled_fields,
            "total_fields": len(labeled_fields),
            "raw_text": filled_text
        }
        
    except Exception as e:
        print(f"Error labeling form: {e}")
        return {
            "form_path": filled_form_result.get("pdf_path", ""),
            "error": str(e),
            "fields": []
        }


def process_all_pdfs(
    pdfs_dir: str,
    blank_form_path: str,
    output_dir: str,
    method: str = "method_two"
):
    """
    Process all PDFs in the directory and generate training data.
    """
    pdfs_path = Path(pdfs_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize OCR engine
    print("Initializing Combined OCR Engine...")
    ocr_engine = CombinedOCREngine(use_cloud_storage=False)
    
    if not ocr_engine.vision_client:
        print("ERROR: Google Vision client not initialized!")
        print("Please set up Google Cloud credentials:")
        print("1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable to path of service account JSON")
        print("2. Or run: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json")
        return
    
    # Step 1: Process blank form to create template
    print("\n" + "="*80)
    print("STEP 1: Processing blank form to create field template...")
    print("="*80)
    
    blank_form_template = create_training_labels_from_blank_form(blank_form_path, ocr_engine)
    
    template_file = output_path / "field_template.json"
    with open(template_file, 'w') as f:
        json.dump(blank_form_template, f, indent=2)
    print(f"Field template saved to: {template_file}")
    print(f"Found {blank_form_template.get('total_fields_found', 0)} fields in blank form")
    
    # Step 2: Process all PDFs
    print("\n" + "="*80)
    print("STEP 2: Processing all PDFs...")
    print("="*80)
    
    pdf_files = list(pdfs_path.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files")
    
    all_results = []
    training_data = []
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
        
        try:
            # Process PDF
            result = ocr_engine.process_pdf(str(pdf_file), method=method)
            all_results.append(result)
            
            # Label the form
            labeled_form = label_filled_form(result, blank_form_template.get("field_template", {}))
            training_data.append(labeled_form)
            
            print(f"  ✓ Processed {result['total_pages']} pages")
            print(f"  ✓ Extracted {labeled_form.get('total_fields', 0)} fields")
            print(f"  ✓ Confidence: {result.get('avg_confidence', 0):.1f}%")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            all_results.append({
                "pdf_path": str(pdf_file),
                "error": str(e)
            })
    
    # Step 3: Save results
    print("\n" + "="*80)
    print("STEP 3: Saving results...")
    print("="*80)
    
    # Save OCR results
    results_file = output_path / "ocr_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "processed_at": datetime.now().isoformat(),
            "method": method,
            "total_pdfs": len(pdf_files),
            "results": all_results
        }, f, indent=2)
    print(f"OCR results saved to: {results_file}")
    
    # Save training data
    training_file = output_path / "training_data.json"
    with open(training_file, 'w') as f:
        json.dump({
            "created_at": datetime.now().isoformat(),
            "total_forms": len(training_data),
            "field_template": blank_form_template.get("field_template", {}),
            "training_samples": training_data
        }, f, indent=2)
    print(f"Training data saved to: {training_file}")
    
    # Generate summary
    total_fields = sum(len(t.get("fields", [])) for t in training_data)
    confidences = [r.get("avg_confidence", 0) for r in all_results if "avg_confidence" in r and r.get("avg_confidence", 0) > 0]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    summary = {
        "total_pdfs_processed": len(pdf_files),
        "total_pages": sum(r.get("total_pages", 0) for r in all_results),
        "total_fields_extracted": total_fields,
        "average_confidence": round(avg_confidence, 2),
        "method_used": method,
        "output_directory": str(output_path)
    }
    
    summary_file = output_path / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Summary saved to: {summary_file}")
    
    print("\n" + "="*80)
    print("PROCESSING COMPLETE!")
    print("="*80)
    print(f"Processed {len(pdf_files)} PDFs")
    print(f"Extracted {total_fields} fields total")
    print(f"Average confidence: {avg_confidence:.1f}%")
    print(f"\nResults saved to: {output_path}")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process PDFs with Combined OCR and generate training data")
    parser.add_argument(
        "--pdfs-dir",
        type=str,
        default="data/samples/pdfs",
        help="Directory containing PDF files to process"
    )
    parser.add_argument(
        "--blank-form",
        type=str,
        default="data/samples/pdfs/student data form scanned.pdf",
        help="Path to blank form template"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="training_output",
        help="Output directory for results and training data"
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["method_one", "method_two"],
        default="method_two",
        help="OCR method to use (method_one: stack regions, method_two: coordinate matching)"
    )
    
    args = parser.parse_args()
    
    process_all_pdfs(
        pdfs_dir=args.pdfs_dir,
        blank_form_path=args.blank_form,
        output_dir=args.output_dir,
        method=args.method
    )
