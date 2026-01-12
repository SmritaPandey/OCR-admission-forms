"""
Empty Form Detection
Detect if a form is empty (template) vs filled (has student data)
"""
from typing import Dict, Any, Optional
from PIL import Image
import re


class EmptyFormDetector:
    """
    Detect if a form is empty (template) or has been filled out
    
    Empty forms typically have:
    - Only form labels/instructions
    - No handwritten text
    - No filled fields
    - Standard form structure text only
    """
    
    # Common form labels that appear in empty templates
    FORM_LABELS = [
        'name', 'student name', 'applicant name',
        'date of birth', 'dob', 'birth date',
        'gender', 'sex',
        'address', 'permanent address',
        'phone', 'mobile', 'contact',
        'email', 'e-mail',
        'father', 'mother', 'guardian',
        'qualification', 'education',
        'course', 'program',
        'application', 'enrollment',
        'signature', 'date'
    ]
    
    # Patterns that indicate filled forms
    FILLED_INDICATORS = [
        r'\d{10}',  # Phone numbers
        r'\d{4}[\s\-]?\d{4}[\s\-]?\d{4}',  # Aadhar numbers
        r'\d{6}',  # Pincodes
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email
        r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}',  # Dates
        r'[A-Z][a-z]+\s+[A-Z][a-z]+',  # Full names (2+ words)
    ]
    
    def detect_empty(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect if form is empty based on OCR results
        
        Args:
            ocr_result: OCR extraction result with raw_text
        
        Returns:
            Dictionary with:
                - is_empty: bool
                - confidence: float (0-1)
                - reason: str
                - suggestions: list of suggestions
        """
        raw_text = ocr_result.get('raw_text', '').strip().lower()
        
        if not raw_text or len(raw_text) < 50:
            return {
                'is_empty': True,
                'confidence': 0.95,
                'reason': 'Very little or no text extracted',
                'suggestions': [
                    'Form may be empty (template)',
                    'OCR may have failed - try different provider',
                    'Image quality may be too low'
                ]
            }
        
        # Count form labels vs filled content
        label_count = sum(1 for label in self.FORM_LABELS if label in raw_text)
        
        # Check for filled indicators
        filled_indicators_found = 0
        for pattern in self.FILLED_INDICATORS:
            if re.search(pattern, ocr_result.get('raw_text', ''), re.IGNORECASE):
                filled_indicators_found += 1
        
        # Calculate confidence
        text_length = len(raw_text)
        word_count = len(raw_text.split())
        
        # Heuristics for empty form
        is_likely_empty = (
            filled_indicators_found == 0 and  # No filled data patterns
            label_count > 5 and  # Many form labels (template structure)
            word_count < 100 and  # Relatively short text
            text_length < 500  # Not much content
        )
        
        # Heuristics for filled form
        is_likely_filled = (
            filled_indicators_found >= 2 or  # Multiple filled patterns
            word_count > 150 or  # Substantial text
            text_length > 800  # Lots of content
        )
        
        if is_likely_filled:
            return {
                'is_empty': False,
                'confidence': 0.85,
                'reason': 'Form appears to be filled with student data',
                'suggestions': []
            }
        elif is_likely_empty:
            return {
                'is_empty': True,
                'confidence': 0.80,
                'reason': 'Form appears to be empty template (only labels, no data)',
                'suggestions': [
                    'This looks like an empty form template',
                    'Students should fill this form before submission',
                    'No student data detected in OCR results'
                ]
            }
        else:
            # Uncertain
            return {
                'is_empty': None,  # Unknown
                'confidence': 0.50,
                'reason': 'Unable to determine if form is empty or filled',
                'suggestions': [
                    'Review OCR results manually',
                    'Check if form has been filled',
                    'Try different OCR provider for better results'
                ]
            }
    
    def get_empty_form_message(self) -> str:
        """Get user-friendly message for empty forms"""
        return (
            "⚠️ Empty Form Detected\n\n"
            "This appears to be an empty admission form template.\n"
            "The form should be filled out by students before submission.\n\n"
            "What to do:\n"
            "1. Ensure students fill out the form completely\n"
            "2. Scan the filled form clearly\n"
            "3. Upload the filled form for processing\n\n"
            "If this form is actually filled, try:\n"
            "- Using a different OCR provider\n"
            "- Improving image quality\n"
            "- Checking if handwriting is clear"
        )
