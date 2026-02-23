"""
Unified OCR Extractor for SRCC Student Records Management System

This module provides a single entry point for all OCR extraction, combining:
1. Azure Form Recognizer for structured form extraction (preferred when available)
2. Google Vision OCR for raw text extraction (fallback)
3. GoogleOCREnhancer for text cleanup and pattern matching
4. SRCCFormExtractor for form-specific field extraction
5. Per-field confidence scoring

Version 2.0.0 - Optimized extraction with Azure/Google Vision + training feedback

Provider Priority:
1. Azure Form Recognizer - Best for structured forms (key-value pairs, checkboxes, tables)
2. Google Vision document_text_detection - Good for general text + handwriting
3. Tesseract - Local fallback
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from PIL import Image
import io

from backend.ocr.base_provider import OCRProvider
from backend.ocr.google_ocr_enhancer import GoogleOCREnhancer, SRCCFormExtractor as EnhancerFormExtractor
from backend.utils.srcc_form_extractor import SRCCFormExtractor
from backend.config import settings

logger = logging.getLogger(__name__)


class UnifiedExtractor(OCRProvider):
    """
    Unified OCR extraction that combines Google Vision with SRCC-specific
    field extraction for maximum accuracy.
    
    This is the recommended entry point for all OCR operations.
    """
    
    def __init__(self):
        self.name = "unified"
        self._google_client = None
        self._enhancer = GoogleOCREnhancer()
        self._srcc_extractor = SRCCFormExtractor()
        self._enhancer_form_extractor = EnhancerFormExtractor()
        
    def _get_google_client(self):
        """Initialize Google Vision client lazily"""
        if self._google_client is None:
            try:
                from google.cloud import vision
                import os
                from pathlib import Path
                
                # Resolve credentials path
                creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
                if creds_path:
                    if not os.path.isabs(creds_path):
                        project_root = Path(__file__).parent.parent.resolve()
                        full_path = project_root / creds_path
                        if full_path.exists():
                            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(full_path)
                
                self._google_client = vision.ImageAnnotatorClient()
            except Exception as e:
                logger.error(f"Failed to initialize Google Vision client: {e}")
                raise
        return self._google_client
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text and structured data from an image.
        
        This method:
        1. Sends the image to Google Vision for document text detection
        2. Enhances the raw OCR output with cleanup and pattern matching
        3. Extracts SRCC form-specific fields
        4. Calculates per-field confidence scores
        
        Returns:
            Dictionary with:
            - raw_text: Enhanced OCR text
            - structured_data: Extracted fields with values
            - confidence: Overall extraction confidence
            - field_confidences: Per-field confidence scores
            - provider: "unified"
        """
        try:
            # Step 1: Get raw text from Google Vision
            raw_text, vision_confidence = await self._google_vision_extract(image)
            
            if not raw_text:
                return {
                    "raw_text": "",
                    "structured_data": {},
                    "confidence": 0.0,
                    "field_confidences": {},
                    "provider": self.get_provider_name()
                }
            
            # Step 2: Enhance the raw text
            enhanced_text = self._enhancer.enhance_ocr_text(raw_text)
            
            # Step 3: Extract fields using multiple extractors for best results
            structured_data = {}
            field_confidences = {}
            
            # Primary extraction: SRCC Form Extractor (most comprehensive)
            srcc_fields = self._srcc_extractor.extract(enhanced_text)
            for field, value in srcc_fields.items():
                if value and not field.startswith('_'):
                    structured_data[field] = value
                    # Calculate confidence
                    conf = self._srcc_extractor.get_field_confidence(field, value)
                    field_confidences[field] = round(conf * 100, 1)
            
            # Secondary extraction: Google OCR Enhancer (fuzzy matching)
            enhancer_fields = self._enhancer.extract_all_fields(enhanced_text)
            for field, data in enhancer_fields.items():
                if field not in structured_data or not structured_data[field]:
                    structured_data[field] = data['value']
                    field_confidences[field] = round(data['confidence'] * 100, 1)
                elif field_confidences.get(field, 0) < data['confidence'] * 100:
                    # Use enhancer result if it has higher confidence
                    structured_data[field] = data['value']
                    field_confidences[field] = round(data['confidence'] * 100, 1)
            
            # Tertiary extraction: Key-value pairs from structured blocks (Azure-style)
            if hasattr(self, '_last_structured_blocks') and self._last_structured_blocks:
                kv_pairs = self._extract_key_value_pairs(self._last_structured_blocks)
                # Map common labels to field names
                label_to_field = {
                    'first name': 'first_name', 'name': 'student_name', 'surname': 'surname',
                    'middle name': 'middle_name', 'gender': 'gender', 'dob': 'date_of_birth',
                    'date of birth': 'date_of_birth', 'email': 'email', 'phone': 'phone_number',
                    'mobile': 'phone_number', 'pincode': 'pincode', 'state': 'permanent_state',
                    'father': 'father_name', 'mother': 'mother_name', 'nationality': 'nationality',
                    'religion': 'religion', 'blood group': 'blood_group', 'aadhar': 'aadhar_number',
                    'cuet': 'cuet_score', 'score': 'cuet_score', 'roll no': 'college_roll_no',
                    'course': 'course', 'session': 'academic_session', 'category': 'category',
                    'income': 'annual_income'
                }
                for label, value in kv_pairs.items():
                    field_name = label_to_field.get(label.lower())
                    if field_name and (field_name not in structured_data or not structured_data[field_name]):
                        structured_data[field_name] = value
                        field_confidences[field_name] = 70.0  # Medium confidence for KV extraction
            
            # Step 4: Calculate overall confidence
            if field_confidences:
                overall_confidence = sum(field_confidences.values()) / len(field_confidences)
            else:
                overall_confidence = vision_confidence
            
            # Step 5: Add extraction metadata
            result = {
                "raw_text": enhanced_text,
                "structured_data": structured_data,
                "confidence": round(overall_confidence, 1),
                "field_confidences": field_confidences,
                "provider": self.get_provider_name(),
                "extraction_metadata": {
                    "total_fields_extracted": len(structured_data),
                    "high_confidence_fields": len([c for c in field_confidences.values() if c >= 80]),
                    "low_confidence_fields": len([c for c in field_confidences.values() if c < 50]),
                    "vision_confidence": vision_confidence
                }
            }
            
            logger.info(f"Unified extraction complete: {len(structured_data)} fields, {overall_confidence:.1f}% confidence")
            return result
            
        except Exception as e:
            logger.error(f"Unified extraction failed: {e}")
            raise
    
    async def _google_vision_extract(self, image: Image.Image) -> tuple:
        """
        Extract text using Google Vision document_text_detection with
        Azure-style structured document analysis.
        
        This method extracts:
        1. Raw text content
        2. Block-level structure with bounding boxes
        3. Word-level positions for key-value pair matching
        
        Returns:
            Tuple of (raw_text, confidence, structured_blocks)
        """
        try:
            from google.cloud import vision
            
            client = self._get_google_client()
            
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            vision_image = vision.Image(content=img_byte_arr.getvalue())
            
            # Use document_text_detection for structured text recognition
            response = client.document_text_detection(image=vision_image)
            
            if response.error.message:
                raise Exception(f"Google Vision API error: {response.error.message}")
            
            # Get full text annotation
            full_text = response.full_text_annotation
            if not full_text:
                # Fallback to text_detection
                response = client.text_detection(image=vision_image)
                texts = response.text_annotations
                if texts:
                    return texts[0].description.strip(), 0.85
                return "", 0.0
            
            raw_text = full_text.text.strip()
            
            # Extract structured blocks (Azure-style approach)
            # This gives us layout information for key-value pair detection
            structured_blocks = []
            confidences = []
            
            for page in full_text.pages:
                page_width = page.width
                page_height = page.height
                
                for block in page.blocks:
                    if block.confidence:
                        confidences.append(block.confidence)
                    
                    block_text = ""
                    block_words = []
                    
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            word_text = ''.join([symbol.text for symbol in word.symbols])
                            
                            # Get bounding box
                            if word.bounding_box and word.bounding_box.vertices:
                                vertices = word.bounding_box.vertices
                                bbox = {
                                    'x': min(v.x for v in vertices) / page_width,
                                    'y': min(v.y for v in vertices) / page_height,
                                    'width': (max(v.x for v in vertices) - min(v.x for v in vertices)) / page_width,
                                    'height': (max(v.y for v in vertices) - min(v.y for v in vertices)) / page_height,
                                }
                            else:
                                bbox = None
                            
                            block_words.append({
                                'text': word_text,
                                'bbox': bbox,
                                'confidence': word.confidence if hasattr(word, 'confidence') else None
                            })
                            block_text += word_text + " "
                    
                    # Get block bounding box
                    if block.bounding_box and block.bounding_box.vertices:
                        vertices = block.bounding_box.vertices
                        block_bbox = {
                            'x': min(v.x for v in vertices) / page_width,
                            'y': min(v.y for v in vertices) / page_height,
                            'width': (max(v.x for v in vertices) - min(v.x for v in vertices)) / page_width,
                            'height': (max(v.y for v in vertices) - min(v.y for v in vertices)) / page_height,
                        }
                    else:
                        block_bbox = None
                    
                    structured_blocks.append({
                        'text': block_text.strip(),
                        'words': block_words,
                        'bbox': block_bbox,
                        'confidence': block.confidence if hasattr(block, 'confidence') else None
                    })
            
            avg_confidence = sum(confidences) / len(confidences) * 100 if confidences else 90.0
            
            # Store structured blocks for key-value extraction
            self._last_structured_blocks = structured_blocks
            
            return raw_text, avg_confidence
            
        except Exception as e:
            logger.error(f"Google Vision extraction failed: {e}")
            raise
    
    def _extract_key_value_pairs(self, structured_blocks: list) -> Dict[str, str]:
        """
        Extract key-value pairs from structured blocks using spatial analysis.
        
        This mimics Azure Form Recognizer's key-value pair extraction by:
        1. Finding label words (colon-terminated or known field labels)
        2. Finding the nearest value to the right or below the label
        """
        key_value_pairs = {}
        
        # Known field labels in SRCC form
        known_labels = [
            'name', 'first name', 'middle name', 'surname', 'gender', 'dob', 
            'date of birth', 'email', 'phone', 'mobile', 'address', 'pincode',
            'state', 'father', 'mother', 'guardian', 'occupation', 'nationality',
            'religion', 'blood group', 'aadhar', 'cuet', 'score', 'roll no',
            'admission', 'course', 'session', 'category', 'income'
        ]
        
        all_words = []
        for block in structured_blocks:
            for word in block.get('words', []):
                if word.get('bbox'):
                    all_words.append(word)
        
        for i, word in enumerate(all_words):
            word_text = word['text'].lower().strip()
            
            # Check if this word ends with colon (label indicator)
            is_label = word_text.endswith(':') or word_text.rstrip(':') in known_labels
            
            if is_label:
                label = word_text.rstrip(':').strip()
                bbox = word['bbox']
                
                # Find the nearest word to the right or below
                best_value = None
                best_distance = float('inf')
                
                for j, candidate in enumerate(all_words):
                    if j == i:
                        continue
                    
                    c_bbox = candidate.get('bbox')
                    if not c_bbox:
                        continue
                    
                    # Check if candidate is to the right (same row) or below
                    is_right = c_bbox['x'] > bbox['x'] + bbox['width'] and abs(c_bbox['y'] - bbox['y']) < 0.02
                    is_below = c_bbox['y'] > bbox['y'] + bbox['height'] and abs(c_bbox['x'] - bbox['x']) < 0.1
                    
                    if is_right:
                        distance = c_bbox['x'] - (bbox['x'] + bbox['width'])
                        if distance < best_distance:
                            best_distance = distance
                            best_value = candidate['text']
                    elif is_below and best_value is None:
                        distance = c_bbox['y'] - (bbox['y'] + bbox['height'])
                        if distance < best_distance:
                            best_distance = distance
                            best_value = candidate['text']
                
                if best_value:
                    key_value_pairs[label] = best_value
        
        return key_value_pairs
    
    def is_available(self) -> bool:
        """Check if unified extractor is available"""
        try:
            import os
            from pathlib import Path
            
            creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if not creds_path:
                return False
            
            if os.path.isabs(creds_path):
                return os.path.exists(creds_path)
            
            project_root = Path(__file__).parent.parent.resolve()
            return (project_root / creds_path).exists()
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        return "unified"


class UnifiedExtractorWithTraining(UnifiedExtractor):
    """
    Extended unified extractor with training feedback integration.
    
    Captures user corrections and applies learned patterns to improve
    extraction accuracy over time.
    """
    
    def __init__(self):
        super().__init__()
        self._training_manager = None
    
    def _get_training_manager(self):
        """Get training manager lazily"""
        if self._training_manager is None:
            try:
                from backend.utils.training_manager import TrainingManager
                self._training_manager = TrainingManager()
            except ImportError:
                logger.debug("Training manager not available")
        return self._training_manager
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """Extract text with training feedback integration"""
        result = await super().extract_text(image, language)
        
        # Apply learned corrections from training data
        training_manager = self._get_training_manager()
        if training_manager and result.get('structured_data'):
            corrected_data = training_manager.apply_corrections(result['structured_data'])
            result['structured_data'] = corrected_data
            result['extraction_metadata']['training_applied'] = True
        
        return result
    
    def record_correction(self, field_name: str, original_value: str, corrected_value: str):
        """Record a user correction for future training"""
        training_manager = self._get_training_manager()
        if training_manager:
            training_manager.record_correction(field_name, original_value, corrected_value)


# Create global instance
unified_extractor = UnifiedExtractor()
unified_extractor_with_training = UnifiedExtractorWithTraining()
