"""
AI-Powered Form Parser
Uses vision-language models to understand form structure and extract fields
"""
from typing import Dict, Any, Optional, List
import json
import re

class AIFormParser:
    """Parser using AI to understand form structure and extract fields"""
    
    def __init__(self):
        self.field_mappings = {
            # Basic Details
            'student_name': ['student_name', 'name', 'student name', 'applicant name', 'full name'],
            'date_of_birth': ['date_of_birth', 'dob', 'date of birth', 'birth date'],
            'gender': ['gender', 'sex'],
            'category': ['category', 'caste', 'reservation category'],
            'nationality': ['nationality', 'country'],
            'religion': ['religion'],
            'aadhar_number': ['aadhar', 'aadhaar', 'uid', 'aadhar_number', 'aadhar number'],
            'blood_group': ['blood_group', 'blood group', 'blood type'],
            
            # Address Details
            'permanent_address': ['permanent_address', 'permanent address'],
            'correspondence_address': ['correspondence_address', 'correspondence address', 'mailing address'],
            'pincode': ['pincode', 'pin code', 'pin'],
            'city': ['city'],
            'state': ['state'],
            
            # Contact Details
            'phone_number': ['phone', 'mobile', 'contact', 'phone_number', 'phone number'],
            'alternate_phone': ['alternate_phone', 'alternate phone', 'alt phone'],
            'email': ['email', 'e-mail', 'email_id', 'email address'],
            'emergency_contact_name': ['emergency_contact', 'emergency contact name'],
            'emergency_contact_phone': ['emergency_contact_phone', 'emergency phone'],
            
            # Guardian/Parent Details
            'father_name': ['father', "father's name", 'father name'],
            'father_occupation': ["father's occupation", 'father occupation'],
            'father_phone': ["father's phone", 'father phone'],
            'mother_name': ['mother', "mother's name", 'mother name'],
            'mother_occupation': ["mother's occupation", 'mother occupation'],
            'mother_phone': ["mother's phone", 'mother phone'],
            'guardian_name': ['guardian', "guardian's name", 'guardian name'],
            'guardian_relation': ['guardian_relation', 'guardian relation', 'relationship'],
            'guardian_phone': ["guardian's phone", 'guardian phone'],
            'annual_income': ['annual_income', 'annual income', 'income'],
            
            # Educational Qualifications
            'tenth_board': ['10th board', '10 board', 'tenth board', 'ssc board'],
            'tenth_year': ['10th year', '10 year', 'tenth year', 'ssc year'],
            'tenth_percentage': ['10th percentage', '10 percentage', 'tenth percentage', 'ssc percentage'],
            'tenth_school': ['10th school', '10 school', 'tenth school', 'ssc school'],
            'twelfth_board': ['12th board', '12 board', 'twelfth board', 'hsc board'],
            'twelfth_year': ['12th year', '12 year', 'twelfth year', 'hsc year'],
            'twelfth_percentage': ['12th percentage', '12 percentage', 'twelfth percentage', 'hsc percentage'],
            'twelfth_school': ['12th school', '12 school', 'twelfth school', 'hsc school'],
            'previous_qualification': ['qualification', 'education', 'degree', 'previous_qualification'],
            'graduation_details': ['graduation', 'degree details', 'bachelor'],
            
            # Course Application Details
            'course_applied': ['course', 'program', 'subject', 'course_applied', 'course applied'],
            'application_number': ['application_no', 'application number', 'app_no', 'app number'],
            'admission_date': ['admission_date', 'admission date', 'date of admission'],
        }
    
    def parse_from_ai_result(self, ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse structured data from AI OCR result
        
        Args:
            ai_result: Dictionary with 'structured_data' key containing AI-extracted fields
        
        Returns:
            Dictionary with normalized field names and values
        """
        structured_data = ai_result.get('structured_data', {})
        if not structured_data:
            # Try to extract from raw_text if structured_data is empty
            return self.parse_from_text(ai_result.get('raw_text', ''))
        
        parsed = {}
        
        # Normalize field names from AI result
        for ai_key, ai_value in structured_data.items():
            normalized_key = self._normalize_field_name(ai_key)
            if normalized_key:
                parsed[normalized_key] = self._clean_value(ai_value, normalized_key)
        
        return parsed
    
    def parse_from_text(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse from raw text (fallback method)
        
        Args:
            raw_text: Raw OCR text
        
        Returns:
            Dictionary with extracted fields
        """
        parsed = {}
        text_lower = raw_text.lower()
        
        # Try to extract fields using patterns
        for field_name, aliases in self.field_mappings.items():
            for alias in aliases:
                # Try to find field in text
                pattern = rf'{re.escape(alias)}[:\s]+([^\n]+)'
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value:
                        parsed[field_name] = self._clean_value(value, field_name)
                        break
        
        return parsed
    
    def _normalize_field_name(self, field_name: str) -> Optional[str]:
        """Normalize AI field name to standard field name"""
        field_name_lower = field_name.lower().strip()
        
        # Direct match
        for standard_field, aliases in self.field_mappings.items():
            if field_name_lower == standard_field:
                return standard_field
            if field_name_lower in [a.lower() for a in aliases]:
                return standard_field
        
        # Fuzzy match - check if field name contains any alias
        for standard_field, aliases in self.field_mappings.items():
            for alias in aliases:
                if alias.lower() in field_name_lower or field_name_lower in alias.lower():
                    return standard_field
        
        return None
    
    def _clean_value(self, value: Any, field_name: str) -> str:
        """Clean and normalize extracted value"""
        if value is None:
            return ""
        
        value = str(value).strip()
        
        # Remove common OCR artifacts
        value = re.sub(r'[^\w\s@.,\-+()\/]', '', value)
        value = re.sub(r'\s+', ' ', value)
        
        # Field-specific cleaning
        if field_name in ['student_name', 'guardian_name', 'father_name', 'mother_name',
                          'emergency_contact_name', 'city', 'state', 'nationality', 'religion']:
            value = ' '.join(word.capitalize() for word in value.split())
        
        elif field_name == 'email':
            value = value.lower().strip()
        
        elif field_name in ['phone_number', 'guardian_phone', 'father_phone', 'mother_phone',
                           'alternate_phone', 'emergency_contact_phone']:
            value = re.sub(r'[^\d+]', '', value)
        
        elif field_name in ['date_of_birth', 'admission_date']:
            value = re.sub(r'[^\d\/\-\.]', '', value)
        
        elif field_name in ['aadhar_number', 'pincode', 'application_number']:
            value = re.sub(r'[^\d\-]', '', value)
        
        elif field_name in ['gender', 'category', 'blood_group']:
            value = value.upper()
        
        return value.strip()
    
    def extract_checkboxes_from_ai_result(self, ai_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract checkbox information from AI result"""
        structured_data = ai_result.get('structured_data', {})
        checkboxes = []
        
        # Look for checkbox-related fields in structured data
        for key, value in structured_data.items():
            if 'checkbox' in key.lower() or 'checked' in key.lower():
                if isinstance(value, dict):
                    checkboxes.append({
                        'label': value.get('label', key),
                        'checked': value.get('checked', False),
                        'confidence': value.get('confidence', 0)
                    })
                elif isinstance(value, bool):
                    checkboxes.append({
                        'label': key,
                        'checked': value,
                        'confidence': 0
                    })
        
        return checkboxes

