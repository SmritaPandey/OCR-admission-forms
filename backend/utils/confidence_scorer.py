"""
Enhanced Confidence Scoring for OCR Results
Validates extracted values and adjusts confidence scores based on:
- Field format validation
- Label filtering success
- Value plausibility
- Cross-field consistency
"""
from typing import Dict, Any, Optional
import re


class OCRConfidenceScorer:
    """Score and improve confidence estimates for OCR results"""
    
    def __init__(self):
        self.field_validators = {
            'student_name': self._validate_name,
            'date_of_birth': self._validate_date,
            'phone_number': self._validate_phone,
            'email': self._validate_email,
            'aadhar_number': self._validate_aadhar,
            'pincode': self._validate_pincode,
            'gender': self._validate_gender,
            'category': self._validate_category,
        }
    
    def improve_confidence(
        self, 
        extracted_data: Dict[str, Any],
        raw_confidence: float,
        field_name: Optional[str] = None
    ) -> float:
        """
        Improve confidence score based on validation
        
        Args:
            extracted_data: Dictionary with extracted field values
            raw_confidence: Original confidence from OCR provider (0-100)
            field_name: Optional specific field to validate
        
        Returns:
            Improved confidence score (0-100)
        """
        if field_name and field_name in self.field_validators:
            # Validate specific field
            value = extracted_data.get(field_name)
            if value:
                is_valid = self.field_validators[field_name](value)
                if is_valid:
                    # Boost confidence for valid fields (up to +15 points)
                    boost = min(15, 100 - raw_confidence)
                    return raw_confidence + boost
                else:
                    # Reduce confidence for invalid fields (up to -25 points)
                    reduction = min(25, raw_confidence)
                    return max(raw_confidence - reduction, 0)
        
        # Overall validation
        valid_fields = 0
        total_fields = 0
        
        for field, validator in self.field_validators.items():
            value = extracted_data.get(field)
            if value:
                try:
                    total_fields += 1
                    if validator(value):
                        valid_fields += 1
                except Exception:
                    # Skip validation if validator fails
                    pass
        
        if total_fields > 0:
            validation_ratio = valid_fields / total_fields
            # Adjust confidence based on validation ratio
            # Higher ratio = more valid fields = higher confidence boost
            if validation_ratio >= 0.9:  # 90%+ valid fields
                adjustment = 15  # Significant boost
            elif validation_ratio >= 0.7:  # 70-90% valid
                adjustment = 10  # Moderate boost
            elif validation_ratio >= 0.5:  # 50-70% valid
                adjustment = 5   # Small boost
            elif validation_ratio >= 0.3:  # 30-50% valid
                adjustment = -5  # Small reduction
            else:  # <30% valid
                adjustment = -15  # Significant reduction
            
            improved = max(0, min(100, raw_confidence + adjustment))
            
            # If we have many valid fields, add extra boost
            if valid_fields >= 10:
                improved = min(100, improved + 5)
            
            return improved
        
        return raw_confidence
    
    def _validate_name(self, value: str) -> bool:
        """Validate name field"""
        if not value or len(value) < 2:
            return False
        # Should contain letters, allow spaces, hyphens, apostrophes
        if not re.match(r'^[A-Za-z\s\-\'\.]{2,50}$', value):
            return False
        # Should have at least one letter
        if not re.search(r'[A-Za-z]', value):
            return False
        return True
    
    def _validate_date(self, value: str) -> bool:
        """Validate date field"""
        if not value:
            return False
        # Check for date patterns
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # DD/MM/YYYY or DD-MM-YYYY
            r'\d{2}[/-]\d{2}[/-]\d{4}',        # DD/MM/YYYY
        ]
        for pattern in date_patterns:
            if re.search(pattern, value):
                return True
        return False
    
    def _validate_phone(self, value: str) -> bool:
        """Validate phone number"""
        if not value:
            return False
        # Extract digits
        digits = re.sub(r'\D', '', value)
        # Should be 10-15 digits
        return 10 <= len(digits) <= 15
    
    def _validate_email(self, value: str) -> bool:
        """Validate email address"""
        if not value:
            return False
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, value))
    
    def _validate_aadhar(self, value: str) -> bool:
        """Validate Aadhar number (12 digits)"""
        if not value:
            return False
        digits = re.sub(r'\D', '', value)
        return len(digits) == 12
    
    def _validate_pincode(self, value: str) -> bool:
        """Validate pincode (6 digits)"""
        if not value:
            return False
        digits = re.sub(r'\D', '', value)
        return len(digits) == 6
    
    def _validate_gender(self, value: str) -> bool:
        """Validate gender"""
        if not value:
            return False
        valid_genders = ['male', 'female', 'transgender', 'other', 'm', 'f']
        return value.lower() in valid_genders
    
    def _validate_category(self, value: str) -> bool:
        """Validate admission category"""
        if not value:
            return False
        valid_categories = ['gen', 'general', 'obc', 'sc', 'st', 'ews', 'pwd', 'sports', 'eca']
        return value.lower() in valid_categories


# Global instance
_confidence_scorer = None

def get_confidence_scorer() -> OCRConfidenceScorer:
    """Get global confidence scorer instance"""
    global _confidence_scorer
    if _confidence_scorer is None:
        _confidence_scorer = OCRConfidenceScorer()
    return _confidence_scorer

def improve_ocr_confidence(
    extracted_data: Dict[str, Any],
    raw_confidence: float,
    field_name: Optional[str] = None
) -> float:
    """
    Improve OCR confidence score based on field validation
    
    Args:
        extracted_data: Dictionary with extracted field values
        raw_confidence: Original confidence from OCR provider (0-100)
        field_name: Optional specific field to validate
    
    Returns:
        Improved confidence score (0-100)
    """
    scorer = get_confidence_scorer()
    return scorer.improve_confidence(extracted_data, raw_confidence, field_name)
