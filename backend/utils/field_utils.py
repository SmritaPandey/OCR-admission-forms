"""
Field Utilities - Quick wins for OCR field extraction improvements.

Provides:
1. Additional field patterns for commonly missed fields
2. Enhanced garbage detection
3. Field name synonyms for flexible matching
4. Date format normalization
5. Value cleanup and formatting
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ==============================================================================
# Field Synonyms - Map various label names to standard field names
# ==============================================================================

FIELD_SYNONYMS = {
    # Student name variations
    'student_name': [
        'name', 'candidate name', 'applicant name', 'full name',
        'name of student', 'name of candidate', 'student\'s name',
        'name in block letters', 'name (in block letters)'
    ],
    
    # Contact variations
    'phone_number': [
        'mobile', 'contact', 'phone no', 'mobile no', 'phone number',
        'mobile number', 'contact number', 'student mobile',
        'contact no', 'cell number', 'cell no', 'phone'
    ],
    'alternate_phone': [
        'alternate mobile', 'alt phone', 'alternate contact',
        'secondary phone', 'other mobile', 'alternate phone number'
    ],
    'email': [
        'e-mail', 'email id', 'email address', 'e-mail address',
        'email id', 'mail id', 'student email'
    ],
    
    # Address variations
    'permanent_address': [
        'address', 'residential address', 'home address',
        'present address', 'permanent addr'
    ],
    'correspondence_address': [
        'mailing address', 'local address', 'communication address',
        'postal address', 'correspondence addr', 'local address for correspondence'
    ],
    'pincode': [
        'pin', 'pin code', 'postal code', 'zip code', 'zip'
    ],
    'state': [
        'permanent state', 'state/ut', 'state name'
    ],
    
    # Family variations
    'father_name': [
        'father', 'father\'s name', 'name of father',
        'father name', 'dad name', 'papa name'
    ],
    'mother_name': [
        'mother', 'mother\'s name', 'name of mother',
        'mother name', 'mom name', 'mummy name'
    ],
    'guardian_name': [
        'guardian', 'guardian\'s name', 'name of guardian',
        'local guardian', 'local guardian\'s name'
    ],
    
    # Academic variations
    'course_applied': [
        'course', 'program', 'programme', 'stream',
        'course applied for', 'course name'
    ],
    'enrollment_number': [
        'enrolment no', 'enrollment no', 'roll no', 'roll number',
        'college roll no', 'university roll no', 'registration number'
    ],
    'application_number': [
        'application no', 'app no', 'form number', 'form no',
        'du portal form number', 'portal form number'
    ],
    
    # Dates
    'date_of_birth': [
        'dob', 'birth date', 'd.o.b', 'd.o.b.', 'born on',
        'date of birth', 'birthdate'
    ],
    'date_of_admission': [
        'admission date', 'date of joining', 'joining date'
    ],
    
    # Identity
    'aadhar_number': [
        'aadhar', 'aadhaar', 'uid', 'aadhaar no', 'aadhar no',
        'uid number', 'aadhaar number'
    ],
    
    # Occupation
    'father_occupation': [
        'father\'s occupation', 'occupation of father',
        'father profession'
    ],
    'mother_occupation': [
        'mother\'s occupation', 'occupation of mother',
        'mother profession'
    ],
}


def get_standard_field_name(label: str) -> Optional[str]:
    """
    Get the standard field name for a label using synonyms.
    
    Args:
        label: Label text from the form
        
    Returns:
        Standard field name or None if not found
    """
    label_lower = label.lower().strip()
    
    # Check direct match with standard field names
    for field_name in FIELD_SYNONYMS.keys():
        if field_name == label_lower:
            return field_name
    
    # Check against synonyms
    for field_name, synonyms in FIELD_SYNONYMS.items():
        if label_lower in synonyms:
            return field_name
        # Also check for partial match
        for syn in synonyms:
            if syn in label_lower or label_lower in syn:
                return field_name
    
    return None


# ==============================================================================
# Additional Field Patterns
# ==============================================================================

ADDITIONAL_PATTERNS = {
    # Alternative phone number
    'alternate_phone': [
        r'(?:alternate|alt|secondary|other)\s*(?:phone|mobile|contact)[:\s]+([6-9]\d{9})',
        r'(?:phone|mobile)\s*2[:\s]+([6-9]\d{9})',
    ],
    
    # Emergency contact
    'emergency_contact_name': [
        r'(?:emergency\s+contact|in\s+case\s+of\s+emergency)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
    ],
    'emergency_contact_phone': [
        r'(?:emergency\s+(?:phone|contact|mobile))[:\s]+([6-9]\d{9})',
    ],
    
    # Parent occupation details
    'father_designation': [
        r"(?:father'?s?\s+)?designation[:\s]+([A-Za-z\s]+?)(?:\n|$)",
    ],
    'mother_designation': [
        r"(?:mother'?s?\s+)?designation[:\s]+([A-Za-z\s]+?)(?:\n|$)",
    ],
    'father_organization': [
        r"(?:father'?s?\s+)?organization[:\s]+([^\n]+)",
    ],
    'mother_organization': [
        r"(?:mother'?s?\s+)?organization[:\s]+([^\n]+)",
    ],
    
    # Hindi medium preference
    'hindi_medium': [
        r'(?:hindi\s+medium|teach.*hindi)[:\s]*(yes|no)',
        r'(?:hindi\s+medium)[:\s]*(?:✓|✔|☑)\s*(yes|no)?',
    ],
    
    # Below poverty line
    'below_poverty_line': [
        r'(?:below\s+poverty\s+line|bpl)[:\s]*(yes|no)',
        r'(?:bpl)[:\s]*(?:✓|✔|☑)\s*(yes|no)?',
    ],
    
    # Minority status
    'minority_status': [
        r'(?:minority|belongs\s+to\s+minority)[:\s]*(yes|no|muslim|jain|sikh|christian|buddhist)',
    ],
    
    # DU Enrollment Number
    'du_enrollment_number': [
        r'(?:du|delhi\s+university)\s+(?:enrollment|enrolment)\s+no\.?[:\s]*(\d+)',
        r'(?:enrollment|enrolment)\s+no\.?[:\s]*(\d+)',
    ],
    
    # Certificate details for reserved categories
    'certificate_authority': [
        r'(?:issuing\s+authority|certificate\s+authority)[:\s]+([^\n]+)',
    ],
    'certificate_number': [
        r'(?:certificate\s+no|cert\.?\s+no)[:\s]+([A-Z0-9\-\/]+)',
    ],
    'certificate_date': [
        r'(?:date\s+of\s+issue|certificate\s+date)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
    ],
}


def extract_with_additional_patterns(text: str) -> Dict[str, Any]:
    """
    Extract fields using additional patterns for commonly missed fields.
    
    Args:
        text: Raw OCR text
        
    Returns:
        Dictionary of extracted fields
    """
    result = {}
    
    for field_name, patterns in ADDITIONAL_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value and len(value) >= 2:
                    result[field_name] = value
                    break
    
    return result


# ==============================================================================
# Enhanced Garbage Detection
# ==============================================================================

GARBAGE_PATTERNS = [
    # Form instructions
    r'^please\s+tick',
    r'^please\s+fill',
    r'^please\s+enter',
    r'^please\s+write',
    r'^if\s+different',
    r'^if\s+applicable',
    r'^if\s+yes',
    r'^if\s+no',
    r'^mandatory',
    r'^optional',
    r'^self\s+attested',
    r'^attach',
    
    # Field numbers and labels only
    r'^\d+\.\s*$',
    r'^\(\w\)\s*$',
    r'^name\s*$',
    r'^address\s*$',
    r'^phone\s*$',
    r'^email\s*$',
    r'^date\s*$',
    r'^gender\s*$',
    r'^category\s*$',
    r'^details\s*$',
    r'^occupation\s*$',
    r'^designation\s*$',
    r'^organization\s*$',
    r'^specify\s*$',
    
    # Form layout text
    r'^tick\s*\(',
    r'^fill\s+in',
    r'^write\s+',
    r'^enter\s+',
    r'^block\s+letters',
    r'^in\s+block\s+letters',
    r'^of\s+the\s+student',
    r'^of\s+student',
    r'^particulars',
    r'^information',
    
    # Common OCR errors from form labels
    r'^first\s+name$',
    r'^middle\s+name$',
    r'^surname$',
    r'^last\s+name$',
    r'^permanent$',
    r'^correspondence$',
    r'^local$',
    r'^contact\s+numbers?$',
    r'^mother\'?s?\s*$',
    r'^father\'?s?\s*$',
    r'^guardian\'?s?\s*$',
    
    # Table headers
    r'^sl\.?\s*no\.?$',
    r'^subjects?$',
    r'^score$',
    r'^total$',
    r'^marks$',
    
    # Section headers
    r'^student\'?s?\s+data\s+form$',
    r'^declaration',
    r'^undertaking',
    r'^documents\s+required',
]


def is_garbage(value: str) -> bool:
    """
    Check if a value is garbage (form label, instruction, etc.)
    
    Args:
        value: Value to check
        
    Returns:
        True if value appears to be garbage
    """
    if not value or len(str(value).strip()) < 2:
        return True
    
    value_lower = str(value).lower().strip()
    
    for pattern in GARBAGE_PATTERNS:
        if re.match(pattern, value_lower, re.IGNORECASE):
            return True
    
    return False


def clean_garbage(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove garbage values from extracted data.
    
    Args:
        data: Dictionary of extracted fields
        
    Returns:
        Cleaned dictionary with garbage removed
    """
    return {
        key: value for key, value in data.items()
        if not is_garbage(str(value))
    }


# ==============================================================================
# Date Format Normalization
# ==============================================================================

# Month name mappings
MONTH_NAMES = {
    'january': '01', 'jan': '01',
    'february': '02', 'feb': '02',
    'march': '03', 'mar': '03',
    'april': '04', 'apr': '04',
    'may': '05',
    'june': '06', 'jun': '06',
    'july': '07', 'jul': '07',
    'august': '08', 'aug': '08',
    'september': '09', 'sep': '09', 'sept': '09',
    'october': '10', 'oct': '10',
    'november': '11', 'nov': '11',
    'december': '12', 'dec': '12',
}


def normalize_date(value: str) -> Optional[str]:
    """
    Convert various date formats to DD/MM/YYYY.
    
    Handles:
    - 23/04/2006
    - 23-04-2006
    - 23.04.2006
    - 23 April 2006
    - 2006-04-23 (ISO format)
    - April 23, 2006
    - 23rd April 2006
    
    Args:
        value: Date string in various formats
        
    Returns:
        Normalized date string (DD/MM/YYYY) or None if parsing fails
    """
    if not value:
        return None
    
    value = str(value).strip()
    
    # Try DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    match = re.match(r'^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})$', value)
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = '20' + year if int(year) < 50 else '19' + year
        return f"{int(day):02d}/{int(month):02d}/{year}"
    
    # Try YYYY-MM-DD (ISO format)
    match = re.match(r'^(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})$', value)
    if match:
        year, month, day = match.groups()
        return f"{int(day):02d}/{int(month):02d}/{year}"
    
    # Try "23 April 2006" or "23rd April 2006"
    match = re.match(
        r'^(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})$', 
        value, re.IGNORECASE
    )
    if match:
        day, month_name, year = match.groups()
        month = MONTH_NAMES.get(month_name.lower())
        if month:
            return f"{int(day):02d}/{month}/{year}"
    
    # Try "April 23, 2006"
    match = re.match(
        r'^([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})$',
        value, re.IGNORECASE
    )
    if match:
        month_name, day, year = match.groups()
        month = MONTH_NAMES.get(month_name.lower())
        if month:
            return f"{int(day):02d}/{month}/{year}"
    
    # Try compact format "23042006"
    match = re.match(r'^(\d{2})(\d{2})(\d{4})$', value)
    if match:
        day, month, year = match.groups()
        if 1 <= int(day) <= 31 and 1 <= int(month) <= 12:
            return f"{day}/{month}/{year}"
    
    return None


def normalize_phone(value: str) -> Optional[str]:
    """
    Normalize phone number to 10 digits.
    
    Handles:
    - +91 9876543210
    - 91-9876543210
    - 9876543210
    - 98765 43210
    
    Args:
        value: Phone number in various formats
        
    Returns:
        10-digit phone number or None
    """
    if not value:
        return None
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(value))
    
    # Remove country code if present
    if len(digits) > 10:
        if digits.startswith('91'):
            digits = digits[2:]
        elif digits.startswith('0'):
            digits = digits[1:]
    
    # Validate
    if len(digits) == 10 and digits[0] in '6789':
        return digits
    
    return None


def normalize_pincode(value: str) -> Optional[str]:
    """
    Normalize pincode to 6 digits.
    
    Args:
        value: Pincode in various formats
        
    Returns:
        6-digit pincode or None
    """
    if not value:
        return None
    
    digits = re.sub(r'\D', '', str(value))
    
    if len(digits) == 6 and digits[0] in '12345678':
        return digits
    
    return None


def normalize_email(value: str) -> Optional[str]:
    """
    Normalize email address.
    
    Handles:
    - Spaces in domain
    - Wrong case
    
    Args:
        value: Email address
        
    Returns:
        Normalized email or None
    """
    if not value:
        return None
    
    # Remove spaces, convert to lowercase
    email = re.sub(r'\s+', '', str(value)).lower()
    
    # Fix common OCR errors
    email = email.replace('. com', '.com')
    email = email.replace('.corn', '.com')
    email = email.replace(',com', '.com')
    email = email.replace('@gmail corn', '@gmail.com')
    
    # Validate format
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return email
    
    return None


def normalize_name(value: str) -> Optional[str]:
    """
    Normalize a name to proper title case.
    
    Args:
        value: Name string
        
    Returns:
        Title case name or None
    """
    if not value or is_garbage(value):
        return None
    
    # Remove extra spaces
    name = ' '.join(str(value).split())
    
    # Remove non-letter characters except spaces
    name = re.sub(r'[^A-Za-z\s]', '', name)
    
    if len(name) < 2:
        return None
    
    # Title case
    return name.title()


def normalize_all_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply all normalization to form data.
    
    Args:
        data: Raw extracted data
        
    Returns:
        Normalized data
    """
    result = {}
    
    for field, value in data.items():
        if value is None:
            continue
        
        value_str = str(value).strip()
        
        # Skip garbage
        if is_garbage(value_str):
            continue
        
        # Apply field-specific normalization
        if field in ['date_of_birth', 'date_of_admission', 'certificate_date']:
            normalized = normalize_date(value_str)
            if normalized:
                result[field] = normalized
        
        elif field in ['phone_number', 'alternate_phone', 'father_phone', 
                       'mother_phone', 'guardian_phone', 'emergency_contact_phone']:
            normalized = normalize_phone(value_str)
            if normalized:
                result[field] = normalized
        
        elif field in ['pincode', 'correspondence_pincode']:
            normalized = normalize_pincode(value_str)
            if normalized:
                result[field] = normalized
        
        elif field == 'email':
            normalized = normalize_email(value_str)
            if normalized:
                result[field] = normalized
        
        elif field in ['student_name', 'father_name', 'mother_name', 
                       'guardian_name', 'emergency_contact_name']:
            normalized = normalize_name(value_str)
            if normalized:
                result[field] = normalized
        
        else:
            # Keep as-is if no specific normalization
            result[field] = value_str
    
    return result
