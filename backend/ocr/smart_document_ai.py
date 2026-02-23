"""
Smart Document AI Provider — World-Class Form Field Extraction

Implements the OCRProvider interface using VLM-based document intelligence.
This is the open-source equivalent of Azure Document Intelligence / Google Document AI.

Architecture:
  PDF/Image → VLM (Qwen2.5-VL) → Structured JSON → Schema Validation → Output
"""

import json
import logging
import os
import re
from typing import Dict, Any, Optional, List
from pathlib import Path

from PIL import Image

try:
    from backend.ocr.base_provider import OCRProvider
except ImportError:
    # Allow standalone usage
    class OCRProvider:
        async def extract_text(self, image, language=None): pass
        def is_available(self): return False
        def get_provider_name(self): return ""

logger = logging.getLogger(__name__)


class SmartDocumentAI(OCRProvider):
    """
    World-class Document AI provider using Vision-Language Models.
    
    Combines:
    - Qwen2.5-VL for direct image → structured JSON extraction
    - Schema validation against AdmissionForm fields
    - Cross-field consistency checks
    - Multi-page document processing
    """
    
    def __init__(self,
                 model_name: str = "Qwen/Qwen2.5-VL-3B-Instruct",
                 custom_model_path: Optional[str] = None):
        self.model_name = custom_model_path or model_name
        self._extractor = None
        
    def _get_extractor(self):
        """Lazy-load the VLM extractor."""
        if self._extractor is None:
            from backend.ocr.vlm_field_extractor import DocumentAIExtractor
            self._extractor = DocumentAIExtractor(
                vlm_model=self.model_name,
                custom_model_path=None,
            )
        return self._extractor
    
    async def extract_text(self, image: Image.Image,
                           language: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract structured text and fields from a form image.
        
        Returns the standard OCRProvider format with additional 'fields' key.
        """
        extractor = self._get_extractor()
        
        logger.info("SmartDocumentAI: Extracting fields from image...")
        
        # Extract fields using VLM
        fields = extractor.vlm.extract_fields_from_image(image)
        
        # Validate and clean fields
        fields = self._validate_fields(fields)
        
        # Build text representation from fields
        text_parts = []
        for key, value in fields.items():
            if value and value.strip():
                readable_key = key.replace("_", " ").title()
                text_parts.append(f"{readable_key}: {value}")
        
        full_text = "\n".join(text_parts)
        
        return {
            "text": full_text,
            "confidence": self._calculate_confidence(fields),
            "provider": self.get_provider_name(),
            "fields": fields,
            "field_count": len([v for v in fields.values() if v and v.strip()]),
            "model": self.model_name,
        }
    
    async def extract_from_pdf(self, pdf_path: str, dpi: int = 200) -> Dict[str, Any]:
        """Extract fields from a multi-page PDF form."""
        extractor = self._get_extractor()
        result = extractor.extract_from_pdf(pdf_path, dpi=dpi)
        
        # Validate
        result["fields"] = self._validate_fields(result.get("fields", {}))
        result["provider"] = self.get_provider_name()
        result["field_count"] = len([v for v in result["fields"].values() if v and v.strip()])
        
        return result
    
    async def extract_from_images(self, image_paths: List[str]) -> Dict[str, Any]:
        """Extract fields from multiple page images."""
        extractor = self._get_extractor()
        result = extractor.extract_from_images(image_paths)
        
        result["fields"] = self._validate_fields(result.get("fields", {}))
        result["provider"] = self.get_provider_name()
        result["field_count"] = len([v for v in result["fields"].values() if v and v.strip()])
        
        return result
    
    def _validate_fields(self, fields: Dict[str, str]) -> Dict[str, str]:
        """Validate and normalize extracted field values."""
        validated = {}
        
        for key, value in fields.items():
            if not value or not str(value).strip():
                validated[key] = ""
                continue
                
            value = str(value).strip()
            
            # Phone number validation
            if any(x in key for x in ["phone", "mobile"]):
                digits = re.sub(r'\D', '', value)
                if len(digits) >= 10:
                    validated[key] = digits[-10:]  # Last 10 digits
                    continue
            
            # PIN code validation
            if "pincode" in key:
                digits = re.sub(r'\D', '', value)
                if len(digits) == 6:
                    validated[key] = digits
                    continue
            
            # Date validation
            if "date" in key and key != "date_of_admission":
                # Try to normalize to DD/MM/YYYY
                date_match = re.search(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})', value)
                if date_match:
                    d, m, y = date_match.groups()
                    validated[key] = f"{int(d):02d}/{int(m):02d}/{y}"
                    continue
            
            # Email validation
            if "email" in key:
                email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', value)
                if email_match:
                    validated[key] = email_match.group(0).lower()
                    continue
            
            # Gender normalization
            if key == "gender":
                val_lower = value.lower()
                if "male" in val_lower and "female" not in val_lower:
                    validated[key] = "Male"
                elif "female" in val_lower:
                    validated[key] = "Female"
                elif "trans" in val_lower:
                    validated[key] = "Transgender"
                else:
                    validated[key] = value
                continue
            
            # Course normalization
            if key == "course":
                val_upper = value.upper()
                if "B.COM" in val_upper:
                    validated[key] = "B.COM.(H)"
                elif "B.A" in val_upper and "ECO" in val_upper:
                    validated[key] = "B.A.(H) ECO"
                else:
                    validated[key] = value
                continue
            
            validated[key] = value
        
        # Cross-field consistency
        validated = self._cross_field_checks(validated)
        
        return validated
    
    def _cross_field_checks(self, fields: Dict[str, str]) -> Dict[str, str]:
        """Cross-validate fields for consistency."""
        # Build full student_name from components
        first = fields.get("first_name", "").strip()
        middle = fields.get("middle_name", "").strip()
        surname = fields.get("surname", "").strip()
        
        if first and surname and not fields.get("student_name"):
            parts = [first, middle, surname] if middle else [first, surname]
            fields["student_name"] = " ".join(parts)
        
        # Sync permanent address fields
        if fields.get("permanent_address") and not fields.get("permanent_state"):
            # Try to extract state from combined address
            states = ["Delhi", "Uttar Pradesh", "Haryana", "Rajasthan", "Punjab",
                       "Madhya Pradesh", "Bihar", "Maharashtra", "West Bengal",
                       "Karnataka", "Tamil Nadu", "Kerala", "Gujarat"]
            addr = fields["permanent_address"]
            for s in states:
                if s.lower() in addr.lower():
                    fields["permanent_state"] = s
                    break
        
        return fields
    
    def _calculate_confidence(self, fields: Dict[str, str]) -> float:
        """Calculate overall extraction confidence based on field coverage."""
        # Key fields that should always be present
        critical_fields = [
            "student_name", "first_name", "date_of_birth", "gender",
            "course", "academic_session", "du_portal_form_number",
            "phone_number", "email", "father_name", "mother_name",
        ]
        
        filled = sum(1 for f in critical_fields if fields.get(f, "").strip())
        coverage = filled / len(critical_fields)
        
        # Total fields filled
        total_filled = len([v for v in fields.values() if v and v.strip()])
        total_score = min(total_filled / 30.0, 1.0)  # 30 fields = full confidence
        
        return round(coverage * 0.6 + total_score * 0.4, 2)
    
    def is_available(self) -> bool:
        """Check if VLM dependencies are available."""
        try:
            import torch
            from transformers import Qwen2_5_VLForConditionalGeneration
            return True
        except ImportError:
            return False
    
    def get_provider_name(self) -> str:
        return "smart_document_ai"
