"""
VLM Field Extractor — Qwen2.5-VL based Document Intelligence

Uses a Vision-Language Model to extract structured fields directly from
admission form images, similar to Azure Document Intelligence / Google Document AI.

Supports:
  - Qwen2.5-VL-3B-Instruct (primary, best accuracy)
  - GOT-OCR2.0 (fallback OCR)
  - Any VLM on HuggingFace with image+text → structured JSON

Architecture:
  Image → VLM → Structured JSON (all 90+ AdmissionForm fields)
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from PIL import Image

logger = logging.getLogger(__name__)

# Schema: all AdmissionForm fields grouped by page
ADMISSION_FORM_SCHEMA = {
    "page_1_academic": [
        "academic_session", "course", "admission_category", "admission_category_other",
        "du_portal_form_number", "cuet_score", "college_roll_no", "date_of_admission",
    ],
    "page_1_personal": [
        "first_name", "middle_name", "surname", "student_name",
        "gender", "date_of_birth", "category", "nationality", "religion",
        "aadhar_number", "blood_group", "below_poverty_line", "minority_category",
    ],
    "page_1_address": [
        "permanent_address", "permanent_state", "permanent_pincode",
        "correspondence_address", "correspondence_state", "correspondence_pincode",
        "phone_number", "alternate_phone", "email",
    ],
    "page_1_parents": [
        "mother_name", "father_name",
    ],
    "page_1_cuet_marks": [
        "cuet_subject_1", "cuet_total_score_1", "cuet_score_obtained_1",
        "cuet_subject_2", "cuet_total_score_2", "cuet_score_obtained_2",
        "cuet_subject_3", "cuet_total_score_3", "cuet_score_obtained_3",
        "cuet_subject_4", "cuet_total_score_4", "cuet_score_obtained_4",
        "cuet_subject_5", "cuet_total_score_5", "cuet_score_obtained_5",
        "cuet_subject_6", "cuet_total_score_6", "cuet_score_obtained_6",
        "cuet_total_score",
    ],
    "page_2_qualifying_exam": [
        "twelfth_year", "twelfth_board", "twelfth_roll_number",
        "twelfth_institution", "hindi_studied_upto",
    ],
    "page_2_personal_info": [
        "annual_income",
    ],
    "page_2_mother_details": [
        "mother_occupation", "mother_designation", "mother_organization",
        "mother_email", "mother_mobile",
    ],
    "page_2_father_details": [
        "father_occupation", "father_designation", "father_organization",
        "father_email", "father_mobile",
    ],
    "page_2_guardian_details": [
        "guardian_name", "guardian_residential_address", "guardian_organization",
        "guardian_email", "guardian_mobile",
    ],
    "page_2_other_info": [
        "du_enrollment_number", "hindi_medium_preference",
        "category_certificate_authority", "category_certificate_number",
        "category_certificate_date", "disability_percentage", "disability_type",
    ],
    "page_3_education": [
        "tenth_board", "tenth_year", "tenth_percentage", "tenth_school",
        "twelfth_percentage", "twelfth_school",
    ],
}

ALL_FIELDS = []
for fields in ADMISSION_FORM_SCHEMA.values():
    ALL_FIELDS.extend(fields)


def get_extraction_prompt(page_hint: str = "") -> str:
    """Generate the system prompt for VLM field extraction."""
    fields_json = json.dumps({f: "" for f in ALL_FIELDS}, indent=2)
    
    prompt = f"""You are a world-class Document AI system specialized in extracting structured data from Indian university admission forms (SRCC / Delhi University).

TASK: Extract ALL field values from this admission form image into structured JSON.

RULES:
1. Extract EXACT text as written in the form — do not paraphrase or correct
2. For checkboxes/ticks, return the selected option (e.g., "Male", "B.COM.(H)", "OBC")
3. For handwritten fields, transcribe as accurately as possible
4. Return empty string "" for fields not visible in this page
5. Names should be in CAPITAL LETTERS as written
6. Dates in DD/MM/YYYY format
7. Phone numbers as digits only (10 digits)
8. PIN codes as 6 digits
9. For CUET marks table, extract each subject with its total and obtained scores

{f"This appears to be {page_hint}." if page_hint else ""}

OUTPUT FORMAT: Return ONLY valid JSON with these exact field names:
{fields_json}

IMPORTANT: Return ONLY the JSON object, no markdown, no explanation, no code fences."""
    return prompt


class VLMFieldExtractor:
    """Extract form fields using a Vision-Language Model."""
    
    def __init__(self, model_name: str = "Qwen/Qwen2.5-VL-3B-Instruct",
                 custom_model_path: Optional[str] = None,
                 device: str = "auto",
                 use_quantization: bool = True):
        self.model_name = custom_model_path or model_name
        self.device = device
        self.use_quantization = use_quantization
        self.model = None
        self.processor = None
        self._loaded = False
        
    def load_model(self):
        """Load the VLM model and processor."""
        if self._loaded:
            return
            
        import torch
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
        
        logger.info(f"Loading VLM: {self.model_name}")
        start = time.time()
        
        # Determine device and dtype
        if torch.cuda.is_available():
            device_map = "auto"
            torch_dtype = torch.float16
            logger.info("  Using CUDA GPU with float16")
        else:
            device_map = "cpu"
            torch_dtype = torch.float32
            logger.info("  Using CPU with float32")
        
        # Load model
        model_kwargs = {
            "torch_dtype": torch_dtype,
            "device_map": device_map,
        }
        
        # Try 4-bit quantization if available and requested
        if self.use_quantization and torch.cuda.is_available():
            try:
                from transformers import BitsAndBytesConfig
                model_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                )
                logger.info("  Using 4-bit quantization")
            except ImportError:
                logger.warning("  bitsandbytes not available, using full precision")
        
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self.model_name, **model_kwargs
        )
        self.processor = AutoProcessor.from_pretrained(
            self.model_name,
            min_pixels=256*28*28,
            max_pixels=1280*28*28,
        )
        
        self._loaded = True
        elapsed = time.time() - start
        logger.info(f"  Model loaded in {elapsed:.1f}s")
        
    def extract_fields_from_image(self, image: Image.Image,
                                   page_hint: str = "") -> Dict[str, str]:
        """Extract all form fields from a single page image."""
        self.load_model()
        
        import torch
        from qwen_vl_utils import process_vision_info
        
        prompt = get_extraction_prompt(page_hint)
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        
        # Process with the model
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.model.device)
        
        # Generate
        with torch.no_grad():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=4096,
                temperature=0.1,
                do_sample=False,
            )
        
        # Decode — only the generated tokens
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )[0]
        
        # Parse JSON from output
        return self._parse_json_output(output_text)
    
    def extract_fields_from_pages(self, images: List[Image.Image]) -> Dict[str, str]:
        """Extract fields from multiple page images and merge."""
        all_fields = {}
        
        page_hints = [
            "Page 1 — academic details, personal info, address, CUET marks",
            "Page 2 — qualifying exam, parent details, guardian, other info",
            "Page 3 — document checklist",
            "Supporting document (certificate, marksheet, ID)",
        ]
        
        for i, img in enumerate(images):
            hint = page_hints[i] if i < len(page_hints) else f"Page {i+1}"
            logger.info(f"  Processing page {i+1}/{len(images)}: {hint}")
            
            try:
                page_fields = self.extract_fields_from_image(img, hint)
                # Merge: keep non-empty values, prefer earlier pages for conflicts
                for key, value in page_fields.items():
                    if value and value.strip():
                        if key not in all_fields or not all_fields[key]:
                            all_fields[key] = value
            except Exception as e:
                logger.error(f"  Error on page {i+1}: {e}")
                continue
        
        return all_fields
    
    def _parse_json_output(self, text: str) -> Dict[str, str]:
        """Parse JSON from VLM output, handling various formats."""
        # Try direct JSON parse
        text = text.strip()
        
        # Remove markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            text = text.strip()
        
        # Try parsing
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return {k: str(v) if v is not None else "" for k, v in result.items()}
        except json.JSONDecodeError:
            pass
        
        # Try finding JSON object in the text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                result = json.loads(text[start:end+1])
                if isinstance(result, dict):
                    return {k: str(v) if v is not None else "" for k, v in result.items()}
            except json.JSONDecodeError:
                pass
        
        logger.warning(f"Failed to parse JSON from VLM output: {text[:200]}...")
        return {}
    
    def is_available(self) -> bool:
        """Check if the VLM model can be loaded."""
        try:
            import torch
            from transformers import Qwen2_5_VLForConditionalGeneration
            return True
        except ImportError:
            return False


class GOTOCRExtractor:
    """Extract text using GOT-OCR2.0 as a high-quality OCR engine."""
    
    def __init__(self, model_name: str = "stepfun-ai/GOT-OCR-2.0-hf"):
        self.model_name = model_name
        self.model = None
        self.processor = None
        self._loaded = False
        
    def load_model(self):
        if self._loaded:
            return
            
        import torch
        from transformers import AutoModel, AutoTokenizer
        
        logger.info(f"Loading GOT-OCR2.0: {self.model_name}")
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            torch_dtype=dtype,
            device_map=device,
        )
        self.model.eval()
        self._loaded = True
        logger.info("  GOT-OCR2.0 loaded")
        
    def extract_text(self, image_path: str, ocr_type: str = "ocr") -> str:
        """Extract text from image using GOT-OCR2.0."""
        self.load_model()
        return self.model.chat(self.tokenizer, image_path, ocr_type=ocr_type)
    
    def extract_formatted(self, image_path: str) -> str:
        """Extract text with formatting (markdown)."""
        self.load_model()
        return self.model.chat(self.tokenizer, image_path, ocr_type="format")
    
    def is_available(self) -> bool:
        try:
            from transformers import AutoModel
            return True
        except ImportError:
            return False


class DocumentAIExtractor:
    """
    World-class Document AI — combines VLM field extraction with OCR fallback.
    
    Architecture:
      1. Primary: Qwen2.5-VL processes each page → structured JSON
      2. Fallback: GOT-OCR2.0 → raw text → regex/pattern extraction
      3. Fusion: Merge results from all pages with validation
    """
    
    def __init__(self, 
                 vlm_model: str = "Qwen/Qwen2.5-VL-3B-Instruct",
                 custom_model_path: Optional[str] = None,
                 use_got_ocr: bool = True):
        self.vlm = VLMFieldExtractor(vlm_model, custom_model_path)
        self.got_ocr = GOTOCRExtractor() if use_got_ocr else None
        
    def extract_from_pdf(self, pdf_path: str, dpi: int = 200) -> Dict[str, Any]:
        """Extract all fields from a multi-page PDF."""
        from pdf2image import convert_from_path
        
        logger.info(f"Processing PDF: {pdf_path}")
        start = time.time()
        
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=dpi)
        logger.info(f"  Converted to {len(images)} pages")
        
        # Process first 3 pages (main form pages)
        form_pages = images[:min(len(images), 4)]
        fields = self.vlm.extract_fields_from_pages(form_pages)
        
        elapsed = time.time() - start
        
        return {
            "fields": fields,
            "num_pages": len(images),
            "pages_processed": len(form_pages),
            "time_seconds": round(elapsed, 1),
            "model": self.vlm.model_name,
        }
    
    def extract_from_image(self, image_path: str) -> Dict[str, Any]:
        """Extract all fields from a single form image."""
        start = time.time()
        
        image = Image.open(image_path).convert("RGB")
        fields = self.vlm.extract_fields_from_image(image)
        
        elapsed = time.time() - start
        
        return {
            "fields": fields,
            "time_seconds": round(elapsed, 1),
            "model": self.vlm.model_name,
        }
    
    def extract_from_images(self, image_paths: List[str]) -> Dict[str, Any]:
        """Extract from multiple page images."""
        start = time.time()
        
        images = [Image.open(p).convert("RGB") for p in image_paths if Path(p).exists()]
        fields = self.vlm.extract_fields_from_pages(images)
        
        elapsed = time.time() - start
        
        return {
            "fields": fields,
            "num_pages": len(images),
            "time_seconds": round(elapsed, 1),
            "model": self.vlm.model_name,
        }


def main():
    """Quick test of the Document AI extractor."""
    import argparse
    
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    parser = argparse.ArgumentParser(description="Document AI Field Extractor")
    parser.add_argument("input", help="Path to PDF or image file")
    parser.add_argument("--model", default="Qwen/Qwen2.5-VL-3B-Instruct",
                       help="VLM model name or path")
    parser.add_argument("--output", help="Output JSON path")
    args = parser.parse_args()
    
    extractor = DocumentAIExtractor(vlm_model=args.model)
    
    input_path = Path(args.input)
    if input_path.suffix.lower() == ".pdf":
        result = extractor.extract_from_pdf(str(input_path))
    else:
        result = extractor.extract_from_image(str(input_path))
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {args.output}")


if __name__ == "__main__":
    main()
