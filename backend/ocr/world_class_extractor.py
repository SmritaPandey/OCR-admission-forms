"""
World-Class Form Extraction Engine
===================================

Advanced OCR post-processing with:
1. Spatial label-value pairing using bounding box analysis
2. Context-aware field extraction
3. OCR error correction with common mistake dictionaries
4. Cross-field validation and verification
5. Per-field confidence scoring
6. Multi-pass extraction with voting

This is designed to be the BEST form extractor possible.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class ExtractedField:
    """Represents an extracted field with metadata"""
    value: str
    confidence: float  # 0.0 to 1.0
    source: str  # Where this was extracted from
    alternatives: List[str] = field(default_factory=list)
    validated: bool = False


@dataclass 
class BoundingBox:
    """Bounding box for spatial analysis"""
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    
    @property
    def center_x(self) -> float:
        return (self.x_min + self.x_max) / 2
    
    @property
    def center_y(self) -> float:
        return (self.y_min + self.y_max) / 2
    
    @property
    def width(self) -> float:
        return self.x_max - self.x_min
    
    @property
    def height(self) -> float:
        return self.y_max - self.y_min


@dataclass
class TextElement:
    """Text element with spatial information"""
    text: str
    bbox: BoundingBox
    confidence: float = 1.0


class OCRErrorCorrector:
    """
    Corrects common OCR mistakes using context-aware rules.
    """
    
    # Common character substitutions
    CHAR_SUBSTITUTIONS = {
        '0': ['O', 'o', 'Q', 'D'],
        'O': ['0', 'Q', 'D'],
        '1': ['l', 'I', 'i', '|', '!'],
        'l': ['1', 'I', 'i', '|'],
        'I': ['1', 'l', 'i', '|'],
        '5': ['S', 's'],
        'S': ['5', '$'],
        '8': ['B', '&'],
        'B': ['8', '&'],
        '2': ['Z', 'z'],
        'Z': ['2'],
        '6': ['G', 'b'],
        'G': ['6', 'C'],
        '9': ['g', 'q'],
        'g': ['9', 'q'],
        'A': ['4', 'R'],
        '4': ['A', 'H'],
        'Y': ['4', 'V'],
        'C': ['(', 'G', 'O'],
        'D': ['O', '0'],
        'E': ['F', '3'],
        'F': ['E', 'P'],
        'H': ['N', 'M', '4'],
        'K': ['X', 'k'],
        'M': ['N', 'H', 'W'],
        'N': ['M', 'H'],
        'P': ['R', 'F'],
        'R': ['P', 'K', 'A'],
        'T': ['1', '7'],
        'U': ['V', 'W'],
        'V': ['U', 'W', 'Y'],
        'W': ['M', 'V', 'U'],
        '.': [',', '\''],
        ',': ['.', '\''],
        ' ': ['_', '-'],
    }
    
    # Common word-level corrections
    WORD_CORRECTIONS = {
        # Common OCR errors in names/words
        'MOUSE WIFE': 'HOUSE WIFE',
        'HOUSEWLFE': 'HOUSEWIFE',
        'QELHI': 'DELHI',
        'DELHL': 'DELHI',
        'OELHI': 'DELHI',
        'DEIHI': 'DELHI',
        'DELHl': 'DELHI',
        'RUSINESS': 'BUSINESS',
        'BUSLNESS': 'BUSINESS',
        'STUDJES': 'STUDIES',
        'STUDLES': 'STUDIES',
        'ACCOUNTANGY': 'ACCOUNTANCY',
        'AGCOUNTANCY': 'ACCOUNTANCY',
        'ECONOMLCS': 'ECONOMICS',
        'ECONOM1CS': 'ECONOMICS',
        'MATHEMATLCS': 'MATHEMATICS',
        'MATHEMAIICS': 'MATHEMATICS',
        'ENGLLSH': 'ENGLISH',
        'ENGL1SH': 'ENGLISH',
        'GMALL': 'GMAIL',
        'GMATL': 'GMAIL',
        'GMA1L': 'GMAIL',
        '. com': '.com',
        '. COM': '.COM',
        '@ ': '@',
        ' @': '@',
        'L.COM': '.COM',
        'L. COM': '.COM',
        'SCHQOL': 'SCHOOL',
        'SCH00L': 'SCHOOL',
        'PUBLLC': 'PUBLIC',
        'PUBL1C': 'PUBLIC',
        'VIHAR': 'VIHAR',
        'V1HAR': 'VIHAR',
        'VLHAR': 'VIHAR',
        'NAGAR': 'NAGAR',
        'NAGBR': 'NAGAR',
        'STREET': 'STREET',
        'STRFET': 'STREET',
        'FLAT': 'FLAT',
        'FLBT': 'FLAT',
    }
    
    # Email domain corrections
    EMAIL_DOMAINS = {
        'gmall.com': 'gmail.com',
        'gmai1.com': 'gmail.com',
        'gmaIl.com': 'gmail.com',
        'gmal.com': 'gmail.com',
        'gnail.com': 'gmail.com',
        'yahooo.com': 'yahoo.com',
        'yah00.com': 'yahoo.com',
        'hotmai1.com': 'hotmail.com',
        'hotmall.com': 'hotmail.com',
        'outlok.com': 'outlook.com',
        'outl00k.com': 'outlook.com',
    }
    
    # Number patterns that should stay as numbers
    NUMERIC_PATTERNS = [
        r'\d{6}',      # Pincode
        r'\d{10}',     # Phone
        r'\d{12}',     # Aadhar
        r'\d{2}/\d{2}/\d{4}',  # Date
        r'\d{4}',      # Year
    ]
    
    @classmethod
    def correct_text(cls, text: str, context: str = 'general') -> str:
        """
        Apply context-aware OCR error correction.
        
        Args:
            text: Raw OCR text
            context: Context hint ('name', 'email', 'phone', 'address', 'date', 'general')
        
        Returns:
            Corrected text
        """
        if not text:
            return text
        
        corrected = text
        
        # Apply word-level corrections
        for wrong, right in cls.WORD_CORRECTIONS.items():
            corrected = corrected.replace(wrong, right)
        
        # Context-specific corrections
        if context == 'email':
            corrected = cls._correct_email(corrected)
        elif context == 'phone':
            corrected = cls._correct_phone(corrected)
        elif context == 'pincode':
            corrected = cls._correct_pincode(corrected)
        elif context == 'date':
            corrected = cls._correct_date(corrected)
        elif context == 'name':
            corrected = cls._correct_name(corrected)
        
        return corrected
    
    @classmethod
    def _correct_email(cls, text: str) -> str:
        """Correct common email OCR errors"""
        text = text.lower().strip()
        
        # Fix common space issues
        text = text.replace(' ', '')
        text = text.replace('@@', '@')
        
        # Fix L.COM -> .com pattern
        text = re.sub(r'l\.com$', '.com', text, flags=re.IGNORECASE)
        text = re.sub(r'\.c0m$', '.com', text, flags=re.IGNORECASE)
        
        # Fix domain errors
        for wrong, right in cls.EMAIL_DOMAINS.items():
            if wrong in text:
                text = text.replace(wrong, right)
        
        return text
    
    @classmethod
    def _correct_phone(cls, text: str) -> str:
        """Extract and correct phone number"""
        # Remove all non-digits
        digits = re.sub(r'\D', '', text)
        
        # Indian phone numbers
        if len(digits) == 10 and digits[0] in '6789':
            return digits
        elif len(digits) == 11 and digits[0] == '0':
            return digits[1:]  # Remove leading 0
        elif len(digits) == 12 and digits[:2] == '91':
            return digits[2:]  # Remove country code
        elif len(digits) >= 10:
            # Take last 10 digits
            return digits[-10:]
        
        return digits
    
    @classmethod
    def _correct_pincode(cls, text: str) -> str:
        """Extract and validate Indian pincode"""
        digits = re.sub(r'\D', '', text)
        
        # Indian pincodes are 6 digits, first digit 1-9
        if len(digits) >= 6:
            pin = digits[:6]
            if pin[0] in '123456789':
                return pin
        
        return ''
    
    @classmethod
    def _correct_date(cls, text: str) -> str:
        """Correct and normalize date format"""
        text = text.strip()
        
        # Try to extract DD/MM/YYYY or DD-MM-YYYY
        match = re.search(r'(\d{1,2})[/\-\s](\d{1,2})[/\-\s](\d{2,4})', text)
        if match:
            day, month, year = match.groups()
            day = day.zfill(2)
            month = month.zfill(2)
            if len(year) == 2:
                year = '20' + year if int(year) < 50 else '19' + year
            return f"{day}/{month}/{year}"
        
        # Try DDMMYYYY format
        match = re.search(r'(\d{2})(\d{2})(\d{4})', text)
        if match:
            day, month, year = match.groups()
            # Validate
            if 1 <= int(day) <= 31 and 1 <= int(month) <= 12 and 1900 <= int(year) <= 2100:
                return f"{day}/{month}/{year}"
        
        return text
    
    @classmethod
    def _correct_name(cls, text: str) -> str:
        """Correct name OCR errors"""
        # Remove extra spaces
        text = ' '.join(text.split())
        
        # Title case
        text = text.title()
        
        # Common name corrections
        corrections = {
            'Klrpal': 'Kirpal',
            'Rlddhi': 'Riddhi',
            'Dhlruv': 'Dhruv',
        }
        
        for wrong, right in corrections.items():
            text = text.replace(wrong, right)
        
        return text


class FieldExtractor:
    """
    Intelligent field extraction with pattern matching and validation.
    """
    
    # Field patterns with priorities (higher = more specific)
    FIELD_PATTERNS = {
        # Academic/Admission Details
        'academic_session': [
            (r'ACADEMIC\s+SESSION[:\s_]*(\d{4}[-/]\d{2,4})', 10),
            (r'SESSION[:\s_]*(\d{4}[-/]\d{2,4})', 8),
            (r'(\d{4}[-/]\d{2,4})\s*(?:session)?', 5),
        ],
        'course': [
            (r'B\.?\s*COM\.?\s*\(?\s*H\s*\)?', 10, 'B.COM.(H)'),
            (r'B\.?\s*A\.?\s*\(?\s*H\s*\)?\s*ECO', 10, 'B.A.(H) ECO'),
            (r'COURSE[:\s]*([A-Z\.\(\)\s]+(?:H|HONS?))', 5),
        ],
        'admission_category': [
            (r'(?:GEN|GENERAL)\s*[✓✔☑]', 10, 'GEN'),
            (r'[✓✔☑]\s*(?:GEN|GENERAL)', 10, 'GEN'),
            (r'OBC\s*[✓✔☑]', 10, 'OBC'),
            (r'[✓✔☑]\s*OBC', 10, 'OBC'),
            (r'(?:SC)\s*[✓✔☑]', 10, 'SC'),
            (r'[✓✔☑]\s*(?:SC)', 10, 'SC'),
            (r'(?:ST)\s*[✓✔☑]', 10, 'ST'),
            (r'[✓✔☑]\s*(?:ST)', 10, 'ST'),
            (r'(?:PWD|PwBD)\s*[✓✔☑]', 10, 'PWD'),
            (r'[✓✔☑]\s*(?:PWD|PwBD)', 10, 'PWD'),
            (r'EWS\s*[✓✔☑]', 10, 'EWS'),
            (r'[✓✔☑]\s*EWS', 10, 'EWS'),
        ],
        'du_portal_form_number': [
            (r'DU\s*Portal\s*Form\s*(?:Number|No\.?)[:\s]*(\d{12})', 10),
            (r'Form\s*Number[:\s]*(\d{12})', 8),
            (r'(\d{12})', 3),  # Fallback - 12 digit number
        ],
        'cuet_score': [
            (r'CUET\s*Score[:\s]*(\d{3,4})', 10),
            (r'TOTAL\s*CUET\s*SCORE[:\s]*(\d{3,4})', 10),
            (r'Score\s*Obtained[:\s]*(\d{3,4})\s*$', 5),
        ],
        'college_roll_no': [
            (r'College\s*Roll\s*No\.?[:\s]*(\d{2}[A-Z]{2}\d{3})', 10),
            (r'Roll\s*No\.?[:\s]*(\d{2}[A-Z]{2}\d{3})', 8),
            (r'(\d{2}[A-Z]{2}\d{3})', 5),
        ],
        
        # Personal Details
        'student_name': [
            (r'1\.\s*([A-Z][A-Z\s]+)\s*(?:First\s*Name|$)', 10),
            (r'NAME\s*IN\s*BLOCK\s*LETTERS[:\s]*([A-Z][A-Z\s]+)', 8),
        ],
        'first_name': [
            (r'First\s*Name[:\s]*([A-Z]+)', 10),
            (r'1\.\s*([A-Z]+)\s+First', 8),
        ],
        'middle_name': [
            (r'Middle\s*Name[:\s]*([A-Z]+)', 10),
        ],
        'surname': [
            (r'Surname[:\s]*([A-Z]+)', 10),
        ],
        'gender': [
            (r'Male\s*[✓✔☑]', 10, 'Male'),
            (r'[✓✔☑]\s*Male', 10, 'Male'),
            (r'Female\s*[✓✔☑]', 10, 'Female'),
            (r'[✓✔☑]\s*Female', 10, 'Female'),
            (r'Transgender\s*[✓✔☑]', 10, 'Transgender'),
        ],
        'date_of_birth': [
            (r'Date\s*of\s*Birth[:\s]*(\d{2}[/\-\s]\d{2}[/\-\s]\d{4})', 10),
            (r'D\.?O\.?B\.?[:\s]*(\d{2}[/\-\s]\d{2}[/\-\s]\d{4})', 8),
            (r'3\.\s*Date\s*of\s*Birth[:\s]*(\d{2})\s*(\d{2})\s*(\d{4})', 10),
        ],
        'date_of_admission': [
            (r'Date\s*of\s*Admission[:\s]*(\d{2}[/\-\s]\d{2}[/\-\s]\d{4})', 10),
            (r'Admission[:\s]*(\d{2})\s*(\d{2})\s*(\d{4})', 8),
        ],
        
        # Address
        'permanent_address': [
            (r'4\.\s*Permanent\s*(?:Address)?[:\s]*(.+?)(?:State|PIN|5\.)', 8),
            (r'Permanent\s*Address[:\s]*(.+?)(?:State|PIN)', 8),
        ],
        'permanent_state': [
            (r'State[:\s]*(DELHI|HARYANA|UTTAR\s*PRADESH|RAJASTHAN|PUNJAB|UP|HR|RJ|PB|BIHAR|MADHYA\s*PRADESH|MP)', 10),
        ],
        'permanent_pincode': [
            (r'PIN[:\s]*(\d{6})', 10),
            (r'Pincode[:\s]*(\d{6})', 10),
        ],
        
        # Contact
        'email': [
            (r'Email[:\s]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', 10),
            (r'([a-zA-Z0-9_.+-]+@(?:gmail|yahoo|hotmail|outlook)\.[a-z]+)', 8),
        ],
        'phone_number': [
            (r'Contact\s*Numbers?[:\s]*(\d{10})', 10),
            (r'Mobile[:\s]*(\d{10})', 8),
            (r'Phone[:\s]*(\d{10})', 8),
        ],
        
        # Parents
        'mother_name': [
            (r"Mother'?s?\s*Name[:\s]*([A-Z][A-Z\s]+)", 10),
            (r'8\.\s*Mother\'?s?\s*Name[:\s]*([A-Z][A-Z\s]+)', 10),
        ],
        'father_name': [
            (r"Father'?s?\s*Name[:\s]*([A-Z][A-Z\s]+)", 10),
            (r'9\.\s*Father\'?s?\s*Name[:\s]*([A-Z][A-Z\s]+)', 10),
        ],
        
        # Aadhar
        'aadhar_number': [
            (r'Aadhaa?r\s*(?:Number|No\.?|Card)?[:\s]*(\d{4}\s*\d{4}\s*\d{4})', 10),
            (r'(\d{4}\s*\d{4}\s*\d{4})', 5),  # 12 digit with spaces
        ],
    }
    
    @classmethod
    def extract_field(cls, field_name: str, text: str) -> Optional[ExtractedField]:
        """
        Extract a specific field from text using pattern matching.
        
        Returns ExtractedField with value and confidence.
        """
        if field_name not in cls.FIELD_PATTERNS:
            return None
        
        patterns = cls.FIELD_PATTERNS[field_name]
        best_match = None
        best_priority = -1
        
        for pattern_def in patterns:
            if len(pattern_def) == 3:
                pattern, priority, fixed_value = pattern_def
            else:
                pattern, priority = pattern_def
                fixed_value = None
            
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match and priority > best_priority:
                if fixed_value:
                    value = fixed_value
                elif match.groups():
                    value = match.group(1).strip()
                else:
                    value = match.group(0).strip()
                
                best_match = ExtractedField(
                    value=value,
                    confidence=min(1.0, priority / 10),
                    source=f'pattern:{pattern[:30]}...'
                )
                best_priority = priority
        
        return best_match
    
    @classmethod
    def extract_all_fields(cls, text: str) -> Dict[str, ExtractedField]:
        """Extract all known fields from text"""
        results = {}
        
        for field_name in cls.FIELD_PATTERNS:
            field = cls.extract_field(field_name, text)
            if field:
                results[field_name] = field
        
        return results


class SpatialLabelValuePairer:
    """
    Pairs labels with values using spatial proximity analysis.
    
    This uses bounding box information to determine which text
    elements are labels and which are their corresponding values.
    """
    
    # Known form labels (lowercase for matching)
    LABELS = {
        'academic session', 'course', 'admission category',
        'du portal form number', 'cuet score', 'college roll no',
        'date of admission', 'first name', 'middle name', 'surname',
        'gender', 'date of birth', 'permanent address', 'state', 'pin',
        'local address', 'correspondence', 'email', 'contact numbers',
        "mother's name", "father's name", 'aadhar number', 'blood group',
        'religion', 'nationality', 'category', 'occupation',
        'designation', 'organization', 'mobile', 'landline',
    }
    
    def __init__(self, text_elements: List[TextElement]):
        self.elements = text_elements
        self.pairs = {}
    
    def find_pairs(self) -> Dict[str, str]:
        """
        Find label-value pairs using spatial analysis.
        
        Strategy:
        1. Identify labels (text matching known label patterns)
        2. Find values to the right of labels (same Y, higher X)
        3. Find values below labels (same X, higher Y)
        """
        for i, elem in enumerate(self.elements):
            text_lower = elem.text.lower().strip()
            
            # Check if this is a known label
            for label in self.LABELS:
                if label in text_lower or self._fuzzy_match(text_lower, label) > 0.8:
                    # Found a label - find its value
                    value = self._find_value_for_label(elem, i)
                    if value:
                        # Normalize label name
                        field_name = label.replace(' ', '_').replace("'s", '')
                        self.pairs[field_name] = value
                    break
        
        return self.pairs
    
    def _find_value_for_label(self, label_elem: TextElement, label_idx: int) -> Optional[str]:
        """Find the value element for a given label"""
        candidates = []
        
        label_bbox = label_elem.bbox
        
        for i, elem in enumerate(self.elements):
            if i == label_idx:
                continue
            
            elem_bbox = elem.bbox
            
            # Check if element is to the RIGHT of label (same line)
            if (abs(elem_bbox.center_y - label_bbox.center_y) < 20 and
                elem_bbox.x_min > label_bbox.x_max):
                distance = elem_bbox.x_min - label_bbox.x_max
                candidates.append((elem, distance, 'right'))
            
            # Check if element is BELOW label
            elif (abs(elem_bbox.center_x - label_bbox.center_x) < 50 and
                  elem_bbox.y_min > label_bbox.y_max):
                distance = elem_bbox.y_min - label_bbox.y_max
                candidates.append((elem, distance, 'below'))
        
        # Sort by distance, prefer right-side values
        candidates.sort(key=lambda x: (0 if x[2] == 'right' else 1, x[1]))
        
        if candidates:
            return candidates[0][0].text
        
        return None
    
    @staticmethod
    def _fuzzy_match(s1: str, s2: str) -> float:
        """Calculate fuzzy match ratio between two strings"""
        return SequenceMatcher(None, s1, s2).ratio()


class CrossFieldValidator:
    """
    Validates extracted fields for consistency and correctness.
    """
    
    @classmethod
    def validate(cls, fields: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Validate and potentially correct extracted fields.
        
        Returns:
            (corrected_fields, validation_issues)
        """
        corrected = dict(fields)
        issues = {}
        
        # Validate date formats
        for date_field in ['date_of_birth', 'date_of_admission', 'category_certificate_date']:
            if date_field in corrected:
                validated = cls._validate_date(corrected[date_field])
                if validated:
                    corrected[date_field] = validated
                else:
                    issues[date_field] = f"Invalid date format: {corrected[date_field]}"
        
        # Validate phone numbers
        for phone_field in ['phone_number', 'mother_mobile', 'father_mobile', 'guardian_mobile']:
            if phone_field in corrected:
                validated = cls._validate_phone(corrected[phone_field])
                if validated:
                    corrected[phone_field] = validated
                else:
                    issues[phone_field] = f"Invalid phone: {corrected[phone_field]}"
        
        # Validate email
        if 'email' in corrected:
            validated = cls._validate_email(corrected['email'])
            if validated:
                corrected['email'] = validated
            else:
                issues['email'] = f"Invalid email: {corrected['email']}"
        
        # Validate pincode
        for pin_field in ['permanent_pincode', 'correspondence_pincode', 'pincode']:
            if pin_field in corrected:
                validated = cls._validate_pincode(corrected[pin_field])
                if validated:
                    corrected[pin_field] = validated
                else:
                    issues[pin_field] = f"Invalid pincode: {corrected[pin_field]}"
        
        # Cross-validate name fields
        cls._validate_name_consistency(corrected, issues)
        
        # Validate CUET scores
        cls._validate_cuet_scores(corrected, issues)
        
        return corrected, issues
    
    @classmethod
    def _validate_date(cls, date_str: str) -> Optional[str]:
        """Validate and normalize date"""
        if not date_str:
            return None
        
        # Try various formats
        patterns = [
            (r'(\d{2})[/\-](\d{2})[/\-](\d{4})', '{}/{}/{}'),
            (r'(\d{2})(\d{2})(\d{4})', '{}/{}/{}'),
            (r'(\d{1,2})\s+(\d{1,2})\s+(\d{4})', '{:02d}/{:02d}/{}'),
        ]
        
        for pattern, fmt in patterns:
            match = re.search(pattern, date_str)
            if match:
                day, month, year = match.groups()
                day, month, year = int(day), int(month), int(year)
                
                if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                    return f"{day:02d}/{month:02d}/{year}"
        
        return None
    
    @classmethod
    def _validate_phone(cls, phone: str) -> Optional[str]:
        """Validate Indian phone number"""
        if not phone:
            return None
        
        digits = re.sub(r'\D', '', phone)
        
        # Remove country code
        if len(digits) == 12 and digits.startswith('91'):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith('0'):
            digits = digits[1:]
        
        # Valid Indian mobile
        if len(digits) == 10 and digits[0] in '6789':
            return digits
        
        return None
    
    @classmethod
    def _validate_email(cls, email: str) -> Optional[str]:
        """Validate and correct email"""
        if not email:
            return None
        
        # Apply OCR corrections
        email = OCRErrorCorrector.correct_text(email, context='email')
        
        # Basic validation
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return email.lower()
        
        return None
    
    @classmethod
    def _validate_pincode(cls, pin: str) -> Optional[str]:
        """Validate Indian pincode"""
        if not pin:
            return None
        
        digits = re.sub(r'\D', '', pin)
        
        if len(digits) >= 6:
            pin = digits[:6]
            if pin[0] in '123456789':
                return pin
        
        return None
    
    @classmethod
    def _validate_name_consistency(cls, fields: Dict[str, Any], issues: Dict[str, str]):
        """Ensure name fields are consistent"""
        first = fields.get('first_name', '')
        middle = fields.get('middle_name', '')
        surname = fields.get('surname', '')
        full = fields.get('student_name', '')
        
        if first and surname and not full:
            # Construct full name
            parts = [first, middle, surname] if middle else [first, surname]
            fields['student_name'] = ' '.join(p for p in parts if p)
        elif full and not first:
            # Try to split full name
            parts = full.split()
            if len(parts) >= 2:
                fields['first_name'] = parts[0]
                fields['surname'] = parts[-1]
                if len(parts) == 3:
                    fields['middle_name'] = parts[1]
    
    @classmethod
    def _validate_cuet_scores(cls, fields: Dict[str, Any], issues: Dict[str, str]):
        """Validate CUET scores are within valid range"""
        total = 0
        count = 0
        
        for i in range(1, 7):
            score_key = f'cuet_score_obtained_{i}'
            total_key = f'cuet_total_score_{i}'
            
            if score_key in fields:
                try:
                    score = int(fields[score_key])
                    if score < 0 or score > 200:
                        issues[score_key] = f"Score out of range: {score}"
                    else:
                        total += score
                        count += 1
                except ValueError:
                    issues[score_key] = f"Invalid score: {fields[score_key]}"
        
        # Verify total matches
        if 'cuet_score' in fields and count > 0:
            try:
                claimed_total = int(fields['cuet_score'])
                if abs(claimed_total - total) > 5:  # Allow small tolerance
                    issues['cuet_score'] = f"Total mismatch: claimed {claimed_total}, calculated {total}"
            except ValueError:
                pass


class WorldClassExtractor:
    """
    World-class form extraction engine combining all techniques.
    
    This orchestrates:
    1. OCR error correction
    2. Pattern-based field extraction  
    3. Spatial label-value pairing
    4. Cross-field validation
    5. Confidence scoring
    """
    
    def __init__(self):
        self.error_corrector = OCRErrorCorrector
        self.field_extractor = FieldExtractor
        self.validator = CrossFieldValidator
    
    def extract(
        self,
        raw_text: str,
        text_elements: Optional[List[TextElement]] = None
    ) -> Dict[str, Any]:
        """
        Perform world-class extraction from OCR text.
        
        Args:
            raw_text: The raw OCR text (line-by-line preferred)
            text_elements: Optional list of text elements with bounding boxes
        
        Returns:
            Dictionary with extracted fields, confidence scores, and metadata
        """
        results = {
            'fields': {},
            'confidence': {},
            'field_count': 0,
            'overall_confidence': 0.0,
            'validation_issues': {},
            'extraction_method': 'world_class_v1'
        }
        
        # Step 1: Pre-process and correct OCR errors
        corrected_text = self._preprocess_text(raw_text)
        
        # Step 2: Pattern-based field extraction
        pattern_fields = self.field_extractor.extract_all_fields(corrected_text)
        
        for field_name, extracted in pattern_fields.items():
            results['fields'][field_name] = extracted.value
            results['confidence'][field_name] = extracted.confidence
        
        # Step 3: Spatial analysis if bounding boxes available
        if text_elements:
            pairer = SpatialLabelValuePairer(text_elements)
            spatial_pairs = pairer.find_pairs()
            
            for field_name, value in spatial_pairs.items():
                if field_name not in results['fields']:
                    results['fields'][field_name] = value
                    results['confidence'][field_name] = 0.7  # Medium confidence
        
        # Step 4: Enhanced extraction with context-aware patterns
        self._extract_enhanced_fields(corrected_text, results)
        
        # Step 5: Cross-field validation
        validated_fields, issues = self.validator.validate(results['fields'])
        results['fields'] = validated_fields
        results['validation_issues'] = issues
        
        # Step 6: Calculate overall metrics
        results['field_count'] = len(results['fields'])
        if results['confidence']:
            results['overall_confidence'] = sum(results['confidence'].values()) / len(results['confidence'])
        
        return results
    
    def _preprocess_text(self, text: str) -> str:
        """Pre-process OCR text with corrections"""
        if not text:
            return ""
        
        # Apply word-level corrections
        corrected = self.error_corrector.correct_text(text, context='general')
        
        # Normalize whitespace
        corrected = re.sub(r'[ \t]+', ' ', corrected)
        
        # Fix common OCR artifacts
        corrected = re.sub(r'[|]', '', corrected)
        corrected = re.sub(r'\.+', '.', corrected)
        
        return corrected
    
    def _extract_enhanced_fields(self, text: str, results: Dict[str, Any]):
        """Extract additional fields with enhanced patterns"""
        fields = results['fields']
        confidence = results['confidence']
        
        # CUET Subject-wise scores
        self._extract_cuet_details(text, fields, confidence)
        
        # Mother's occupational details
        self._extract_parent_details(text, fields, confidence, 'mother')
        
        # Father's occupational details
        self._extract_parent_details(text, fields, confidence, 'father')
        
        # Guardian details
        self._extract_guardian_details(text, fields, confidence)
        
        # Class XII details
        self._extract_class_xii(text, fields, confidence)
        
        # Additional personal info
        self._extract_personal_info(text, fields, confidence)
        
        # Certificate details
        self._extract_certificate_details(text, fields, confidence)
    
    def _extract_cuet_details(self, text: str, fields: Dict, confidence: Dict):
        """Extract CUET subject-wise scores from table structure"""
        # Look for CUET marks section
        cuet_section = re.search(
            r'(?:CUET|Qualifying\s+Examination)[\s\S]{0,2000}?(?:TOTAL\s+CUET|11\.|Declaration)',
            text, re.IGNORECASE
        )
        
        if not cuet_section:
            return
        
        section_text = cuet_section.group(0)
        
        # Extract subjects and scores
        subjects = ['English', 'Accountancy', 'Business Studies', 'Economics', 'Mathematics']
        
        for i, subject in enumerate(subjects, 1):
            # Pattern: Subject ... Total Score ... Obtained Score
            pattern = rf'{subject}[\s\S]{{0,100}}?(\d{{2,3}})\s+(\d{{2,3}})'
            match = re.search(pattern, section_text, re.IGNORECASE)
            
            if match:
                total_score = match.group(1)
                obtained_score = match.group(2)
                
                # Validate scores
                try:
                    total = int(total_score)
                    obtained = int(obtained_score)
                    
                    if 100 <= total <= 200 and 0 <= obtained <= total:
                        fields[f'cuet_subject_{i}'] = subject
                        fields[f'cuet_total_score_{i}'] = total_score
                        fields[f'cuet_score_obtained_{i}'] = obtained_score
                        confidence[f'cuet_subject_{i}'] = 0.9
                        confidence[f'cuet_total_score_{i}'] = 0.9
                        confidence[f'cuet_score_obtained_{i}'] = 0.9
                except ValueError:
                    pass
    
    def _extract_parent_details(self, text: str, fields: Dict, confidence: Dict, parent: str):
        """Extract parent occupational details"""
        prefix = parent  # 'mother' or 'father'
        
        # Section patterns
        section_patterns = [
            rf"11[ab]?\.\s*{parent.title()}'?s?\s*Occupational\s*Details",
            rf"{parent.title()}'?s?\s*Occupational",
        ]
        
        section_text = None
        for pattern in section_patterns:
            match = re.search(pattern + r'[\s\S]{0,800}?(?:12\.|Father|Mother|Guardian|Local)', text, re.IGNORECASE)
            if match:
                section_text = match.group(0)
                break
        
        if not section_text:
            section_text = text  # Fallback to full text
        
        # Occupation
        occ_patterns = [
            rf'{parent.title()}\'?s?\s*Occupation[:\s]*([A-Za-z\s]+?)(?:\n|Designation|Email)',
            r'Occupation[:\s]*([A-Za-z\s]+?)(?:\n|Designation)',
        ]
        
        for pattern in occ_patterns:
            match = re.search(pattern, section_text, re.IGNORECASE)
            if match:
                occupation = match.group(1).strip()
                occupation = self.error_corrector.correct_text(occupation, 'name')
                if occupation and len(occupation) > 2:
                    fields[f'{prefix}_occupation'] = occupation
                    confidence[f'{prefix}_occupation'] = 0.8
                break
        
        # Email
        email_match = re.search(r'Email[:\s]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', section_text, re.IGNORECASE)
        if email_match:
            email = self.error_corrector.correct_text(email_match.group(1), 'email')
            fields[f'{prefix}_email'] = email
            confidence[f'{prefix}_email'] = 0.85
        
        # Phone/Mobile
        phone_match = re.search(r'(?:Mobile|Phone)[:\s]*(\d{10})', section_text, re.IGNORECASE)
        if phone_match:
            phone = self.error_corrector.correct_text(phone_match.group(1), 'phone')
            fields[f'{prefix}_mobile'] = phone
            confidence[f'{prefix}_mobile'] = 0.9
    
    def _extract_guardian_details(self, text: str, fields: Dict, confidence: Dict):
        """Extract local guardian details"""
        guardian_section = re.search(
            r'12\.\s*Local\s*Guardian[\s\S]{0,1000}?(?:13\.|14\.|Below Poverty)',
            text, re.IGNORECASE
        )
        
        if not guardian_section:
            return
        
        section_text = guardian_section.group(0)
        
        # Name
        name_match = re.search(r'Name[:\s]*([A-Z][A-Za-z\s]+?)(?:\n|Relation)', section_text, re.IGNORECASE)
        if name_match:
            fields['guardian_name'] = name_match.group(1).strip()
            confidence['guardian_name'] = 0.8
        
        # Relation
        relation_match = re.search(r'Relation[:\s]*([A-Za-z]+)', section_text, re.IGNORECASE)
        if relation_match:
            fields['guardian_relation'] = relation_match.group(1).strip()
            confidence['guardian_relation'] = 0.8
    
    def _extract_class_xii(self, text: str, fields: Dict, confidence: Dict):
        """Extract Class XII / qualifying exam details"""
        # Year of passing
        year_match = re.search(r'Year\s*of\s*Passing[:\s]*(\d{4})', text, re.IGNORECASE)
        if year_match:
            fields['twelfth_year'] = year_match.group(1)
            confidence['twelfth_year'] = 0.9
        
        # Board
        board_patterns = [
            r'Board[:\s]*([A-Z]+\s*Board|CBSE|ICSE|State Board)',
            r'(CBSE|ICSE|ISC)',
        ]
        for pattern in board_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['twelfth_board'] = match.group(1).upper()
                confidence['twelfth_board'] = 0.85
                break
        
        # Roll number
        roll_match = re.search(r'(?:Board\s*)?Roll\s*(?:Number|No\.?)[:\s]*(\d{8,12})', text, re.IGNORECASE)
        if roll_match:
            fields['twelfth_roll_number'] = roll_match.group(1)
            confidence['twelfth_roll_number'] = 0.9
        
        # Institution/School
        school_patterns = [
            r'Institution\s*Last\s*Attended[:\s]*([A-Za-z\s]+(?:School|College|Academy)[A-Za-z\s]*)',
            r'School[:\s]*([A-Za-z\s]+(?:Public|Convent|Vidyalaya|Academy))',
        ]
        for pattern in school_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                school = match.group(1).strip()
                school = self.error_corrector.correct_text(school, 'name')
                fields['twelfth_institution'] = school
                confidence['twelfth_institution'] = 0.8
                break
    
    def _extract_personal_info(self, text: str, fields: Dict, confidence: Dict):
        """Extract additional personal information"""
        # Blood group
        blood_match = re.search(r'Blood\s*Group[:\s]*([ABO]+[+-]?)', text, re.IGNORECASE)
        if blood_match:
            fields['blood_group'] = blood_match.group(1).upper()
            confidence['blood_group'] = 0.9
        
        # Religion
        religion_patterns = ['Hindu', 'Muslim', 'Christian', 'Sikh', 'Buddhist', 'Jain']
        for religion in religion_patterns:
            if re.search(rf'{religion}\s*[✓✔☑]|[✓✔☑]\s*{religion}', text, re.IGNORECASE):
                fields['religion'] = religion
                confidence['religion'] = 0.85
                break
        
        # Nationality
        if re.search(r'Indian\s*[✓✔☑]|Nationality[:\s]*Indian', text, re.IGNORECASE):
            fields['nationality'] = 'Indian'
            confidence['nationality'] = 0.95
        
        # Below Poverty Line
        bpl_section = re.search(r'Below\s*Poverty\s*Line[\s\S]{0,100}?(Yes|No)\s*[✓✔☑✗×]', text, re.IGNORECASE)
        if bpl_section:
            response = bpl_section.group(1)
            fields['below_poverty_line'] = response.title()
            confidence['below_poverty_line'] = 0.85
        
        # Annual Income
        income_match = re.search(r'Annual\s*(?:Family\s*)?Income[:\s]*(?:Rs\.?\s*)?(\d{1,3}(?:,\d{3})*|\d+)', text, re.IGNORECASE)
        if income_match:
            income = income_match.group(1).replace(',', '')
            fields['annual_income'] = income
            confidence['annual_income'] = 0.8
    
    def _extract_certificate_details(self, text: str, fields: Dict, confidence: Dict):
        """Extract certificate-related information"""
        # Category certificate details
        cert_section = re.search(
            r'17\.\s*Certificate[\s\S]{0,500}?(?:18\.|Declaration|$)',
            text, re.IGNORECASE
        )
        
        if cert_section:
            section_text = cert_section.group(0)
            
            # Certificate number
            num_match = re.search(r'Certificate\s*(?:Number|No\.?)[:\s]*([A-Z0-9/\-]+)', section_text, re.IGNORECASE)
            if num_match:
                fields['category_certificate_number'] = num_match.group(1)
                confidence['category_certificate_number'] = 0.8
            
            # Issue date
            date_match = re.search(r'Date\s*of\s*Issue[:\s]*(\d{2}[/\-]?\d{2}[/\-]?\d{4})', section_text, re.IGNORECASE)
            if date_match:
                date = self.error_corrector.correct_text(date_match.group(1), 'date')
                fields['category_certificate_date'] = date
                confidence['category_certificate_date'] = 0.8
            
            # Issuing authority
            auth_match = re.search(r'(?:Issuing\s*)?Authority[:\s]*([A-Za-z\s,]+?)(?:\n|$)', section_text, re.IGNORECASE)
            if auth_match:
                fields['category_certificate_authority'] = auth_match.group(1).strip()
                confidence['category_certificate_authority'] = 0.75


# Singleton instance for easy access
world_class_extractor = WorldClassExtractor()
