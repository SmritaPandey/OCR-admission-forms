"""
Enhanced Google OCR Post-Processor and Training System

This module provides:
1. Text cleanup and normalization for noisy OCR output
2. SRCC form-specific field extraction with fuzzy matching
3. Training data collection for continuous improvement
4. Confidence scoring and validation
"""
import re
from typing import Dict, Any, Optional, List, Tuple
from difflib import SequenceMatcher
import json
from pathlib import Path
from datetime import datetime


class GoogleOCREnhancer:
    """
    Enhances Google OCR output for better field extraction.
    Handles noisy OCR text, common errors, and form-specific patterns.
    """
    
    def __init__(self):
        self.training_data_path = Path("training_data/google_ocr_corrections.json")
        self.corrections_cache = self._load_corrections()
        
        # Common OCR character substitution errors
        self.ocr_substitutions = {
            # Numbers commonly confused with letters
            '0': ['O', 'o', 'Q', 'D'],
            '1': ['l', 'I', 'i', '|', '/'],
            '2': ['Z', 'z'],
            '3': ['E', 'B'],
            '4': ['A', 'H'],
            '5': ['S', 's'],
            '6': ['G', 'b'],
            '7': ['T', 'Y', '/'],
            '8': ['B', 'g', '&'],
            '9': ['g', 'q', 'P'],
            
            # Letters commonly confused
            'a': ['@', 'o', 'e', 'α'],
            'b': ['d', '6', 'h'],
            'c': ['e', 'o', '('],
            'd': ['b', 'o', 'cl'],
            'e': ['c', 'a', 'o'],
            'g': ['9', 'q', 'y'],
            'h': ['n', 'b', 'li'],
            'i': ['l', '1', '!', '|'],
            'l': ['1', 'i', '|', '/'],
            'm': ['n', 'rn', 'in'],
            'n': ['m', 'h', 'r'],
            'o': ['0', 'c', 'e', 'a'],
            'p': ['q', 'b', 'd'],
            'q': ['g', '9', 'p'],
            'r': ['n', 'i'],
            's': ['5', 'S'],
            't': ['1', '+', 'f'],
            'u': ['v', 'n', 'ii'],
            'v': ['u', 'y', 'w'],
            'w': ['vv', 'vy', 'v'],
            'y': ['v', 'g'],
            'z': ['2', 's'],
        }
        
        # SRCC form-specific field labels and their variations
        self.srcc_field_labels = {
            'academic_session': [
                'academic session', 'session', 'academic year', 'session year',
                'acad. session', 'acad session', 'ACADEMIC SESSION'
            ],
            'course': [
                'course', 'course (please', 'course applied', 'programme',
                'b.com.(h)', 'b.com(h)', 'b.a.(h) eco', 'b.a.(h)eco', 'bcom h', 'ba h eco'
            ],
            'admission_category': [
                'admission category', 'category (please', 'admission cat',
                'gen', 'obc', 'sc', 'st', 'ews', 'sports', 'pwd'
            ],
            'du_portal_form_number': [
                'du portal form number', 'du form number', 'portal form number',
                'form number', 'application number', 'du portal no', 'portal no'
            ],
            'cuet_score': [
                'cuet score', 'cuet', 'cuet marks', 'entrance score',
                'total cuet score', 'cuet total score'
            ],
            'college_roll_no': [
                'college roll no', 'roll no', 'roll number', 'college roll',
                'roll no.', 'college roll no.', 'enrolment no'
            ],
            'date_of_admission': [
                'date of admission', 'admission date', 'date admitted',
                'date of admission :', 'doa'
            ],
            'student_name': [
                'name in block letters', 'name', 'student name', 'full name',
                'first name', 'applicant name', 'candidate name',
                'name of student', 'name of candidate'
            ],
            'first_name': ['first name', 'firstname', 'first'],
            'middle_name': ['middle name', 'middlename', 'middle'],
            'surname': ['surname', 'last name', 'lastname', 'family name'],
            'gender': [
                'gender', 'sex', 'male/female', 'gender tick',
                'male', 'female', 'transgender', 'm/f/t'
            ],
            'date_of_birth': [
                'date of birth', 'dob', 'birth date', 'birthday',
                'd.o.b', 'd.o.b.', 'date of birth (dd/mm/yyyy)'
            ],
            'permanent_address': [
                'permanent address', 'permanent addr', 'perm. address',
                'home address', 'residential address'
            ],
            'correspondence_address': [
                'correspondence address', 'local address', 'mailing address',
                'current address', 'local address for correspondence',
                'correspondence addr', 'local addr'
            ],
            'email': [
                'email', 'e-mail', 'email id', 'email address',
                'e mail', 'emailid', 'mail'
            ],
            'phone_number': [
                'contact numbers', 'phone', 'mobile', 'contact',
                'phone number', 'mobile number', 'contact no',
                'phone no', 'mobile no', 'tel'
            ],
            'mother_name': [
                "mother's name", 'mother name', 'mothers name', 'mother',
                'name of mother', "mother's"
            ],
            'father_name': [
                "father's name", 'father name', 'fathers name', 'father',
                'name of father', "father's", 'guardian name'
            ],
            'nationality': [
                'nationality', 'nation', 'citizenship', 'country'
            ],
            'religion': ['religion', 'faith'],
            'blood_group': [
                'blood group', 'blood type', 'blood', 'bg'
            ],
            'annual_income': [
                'annual income', "parent's / family annual income",
                'family income', 'income', "parents' income"
            ],
            'aadhar_number': [
                'aadhar', 'aadhaar', 'uid', 'aadhar no', 'aadhaar no',
                'aadhar number', 'aadhaar number', 'uid no'
            ],
            'category_certificate': [
                'certificate no', 'certificate number', 'caste certificate',
                'category certificate', 'ews/sc/st/obc certificate'
            ],
            'twelfth_board': [
                'board / university', 'board/university', '12th board',
                'class xii board', 'qualifying board', 'hsc board'
            ],
            'twelfth_year': [
                'year of passing', 'passing year', '12th year',
                'class xii year', 'qualifying year', 'hsc year'
            ],
            'twelfth_roll_number': [
                'examination roll no', 'roll no', '12th roll',
                'class xii roll', 'board roll no'
            ],
            'twelfth_institution': [
                'institution last attended', 'school', 'institution',
                'school last attended', 'last school'
            ],
            'hindi_studied': [
                'hindi studied upto', 'hindi studied', 'hindi upto',
                'viii/x/xii/never', 'hindi class'
            ],
        }
        
        # Known correct patterns for various fields
        self.field_patterns = {
            'academic_session': r'20\d{2}\s*[-–—]\s*20\d{2}',
            'du_portal_form_number': r'2[0-4]\d{10}',  # 12-digit number starting with 2
            'cuet_score': r'\d{2,4}(?:\.\d{1,3})?',
            'college_roll_no': r'\d{2}\s*[A-Z]{2,3}\s*\d{2,4}',
            'date': r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})',
            'phone': r'[6-9]\d{9}',
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'aadhar': r'\d{4}\s*\d{4}\s*\d{4}',
            'pincode': r'[1-9]\d{5}',
            'year': r'(19|20)\d{2}',
            'percentage': r'\d{1,3}(?:\.\d{1,2})?',
        }
        
        # Common Indian names dictionary for fuzzy matching
        self.common_names = self._load_common_names()
    
    def _load_corrections(self) -> Dict[str, str]:
        """Load previously saved OCR corrections for learning"""
        try:
            if self.training_data_path.exists():
                with open(self.training_data_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_corrections(self):
        """Save OCR corrections for future training"""
        try:
            self.training_data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.training_data_path, 'w') as f:
                json.dump(self.corrections_cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save corrections: {e}")
    
    def _load_common_names(self) -> List[str]:
        """Load common Indian names for fuzzy matching"""
        return [
            # First names (sample)
            'Aarav', 'Aditya', 'Arjun', 'Ananya', 'Aarushi', 'Aisha', 'Akshay',
            'Amit', 'Amita', 'Anjali', 'Aryan', 'Bhavya', 'Chirag', 'Deepak',
            'Diya', 'Gaurav', 'Harsh', 'Ishaan', 'Jatin', 'Kajal', 'Karan',
            'Kavya', 'Khushi', 'Krishna', 'Lakshmi', 'Manish', 'Meera', 'Mohit',
            'Navya', 'Neha', 'Nikhil', 'Nisha', 'Pooja', 'Priya', 'Rahul',
            'Raj', 'Riya', 'Rohan', 'Sachin', 'Sahil', 'Sakshi', 'Sandeep',
            'Shreya', 'Simran', 'Sneha', 'Sonu', 'Tanvi', 'Varun', 'Vijay',
            'Vikas', 'Yash', 'Yogesh', 'Hemraj', 'Meeta', 'Kirpal', 'Mamta',
            'Devesh', 'Verma', 'Yadav', 'Sharma', 'Singh', 'Kumar', 'Gupta',
            # Last names (sample)
            'Agarwal', 'Aggarwal', 'Bansal', 'Bhardwaj', 'Chauhan', 'Chaudhary',
            'Chopra', 'Dubey', 'Garg', 'Goyal', 'Jain', 'Joshi', 'Kapoor',
            'Khanna', 'Malik', 'Malhotra', 'Mathur', 'Mehra', 'Mishra', 'Mittal',
            'Nair', 'Pandey', 'Patel', 'Rao', 'Reddy', 'Saxena', 'Sethi',
            'Shah', 'Sinha', 'Srivastava', 'Tandon', 'Thakur', 'Tiwari', 'Verma',
        ]
    
    def enhance_ocr_text(self, raw_text: str) -> str:
        """
        Enhance raw OCR text by cleaning up common errors.
        
        Args:
            raw_text: Raw OCR output
            
        Returns:
            Cleaned and enhanced text
        """
        if not raw_text:
            return ""
        
        text = raw_text
        
        # Step 1: Basic cleanup
        text = self._basic_cleanup(text)
        
        # Step 2: Fix common OCR errors in known patterns
        text = self._fix_known_patterns(text)
        
        # Step 3: Apply learned corrections
        text = self._apply_corrections(text)
        
        # Step 4: Normalize spacing and formatting
        text = self._normalize_formatting(text)
        
        return text
    
    def _basic_cleanup(self, text: str) -> str:
        """Basic text cleanup"""
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Fix common OCR artifacts
        text = re.sub(r'[|]{2,}', '', text)  # Multiple pipes
        text = re.sub(r'[\[\]]{2,}', '', text)  # Multiple brackets
        text = re.sub(r'[_]{3,}', '', text)  # Long underscores
        
        # Fix spacing around colons
        text = re.sub(r'\s*:\s*', ': ', text)
        
        # Fix common word concatenations (without spaces)
        common_fixes = [
            (r'(?i)STUDENTSDATAFORM', 'STUDENTS DATA FORM'),
            (r'(?i)COLLEGEOFCOMMERCE', 'COLLEGE OF COMMERCE'),
            (r'(?i)SHRIRAMCOLLEGE', 'SHRI RAM COLLEGE'),
            (r'(?i)ACADEMICSESSION', 'ACADEMIC SESSION'),
            (r'(?i)DATEOFBIRTH', 'DATE OF BIRTH'),
            (r'(?i)DATEOFADMISSION', 'DATE OF ADMISSION'),
            (r'(?i)CONTACTNUMBERS?', 'CONTACT NUMBERS'),
            (r'(?i)NAMEINBLOCKLETTERS', 'NAME IN BLOCK LETTERS'),
            (r'(?i)PERMANENTADDRESS', 'PERMANENT ADDRESS'),
            (r'(?i)CORRESPONDENCEADDRESS', 'CORRESPONDENCE ADDRESS'),
            (r'(?i)FATHERSNAME', "FATHER'S NAME"),
            (r'(?i)MOTHERSNAME', "MOTHER'S NAME"),
            (r'(?i)GUARDIANSNAME', "GUARDIAN'S NAME"),
            (r'(?i)CUETSCORE', 'CUET SCORE'),
            (r'(?i)COLLEGEROLLNO', 'COLLEGE ROLL NO'),
            (r'(?i)PORTALFORMNUMBER', 'PORTAL FORM NUMBER'),
            (r'(?i)ANNUALINCOME', 'ANNUAL INCOME'),
            (r'(?i)BLOODGROUP', 'BLOOD GROUP'),
            (r'(?i)AADHARNUMBER', 'AADHAR NUMBER'),
            (r'(?i)YEAROFPASSING', 'YEAR OF PASSING'),
            (r'(?i)BOARDUNIVERSITY', 'BOARD / UNIVERSITY'),
        ]
        
        for pattern, replacement in common_fixes:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def _fix_known_patterns(self, text: str) -> str:
        """Fix OCR errors in known field patterns"""
        
        # Fix academic session format (e.g., "2024-2025")
        text = re.sub(
            r'20[0-9O][0-9O]\s*[-–—_]\s*20[0-9O][0-9O]',
            lambda m: self._fix_year_range(m.group(0)),
            text
        )
        
        # Fix DU portal form number (12 digits)
        text = re.sub(
            r'2[0-4O][0-9O]{10,11}',
            lambda m: self._fix_digits(m.group(0)),
            text
        )
        
        # Fix phone numbers (10 digits)
        text = re.sub(
            r'[6-9O][0-9O]{9}',
            lambda m: self._fix_digits(m.group(0)),
            text
        )
        
        # Fix dates (DD/MM/YYYY or similar)
        text = re.sub(
            r'[0-9O]{1,2}[\/\-\.][0-9O]{1,2}[\/\-\.][0-9O]{2,4}',
            lambda m: self._fix_date(m.group(0)),
            text
        )
        
        # Fix email addresses
        text = re.sub(
            r'[a-zA-Z0-9._%+\-]+[@][a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
            lambda m: m.group(0).lower().replace(' ', ''),
            text
        )
        
        # Fix college roll number pattern (e.g., "25 BC 463" or "25BC463")
        text = re.sub(
            r'\b[0-9O]{2}\s*[A-Za-z]{2,3}\s*[0-9O]{2,4}\b',
            lambda m: self._fix_roll_number(m.group(0)),
            text
        )
        
        # Fix Aadhar numbers (12 digits with optional spaces)
        text = re.sub(
            r'[0-9O]{4}\s*[0-9O]{4}\s*[0-9O]{4}',
            lambda m: self._fix_digits(m.group(0).replace(' ', '')),
            text
        )
        
        # Fix pincode (6 digits)
        text = re.sub(
            r'\b[1-9O][0-9O]{5}\b',
            lambda m: self._fix_digits(m.group(0)),
            text
        )
        
        return text
    
    def _fix_year_range(self, text: str) -> str:
        """Fix year range like '2024-2025'"""
        # Replace O with 0 in year ranges
        text = re.sub(r'O', '0', text)
        text = re.sub(r'[–—_]', '-', text)
        
        # Ensure proper format
        match = re.search(r'(\d{4})\s*-\s*(\d{4})', text)
        if match:
            year1, year2 = match.groups()
            return f"{year1}-{year2}"
        return text
    
    def _fix_digits(self, text: str) -> str:
        """Fix common OCR digit errors"""
        replacements = {
            'O': '0', 'o': '0',
            'l': '1', 'I': '1', 'i': '1', '|': '1',
            'Z': '2', 'z': '2',
            'E': '3',
            'A': '4', 'H': '4',
            'S': '5', 's': '5',
            'G': '6', 'b': '6',
            'T': '7', '/': '7',
            'B': '8', '&': '8',
            'g': '9', 'q': '9',
        }
        
        result = ''
        for char in text:
            result += replacements.get(char, char)
        
        return result
    
    def _fix_date(self, text: str) -> str:
        """Fix date format"""
        text = self._fix_digits(text)
        
        # Normalize separator
        text = re.sub(r'[\-\.]', '/', text)
        
        return text
    
    def _fix_roll_number(self, text: str) -> str:
        """Fix college roll number format"""
        # Remove extra spaces
        text = re.sub(r'\s+', '', text)
        
        # Fix O to 0 in numeric parts
        parts = re.match(r'([0-9O]{2})([A-Za-z]{2,3})([0-9O]{2,4})', text, re.IGNORECASE)
        if parts:
            num1 = self._fix_digits(parts.group(1))
            letters = parts.group(2).upper()
            num2 = self._fix_digits(parts.group(3))
            return f"{num1}{letters}{num2}"
        
        return text
    
    def _apply_corrections(self, text: str) -> str:
        """Apply learned corrections from training data"""
        for wrong, correct in self.corrections_cache.items():
            # Use word boundary matching for safety
            text = re.sub(r'\b' + re.escape(wrong) + r'\b', correct, text, flags=re.IGNORECASE)
        
        return text
    
    def _normalize_formatting(self, text: str) -> str:
        """Normalize spacing and formatting"""
        # Normalize multiple spaces to single space
        text = re.sub(r' {2,}', ' ', text)
        
        # Ensure proper spacing around colons
        text = re.sub(r'\s*:\s*', ': ', text)
        
        # Fix missing spaces after punctuation
        text = re.sub(r'([.,;!?])([A-Za-z])', r'\1 \2', text)
        
        # Trim lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text
    
    def extract_field_with_fuzzy_match(
        self, text: str, field_name: str, confidence_threshold: float = 0.6
    ) -> Tuple[Optional[str], float]:
        """
        Extract a field value using fuzzy matching for the label.
        
        Args:
            text: OCR text to search
            field_name: Field name to extract
            confidence_threshold: Minimum similarity ratio
            
        Returns:
            Tuple of (extracted_value, confidence_score)
        """
        if field_name not in self.srcc_field_labels:
            return None, 0.0
        
        labels = self.srcc_field_labels[field_name]
        text_lower = text.lower()
        lines = text.split('\n')
        
        best_value = None
        best_confidence = 0.0
        
        # Field-specific patterns for direct extraction
        field_patterns = {
            'du_portal_form_number': r'\b(2[0-4]\d{10})\b',
            'cuet_score': r'cuet\s*score[:\s]+(\d{2,4}(?:\.\d+)?)',
            'college_roll_no': r'(?:college\s*)?roll\s*no\.?[:\s]+(\d{2}\s*[A-Z]{2,3}\s*\d{2,4})',
            'date_of_admission': r'date\s*of\s*admission[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            'date_of_birth': r'(?:date\s*of\s*birth|dob)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            'phone_number': r'(?:contact\s*numbers?|phone|mobile)[:\s()]*([6-9]\d{9})',
            'email': r'(?:email|e-mail)[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            'academic_session': r'(?:academic\s*)?session[:\s]+(\d{4}\s*[-–]\s*\d{4})',
            'aadhar_number': r'(?:aadh?a+r|uid)[:\s]+(\d{4}\s*\d{4}\s*\d{4})',
            'pincode': r'(?:pin|pincode)[:\s]+(\d{6})',
            'nationality': r'nationality[:\s]+([A-Za-z]+)',
            'religion': r'religion[:\s]+([A-Za-z]+)',
            'blood_group': r'blood\s*group[:\s]+([ABO]{1,2}[+\-]?)',
            'gender': r'gender[:\s\(\)tick✓]*([Mm]ale|[Ff]emale|[Tt]ransgender)',
            'annual_income': r'(BELOW\s+\d+\s*LAKHS?|\d+[-–]\d+\s*LAKHS?)',
            # Name patterns - look for capitalized names after labels
            'mother_name': r"mother(?:'?s)?\s*name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            'father_name': r"father(?:'?s)?\s*name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            'guardian_name': r"(?:local\s+)?guardian(?:'?s)?\s*name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        }
        
        # Special handling for student name (most complex)
        if field_name == 'student_name':
            # Try to find first name + surname pattern
            name_pattern = r'(?:first\s*name|name\s*in\s*block\s*letters)[:\s]+([A-Z]+)\s*(?:middle\s*name[:\s]*)?(?:surname|last\s*name)?[:\s]*([A-Z]+)?'
            match = re.search(name_pattern, text, re.IGNORECASE)
            if match:
                first = match.group(1).strip() if match.group(1) else ''
                last = match.group(2).strip() if match.group(2) else ''
                if first:
                    full_name = f"{first.title()} {last.title()}".strip()
                    confidence = 0.85 if last else 0.7
                    return full_name, confidence
            
            # Alternative: look for capitalized words after "NAME"
            name_match = re.search(r'NAME\s*(?:IN\s*BLOCK\s*LETTERS)?[:\s]+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)', text)
            if name_match:
                name = name_match.group(1).strip()
                # Filter out common non-name words
                if name.upper() not in ['FIRST', 'MIDDLE', 'SURNAME', 'LAST', 'GENDER', 'DOB', 'IN', 'BLOCK', 'LETTERS']:
                    return name.title(), 0.75
        
        # Special handling for course (tick mark detection)
        if field_name == 'course':
            checkmarks = r'[✓✔☑☒✗×√]'
            course_section = text[:800]
            
            # Check for B.COM.(H) with tick mark
            bcom_with_tick = re.search(
                rf'B\.?\s*COM\.?\s*\(H\)\s*{checkmarks}|{checkmarks}\s*B\.?\s*COM\.?\s*\(H\)',
                course_section, re.IGNORECASE
            )
            
            # Check for B.A.(H) ECO with tick mark
            ba_with_tick = re.search(
                rf'B\.?\s*A\.?\s*\(H\)\s*ECO\s*{checkmarks}|{checkmarks}\s*B\.?\s*A\.?\s*\(H\)\s*ECO',
                course_section, re.IGNORECASE
            )
            
            if bcom_with_tick and not ba_with_tick:
                return 'B.COM.(H)', 0.95
            elif ba_with_tick and not bcom_with_tick:
                return 'B.A.(H) ECO', 0.95
            elif bcom_with_tick and ba_with_tick:
                if bcom_with_tick.start() < ba_with_tick.start():
                    return 'B.COM.(H)', 0.9
                else:
                    return 'B.A.(H) ECO', 0.9
            # Fallback to pattern detection
            elif re.search(r'B\.?\s*COM\.?\s*\(H\)', course_section, re.IGNORECASE):
                return 'B.COM.(H)', 0.7
            elif re.search(r'B\.?\s*A\.?\s*\(H\)\s*ECO', course_section, re.IGNORECASE):
                return 'B.A.(H) ECO', 0.7
        
        # Special handling for admission_category (tick mark detection)
        if field_name == 'admission_category':
            checkmarks = r'[✓✔☑☒✗×√]'
            category_section = text[:1200]
            categories = ['GEN', 'OBC', 'SC', 'ST', 'EWS', 'PWD', 'Sports', 'Foreign', 'CW', 'KM', 'ECA']
            
            for cat in categories:
                # Tick after category
                if re.search(rf'\b{cat}\b\s*{checkmarks}', category_section, re.IGNORECASE):
                    return cat.upper(), 0.95
                # Tick before category
                if re.search(rf'{checkmarks}\s*\b{cat}\b', category_section, re.IGNORECASE):
                    return cat.upper(), 0.95
        
        # Try field-specific pattern first
        if field_name in field_patterns:
            pattern = field_patterns[field_name]
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                value = self._clean_extracted_value(value, field_name)
                if value:
                    confidence = self._calculate_field_confidence(value, field_name)
                    if confidence > 0.7:
                        return value, confidence
        
        # Try each label variation
        for label in labels:
            # Look for "label: value" pattern - be more restrictive
            # Only capture until end of line or next field label
            escaped_label = re.escape(label)
            
            # Pattern that stops at common field labels
            stop_words = r'(?=\n|$|(?:name|dob|date|phone|email|address|gender|category|course|score)[\s:]*[A-Z])'
            pattern = rf'{escaped_label}[:\s]+(.+?)' + stop_words
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            
            if match:
                value = match.group(1).strip()
                # Limit to first reasonable chunk
                value = value.split('\n')[0].strip()
                
                # Remove trailing labels/field names
                value = re.sub(r'\s*(name|dob|date|phone|email|gender|category|course|score|address)\s*$', '', value, flags=re.IGNORECASE)
                
                value = self._clean_extracted_value(value, field_name)
                
                if value and not self._is_label_text(value) and len(value) > 1:
                    confidence = self._calculate_field_confidence(value, field_name)
                    if confidence > best_confidence:
                        best_value = value
                        best_confidence = confidence
        
        # Fallback: simpler line-based extraction
        if not best_value or best_confidence < 0.5:
            for label in labels[:3]:  # Only try first few labels
                for i, line in enumerate(lines):
                    line_lower = line.lower().strip()
                    label_lower = label.lower()
                    
                    # Check if line starts with label
                    if line_lower.startswith(label_lower):
                        # Extract value after label
                        remainder = line[len(label):].strip()
                        if remainder.startswith(':'):
                            remainder = remainder[1:].strip()
                        
                        if remainder:
                            value = self._clean_extracted_value(remainder, field_name)
                            if value and not self._is_label_text(value):
                                confidence = self._calculate_field_confidence(value, field_name)
                                if confidence > best_confidence:
                                    best_value = value
                                    best_confidence = confidence
                        elif i + 1 < len(lines):
                            # Value might be on next line
                            next_line = lines[i + 1].strip()
                            if next_line and not self._is_label_text(next_line):
                                value = self._clean_extracted_value(next_line, field_name)
                                if value:
                                    confidence = self._calculate_field_confidence(value, field_name)
                                    if confidence > best_confidence:
                                        best_value = value
                                        best_confidence = confidence
        
        return best_value, best_confidence
    
    def _clean_extracted_value(self, value: str, field_name: str) -> str:
        """Clean extracted value based on field type"""
        if not value:
            return ""
        
        # Remove common noise
        value = re.sub(r'^[:\s\-\.\(\)]+', '', value)
        value = re.sub(r'[:\s\-\.\(\)]+$', '', value)
        
        # Field-specific cleaning
        if field_name in ['phone_number', 'father_phone', 'mother_phone', 'guardian_phone']:
            # Keep only digits
            value = re.sub(r'[^\d+]', '', value)
            # Extract 10-digit phone
            match = re.search(r'[6-9]\d{9}', value)
            if match:
                value = match.group(0)
        
        elif field_name == 'email':
            value = value.lower().strip()
            # Remove spaces in email
            value = value.replace(' ', '')
        
        elif field_name in ['date_of_birth', 'date_of_admission', 'admission_date']:
            value = self._fix_date(value)
        
        elif field_name in ['aadhar_number']:
            value = self._fix_digits(value.replace(' ', ''))
        
        elif field_name in ['pincode', 'permanent_pincode', 'correspondence_pincode']:
            value = self._fix_digits(value.replace(' ', ''))
        
        elif field_name in ['cuet_score']:
            # Extract numeric score
            value = self._fix_digits(value)
            match = re.search(r'\d+(?:\.\d+)?', value)
            if match:
                value = match.group(0)
        
        elif field_name in ['gender']:
            value = value.upper()
            if value in ['M', 'MALE']:
                value = 'Male'
            elif value in ['F', 'FEMALE']:
                value = 'Female'
            elif value in ['T', 'TRANSGENDER', 'TRANS']:
                value = 'Transgender'
        
        elif field_name in ['category', 'admission_category']:
            value = value.upper()
            # Normalize category names
            category_map = {
                'GENERAL': 'GEN', 'GEN': 'GEN',
                'OBC': 'OBC', 'OTHER BACKWARD': 'OBC',
                'SC': 'SC', 'SCHEDULED CASTE': 'SC',
                'ST': 'ST', 'SCHEDULED TRIBE': 'ST',
                'EWS': 'EWS', 'ECONOMICALLY WEAKER': 'EWS',
                'PWD': 'PWD', 'PERSON WITH DISABILITY': 'PWD',
                'SPORTS': 'Sports', 'SPORT': 'Sports',
                'ECA': 'ECA',
            }
            for key, val in category_map.items():
                if key in value:
                    value = val
                    break
        
        elif field_name in ['student_name', 'father_name', 'mother_name', 'guardian_name']:
            # Title case for names
            value = ' '.join(word.capitalize() for word in value.split())
            # Try to correct common OCR errors in names using fuzzy matching
            value = self._correct_name(value)
        
        elif field_name in ['nationality']:
            value = value.capitalize()
            if 'INDIAN' in value.upper():
                value = 'Indian'
        
        elif field_name in ['blood_group']:
            value = value.upper()
            # Normalize blood group
            match = re.search(r'(A|B|AB|O)[+\-]?', value)
            if match:
                value = match.group(0)
                if not value.endswith('+') and not value.endswith('-'):
                    value += '+'  # Default to positive
        
        return value.strip()
    
    def _correct_name(self, name: str) -> str:
        """Try to correct OCR errors in names using fuzzy matching"""
        words = name.split()
        corrected_words = []
        
        for word in words:
            # Check if word matches any common name with high similarity
            best_match = word
            best_ratio = 0.0
            
            for common_name in self.common_names:
                ratio = SequenceMatcher(None, word.lower(), common_name.lower()).ratio()
                if ratio > 0.8 and ratio > best_ratio:
                    best_match = common_name
                    best_ratio = ratio
            
            corrected_words.append(best_match)
        
        return ' '.join(corrected_words)
    
    def _is_label_text(self, value: str) -> bool:
        """Check if value is actually a form label rather than data"""
        if not value or len(value) < 2:
            return True
        
        value_lower = value.lower().strip()
        
        # Check for common label patterns
        label_patterns = [
            r'^name\s*$', r'^dob\s*$', r'^gender\s*$', r'^address\s*$',
            r'^phone\s*$', r'^email\s*$', r'^category\s*$', r'^course\s*$',
            r'^please\s', r'^tick\s', r'^fill\s', r'^enter\s',
            r'form', r'student', r'details', r'information',
            r'instruction', r'document', r'required', r'mandatory',
        ]
        
        for pattern in label_patterns:
            if re.match(pattern, value_lower):
                return True
        
        # Check if value is all uppercase and looks like a label
        if value.isupper() and len(value.split()) <= 3 and len(value) < 30:
            return True
        
        return False
    
    def _calculate_field_confidence(self, value: str, field_name: str) -> float:
        """Calculate confidence score for an extracted value"""
        if not value:
            return 0.0
        
        confidence = 0.5  # Base confidence
        
        # Field-specific validation
        if field_name in ['phone_number', 'father_phone', 'mother_phone']:
            if re.match(r'^[6-9]\d{9}$', value):
                confidence = 0.95
            elif re.match(r'^\d{10,}$', value):
                confidence = 0.7
        
        elif field_name == 'email':
            if re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', value.lower()):
                confidence = 0.95
        
        elif field_name in ['date_of_birth', 'date_of_admission']:
            if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', value):
                confidence = 0.9
        
        elif field_name in ['aadhar_number']:
            if re.match(r'^\d{12}$', value):
                confidence = 0.95
        
        elif field_name in ['pincode']:
            if re.match(r'^[1-9]\d{5}$', value):
                confidence = 0.95
        
        elif field_name == 'cuet_score':
            if re.match(r'^\d{2,4}(\.\d+)?$', value):
                confidence = 0.85
        
        elif field_name == 'college_roll_no':
            if re.match(r'^\d{2}[A-Z]{2,3}\d{2,4}$', value, re.IGNORECASE):
                confidence = 0.9
        
        elif field_name in ['student_name', 'father_name', 'mother_name']:
            # Names should have 2-4 words
            words = value.split()
            if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
                confidence = 0.85
            elif len(words) >= 1:
                confidence = 0.6
        
        elif field_name == 'gender':
            if value in ['Male', 'Female', 'Transgender']:
                confidence = 0.95
        
        elif field_name in ['category', 'admission_category']:
            if value in ['GEN', 'OBC', 'SC', 'ST', 'EWS', 'PWD', 'Sports', 'ECA']:
                confidence = 0.95
        
        elif field_name == 'blood_group':
            if re.match(r'^(A|B|AB|O)[+-]$', value):
                confidence = 0.95
        
        elif field_name == 'nationality':
            if value.lower() == 'indian':
                confidence = 0.95
        
        elif field_name == 'academic_session':
            if re.match(r'^20\d{2}-20\d{2}$', value):
                confidence = 0.95
        
        elif field_name == 'du_portal_form_number':
            if re.match(r'^2[0-4]\d{10}$', value):
                confidence = 0.95
        
        elif field_name == 'annual_income':
            # Accept "BELOW X LAKHS" or numeric values
            if re.match(r'^BELOW\s+\d+\s*LAKHS?$', value, re.IGNORECASE):
                confidence = 0.9
            elif re.match(r'^\d+[-–]\d+\s*LAKHS?$', value, re.IGNORECASE):
                confidence = 0.9
            elif re.match(r'^\d[\d,]*$', value):
                confidence = 0.8
        
        return confidence
    
    def extract_all_fields(self, text: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract all SRCC form fields from OCR text.
        
        Returns:
            Dictionary mapping field names to {value, confidence}
        """
        # First enhance the text
        enhanced_text = self.enhance_ocr_text(text)
        
        results = {}
        
        for field_name in self.srcc_field_labels.keys():
            value, confidence = self.extract_field_with_fuzzy_match(enhanced_text, field_name)
            if value and confidence > 0.4:
                results[field_name] = {
                    'value': value,
                    'confidence': round(confidence, 2)
                }
        
        return results
    
    def record_correction(self, wrong_text: str, correct_text: str):
        """
        Record a correction for training.
        
        Args:
            wrong_text: OCR error
            correct_text: Correct value
        """
        if wrong_text and correct_text and wrong_text != correct_text:
            self.corrections_cache[wrong_text] = correct_text
            self._save_corrections()
    
    def export_training_data(
        self, image_path: str, raw_ocr: str, verified_fields: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Export a training sample with verified ground truth.
        
        Args:
            image_path: Path to the form image
            raw_ocr: Raw OCR text
            verified_fields: Dictionary of verified field values
            
        Returns:
            Training sample dictionary
        """
        # Extract fields from OCR
        extracted_fields = self.extract_all_fields(raw_ocr)
        
        # Calculate accuracy
        correct = 0
        total = len(verified_fields)
        
        for field, verified_value in verified_fields.items():
            if field in extracted_fields:
                extracted_value = extracted_fields[field]['value']
                if extracted_value.lower() == verified_value.lower():
                    correct += 1
                else:
                    # Record correction for training
                    self.record_correction(extracted_value, verified_value)
        
        accuracy = correct / total if total > 0 else 0.0
        
        return {
            'image_path': image_path,
            'raw_ocr': raw_ocr,
            'extracted_fields': extracted_fields,
            'verified_fields': verified_fields,
            'accuracy': round(accuracy, 2),
            'timestamp': datetime.now().isoformat()
        }


class SRCCFormExtractor:
    """
    High-level extractor specifically for SRCC admission forms.
    Combines enhanced OCR with form-specific logic.
    """
    
    def __init__(self):
        self.enhancer = GoogleOCREnhancer()
        
        # Define all SRCC form fields with their expected types
        self.form_structure = {
            # Header fields
            'academic_session': {'type': 'text', 'required': True},
            'course': {'type': 'select', 'required': True},
            'admission_category': {'type': 'select', 'required': True},
            'du_portal_form_number': {'type': 'number', 'required': True},
            'cuet_score': {'type': 'number', 'required': True},
            'college_roll_no': {'type': 'text', 'required': True},
            'date_of_admission': {'type': 'date', 'required': True},
            
            # Personal details
            'student_name': {'type': 'text', 'required': True},
            'first_name': {'type': 'text', 'required': False},
            'middle_name': {'type': 'text', 'required': False},
            'surname': {'type': 'text', 'required': False},
            'gender': {'type': 'select', 'required': True},
            'date_of_birth': {'type': 'date', 'required': True},
            
            # Address
            'permanent_address': {'type': 'text', 'required': True},
            'correspondence_address': {'type': 'text', 'required': False},
            'pincode': {'type': 'number', 'required': True},
            
            # Contact
            'email': {'type': 'email', 'required': True},
            'phone_number': {'type': 'phone', 'required': True},
            
            # Family
            'mother_name': {'type': 'text', 'required': True},
            'father_name': {'type': 'text', 'required': True},
            
            # Other
            'nationality': {'type': 'text', 'required': True},
            'religion': {'type': 'text', 'required': False},
            'blood_group': {'type': 'text', 'required': False},
            'annual_income': {'type': 'number', 'required': False},
            'aadhar_number': {'type': 'number', 'required': False},
            
            # Academic
            'twelfth_board': {'type': 'text', 'required': False},
            'twelfth_year': {'type': 'number', 'required': False},
            'twelfth_roll_number': {'type': 'text', 'required': False},
            'twelfth_institution': {'type': 'text', 'required': False},
            'hindi_studied': {'type': 'text', 'required': False},
        }
    
    def extract_from_ocr_result(
        self, ocr_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract structured form data from OCR result.
        
        Args:
            ocr_result: Dictionary with 'raw_text' key
            
        Returns:
            Dictionary with extracted fields and metadata
        """
        raw_text = ocr_result.get('raw_text', '')
        if not raw_text:
            return {'fields': {}, 'confidence': 0, 'completeness': 0}
        
        # Extract all fields
        extracted = self.enhancer.extract_all_fields(raw_text)
        
        # Calculate overall confidence and completeness
        total_confidence = 0
        total_fields = 0
        required_found = 0
        required_total = 0
        
        for field_name, field_info in self.form_structure.items():
            if field_info['required']:
                required_total += 1
            
            if field_name in extracted:
                total_confidence += extracted[field_name]['confidence']
                total_fields += 1
                if field_info['required']:
                    required_found += 1
        
        avg_confidence = total_confidence / total_fields if total_fields > 0 else 0
        completeness = required_found / required_total if required_total > 0 else 0
        
        # Flatten fields for easier use
        fields = {}
        for field_name, data in extracted.items():
            fields[field_name] = data['value']
        
        return {
            'fields': fields,
            'field_details': extracted,
            'confidence': round(avg_confidence * 100, 1),
            'completeness': round(completeness * 100, 1),
            'raw_text_enhanced': self.enhancer.enhance_ocr_text(raw_text)
        }
    
    def validate_and_correct(
        self, extracted: Dict[str, Any], corrections: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Apply user corrections and update training data.
        
        Args:
            extracted: Previously extracted fields
            corrections: User-provided corrections {field: correct_value}
            
        Returns:
            Updated extraction with corrections applied
        """
        fields = extracted.get('fields', {}).copy()
        
        for field_name, correct_value in corrections.items():
            if field_name in fields:
                old_value = fields[field_name]
                if old_value != correct_value:
                    # Record for training
                    self.enhancer.record_correction(old_value, correct_value)
            
            fields[field_name] = correct_value
        
        extracted['fields'] = fields
        extracted['corrections_applied'] = corrections
        
        return extracted


# Create global instances
google_ocr_enhancer = GoogleOCREnhancer()
srcc_form_extractor = SRCCFormExtractor()
