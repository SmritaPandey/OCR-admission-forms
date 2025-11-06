"""
Specialized form parser for SRCC DATA FORM patterns
Handles structured form extraction based on known form layouts
"""
import re
from typing import Dict, Any, Optional
from datetime import datetime

class SRCCFormParser:
    """Parser for SRCC DATA FORM format"""
    
    # Comprehensive field patterns for SRCC forms
    FIELD_PATTERNS = {
        # Basic Details
        'student_name': [
            r'(?:name|student\s+name|applicant\s+name|full\s+name|name\s+of\s+student|name\s+of\s+applicant)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+?)(?:\s+[Dd][Oo][Bb]|\n|phone|email|address|gender|$)',
            r'(?:name|student\s+name|applicant\s+name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+?)(?:\s+[Dd][Oo][Bb]|\n|phone|email|address|gender|$)',
            r'(?:name|student\s+name)[:\s]+([^\n]{3,50}?)(?:\s+[Dd][Oo][Bb]|\n|phone|email|gender|$)',
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*$',
        ],
        'date_of_birth': [
            r'(?:dob|date\s+of\s+birth|birth\s+date|born|date\s+of\s+birth)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            r'(?:dob|date\s+of\s+birth)[:\s]+(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
            r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        ],
        'gender': [
            r'(?:gender|sex)[:\s]+(male|female|other|m|f)',
            r'(?:gender|sex)[:\s]+([MF])',
        ],
        'category': [
            r'(?:category|caste)[:\s]+(general|obc|sc|st|other|gen|scheduled\s+caste|scheduled\s+tribe)',
            r'(?:category|caste)[:\s]+([A-Z]{3,})',
        ],
        'nationality': [
            r'(?:nationality|country)[:\s]+([A-Za-z\s]+)',
            r'(?:nationality)[:\s]+([A-Z][a-z]+)',
        ],
        'religion': [
            r'(?:religion)[:\s]+([A-Za-z\s]+)',
        ],
        'aadhar_number': [
            r'(?:aadhar|aadhaar|uid|aadhar\s+no|aadhaar\s+no|aadhar\s+number)[:\s]+(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})',
            r'(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})',
        ],
        'blood_group': [
            r'(?:blood\s+group|blood\s+type)[:\s]+([ABO][\+\-]?|AB[\+\-]?)',
            r'(?:blood\s+group)[:\s]+([A-Z]{1,3})',
        ],
        
        # Address Details
        'permanent_address': [
            r'(?:permanent\s+address|permanent\s+addr)[:\s]+([^\n]+(?:\n[^\n]+){0,4})',
            r'(?:permanent\s+address)[:\s]+([A-Za-z0-9\s,.-]+(?:\n[A-Za-z0-9\s,.-]+){0,3})',
        ],
        'correspondence_address': [
            r'(?:correspondence\s+address|correspondence\s+addr|mailing\s+address)[:\s]+([^\n]+(?:\n[^\n]+){0,4})',
            r'(?:correspondence\s+address)[:\s]+([A-Za-z0-9\s,.-]+(?:\n[A-Za-z0-9\s,.-]+){0,3})',
        ],
        'pincode': [
            r'(?:pincode|pin\s+code|pin)[:\s]+(\d{6})',
            r'(\d{6})',
        ],
        'city': [
            r'(?:city)[:\s]+([A-Za-z\s]+)',
        ],
        'state': [
            r'(?:state)[:\s]+([A-Za-z\s]+)',
        ],
        
        # Contact Details
        'phone_number': [
            r'(?:phone|mobile|contact|tel|phone\s+no|mobile\s+no|student\s+phone)[:\s]+([+\d\s\-()]{10,15})',
            r'(?:phone|mobile)[:\s]+(\d{10,15})',
            r'(\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        ],
        'alternate_phone': [
            r'(?:alternate\s+phone|alt\s+phone|alternate\s+mobile|secondary\s+phone)[:\s]+([+\d\s\-()]{10,15})',
            r'(?:alternate|alt)[:\s]+(\d{10,15})',
        ],
        'email': [
            r'(?:email|e-mail|email\s+id|email\s+address)[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        ],
        'emergency_contact_name': [
            r'(?:emergency\s+contact|emergency\s+contact\s+name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        ],
        'emergency_contact_phone': [
            r'(?:emergency\s+contact\s+phone|emergency\s+phone)[:\s]+([+\d\s\-()]{10,15})',
        ],
        
        # Guardian/Parent Details
        'father_name': [
            r'(?:father|father\'?s\s+name|father\s+name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'(?:father)[:\s]+([^\n]{3,50})',
        ],
        'father_occupation': [
            r'(?:father\'?s\s+occupation|father\s+occupation)[:\s]+([A-Za-z\s]+)',
        ],
        'father_phone': [
            r'(?:father\'?s\s+phone|father\s+phone|father\s+contact)[:\s]+([+\d\s\-()]{10,15})',
        ],
        'mother_name': [
            r'(?:mother|mother\'?s\s+name|mother\s+name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'(?:mother)[:\s]+([^\n]{3,50})',
        ],
        'mother_occupation': [
            r'(?:mother\'?s\s+occupation|mother\s+occupation)[:\s]+([A-Za-z\s]+)',
        ],
        'mother_phone': [
            r'(?:mother\'?s\s+phone|mother\s+phone|mother\s+contact)[:\s]+([+\d\s\-()]{10,15})',
        ],
        'guardian_name': [
            r'(?:guardian|guardian\'?s\s+name|guardian\s+name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'(?:guardian)[:\s]+([^\n]{3,50})',
        ],
        'guardian_relation': [
            r'(?:guardian\s+relation|guardian\s+relationship|relation)[:\s]+([A-Za-z\s]+)',
        ],
        'guardian_phone': [
            r'(?:guardian\'?s\s+phone|guardian\s+phone|guardian\s+contact)[:\s]+([+\d\s\-()]{10,15})',
        ],
        'annual_income': [
            r'(?:annual\s+income|income|family\s+income)[:\s]+([\d,\.]+)',
            r'(?:annual\s+income)[:\s]+([\d]+)',
        ],
        
        # Educational Qualifications
        'tenth_board': [
            r'(?:10th\s+board|10\s+board|tenth\s+board|ssc\s+board)[:\s]+([A-Za-z\s]+)',
        ],
        'tenth_year': [
            r'(?:10th\s+year|10\s+year|tenth\s+year|ssc\s+year)[:\s]+(\d{4})',
        ],
        'tenth_percentage': [
            r'(?:10th\s+percentage|10\s+percentage|tenth\s+percentage|ssc\s+percentage|10th\s+%)[:\s]+([\d\.]+)',
        ],
        'tenth_school': [
            r'(?:10th\s+school|10\s+school|tenth\s+school|ssc\s+school)[:\s]+([^\n]{3,100})',
        ],
        'twelfth_board': [
            r'(?:12th\s+board|12\s+board|twelfth\s+board|hsc\s+board|intermediate\s+board)[:\s]+([A-Za-z\s]+)',
        ],
        'twelfth_year': [
            r'(?:12th\s+year|12\s+year|twelfth\s+year|hsc\s+year|intermediate\s+year)[:\s]+(\d{4})',
        ],
        'twelfth_percentage': [
            r'(?:12th\s+percentage|12\s+percentage|twelfth\s+percentage|hsc\s+percentage|12th\s+%)[:\s]+([\d\.]+)',
        ],
        'twelfth_school': [
            r'(?:12th\s+school|12\s+school|twelfth\s+school|hsc\s+school|intermediate\s+school)[:\s]+([^\n]{3,100})',
        ],
        'previous_qualification': [
            r'(?:qualification|education|degree|diploma|previous\s+qualification|educational\s+qualification)[:\s]+([^\n]{3,100})',
            r'(?:qualification|education)[:\s]+([A-Za-z\s&.,]+)',
        ],
        'graduation_details': [
            r'(?:graduation|degree\s+details|bachelor)[:\s]+([^\n]{3,200})',
        ],
        
        # Course Application Details
        'course_applied': [
            r'(?:course|program|subject|stream|course\s+applied|program\s+applied|course\s+of\s+study)[:\s]+([^\n]{3,100})',
            r'(?:course|program)[:\s]+([A-Za-z\s&]+)',
        ],
        'application_number': [
            r'(?:application\s+no|application\s+number|app\s+no|app\s+number)[:\s]+([A-Z0-9\-]+)',
        ],
        'admission_date': [
            r'(?:admission\s+date|date\s+of\s+admission)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        ],
    }
    
    def parse(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse OCR text and extract structured information
        
        Args:
            raw_text: Raw OCR extracted text
        
        Returns:
            Dictionary with extracted fields
        """
        parsed = {}
        text = raw_text
        text_lower = text.lower()
        
        # Normalize text - remove extra spaces, handle line breaks
        text = re.sub(r'\s+', ' ', text)
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        # Extract each field
        for field_name, patterns in self.FIELD_PATTERNS.items():
            value = self._extract_field(text, text_lower, lines, patterns, field_name)
            if value:
                parsed[field_name] = value
        
        return parsed
    
    def _extract_field(self, text: str, text_lower: str, lines: list, 
                      patterns: list, field_name: str) -> Optional[str]:
        """Extract a single field using multiple patterns"""
        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1) if match.lastindex >= 1 else match.group(0)
                    if value:
                        value = self._clean_value(value, field_name)
                        if self._validate_value(value, field_name):
                            return value
            except Exception:
                continue
        
        return None
    
    def _clean_value(self, value: str, field_name: str) -> str:
        """Clean and normalize extracted value"""
        value = value.strip()
        
        # Remove common OCR artifacts
        value = re.sub(r'[^\w\s@.,\-+()\/]', '', value)
        value = re.sub(r'\s+', ' ', value)
        
        # Field-specific cleaning
        if field_name in ['student_name', 'guardian_name', 'father_name', 'mother_name', 
                          'emergency_contact_name', 'city', 'state', 'nationality', 'religion']:
            # Title case for names
            value = ' '.join(word.capitalize() for word in value.split())
        
        elif field_name == 'email':
            value = value.lower().strip()
        
        elif field_name in ['phone_number', 'guardian_phone', 'father_phone', 'mother_phone',
                           'alternate_phone', 'emergency_contact_phone']:
            # Remove non-digit characters except +
            value = re.sub(r'[^\d+]', '', value)
        
        elif field_name in ['date_of_birth', 'admission_date']:
            # Normalize date format
            value = re.sub(r'[^\d\/\-\.]', '', value)
        
        elif field_name in ['permanent_address', 'correspondence_address', 'tenth_school', 
                           'twelfth_school', 'previous_qualification', 'graduation_details']:
            # Clean address but keep structure
            value = re.sub(r'\s+', ' ', value)
            value = value.strip(',')
        
        elif field_name in ['aadhar_number', 'pincode', 'application_number']:
            # Remove spaces, keep numbers and hyphens
            value = re.sub(r'[^\d\-]', '', value)
        
        elif field_name in ['tenth_percentage', 'twelfth_percentage', 'annual_income']:
            # Keep numbers and decimal points
            value = re.sub(r'[^\d\.]', '', value)
        
        elif field_name in ['gender', 'category', 'blood_group']:
            # Uppercase
            value = value.upper()
        
        return value.strip()
    
    def _validate_value(self, value: str, field_name: str) -> bool:
        """Validate extracted value"""
        if not value or len(value) < 2:
            return False
        
        if field_name in ['student_name', 'guardian_name', 'father_name', 'mother_name', 
                         'emergency_contact_name', 'city', 'state']:
            # Name should be 2-50 chars, contain letters
            return 2 <= len(value) <= 50 and re.search(r'[a-zA-Z]', value)
        
        elif field_name == 'email':
            # Email validation
            return '@' in value and '.' in value.split('@')[1] and len(value) >= 5
        
        elif field_name in ['phone_number', 'guardian_phone', 'father_phone', 'mother_phone',
                           'alternate_phone', 'emergency_contact_phone']:
            # Phone should be 10-15 digits
            digits = re.sub(r'\D', '', value)
            return 10 <= len(digits) <= 15
        
        elif field_name in ['date_of_birth', 'admission_date']:
            # Date should be 8-12 chars
            return 8 <= len(value) <= 12
        
        elif field_name in ['permanent_address', 'correspondence_address']:
            # Address should be at least 10 chars
            return len(value) >= 10
        
        elif field_name == 'aadhar_number':
            # Aadhar should be 12 digits
            digits = re.sub(r'\D', '', value)
            return len(digits) == 12
        
        elif field_name == 'pincode':
            # Pincode should be 6 digits
            digits = re.sub(r'\D', '', value)
            return len(digits) == 6
        
        elif field_name in ['course_applied', 'previous_qualification', 'tenth_school', 
                           'twelfth_school']:
            # Should be 3-100 chars
            return 3 <= len(value) <= 100
        
        elif field_name in ['tenth_percentage', 'twelfth_percentage']:
            # Percentage should be 0-100
            try:
                pct = float(value)
                return 0 <= pct <= 100
            except:
                return False
        
        return True
    
    def parse_with_context(self, raw_text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Parse with additional context (e.g., form type, known patterns)
        
        Args:
            raw_text: Raw OCR text
            context: Additional context like form type, known field positions
        
        Returns:
            Dictionary with extracted fields
        """
        parsed = self.parse(raw_text)
        
        # If context provided, use it to improve extraction
        if context:
            # Can add form-specific logic here
            pass
        
        return parsed

def parse_form_text(raw_text: str, form_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Main function to parse form text
    
    Args:
        raw_text: Raw OCR extracted text
        form_type: Optional form type identifier (e.g., 'srcc')
    
    Returns:
        Dictionary with extracted fields
    """
    parser = SRCCFormParser()
    return parser.parse(raw_text)
