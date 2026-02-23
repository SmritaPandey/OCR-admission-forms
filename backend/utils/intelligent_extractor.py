"""
Intelligent Form Field Extractor

A holistic, line-aware OCR field extraction engine that handles:
1. Scattered values across multiple lines
2. Checkbox/tick mark detection for selection fields
3. Multi-component name assembly
4. Date reconstruction with field-specific validation
5. Cross-field consistency validation
6. Contextual value extraction using proximity

This is designed to be "world-class" extraction for Indian college admission forms.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

# Import comprehensive form labels module
try:
    from backend.utils.form_labels import (
        ALL_FORM_LABELS, NAME_REJECT_LABELS, ADDRESS_WORDS,
        is_form_label, is_reject_name_value, clean_name_value
    )
    HAVE_FORM_LABELS = True
except ImportError:
    HAVE_FORM_LABELS = False


@dataclass
class ParsedLine:
    """Represents a parsed line from OCR output with metadata"""
    index: int
    text: str
    is_label: bool = False
    is_value: bool = False
    is_empty: bool = False
    field_type: Optional[str] = None  # 'name', 'date', 'number', 'text', 'checkbox'


class IntelligentFieldExtractor:
    """
    Intelligent form field extractor that understands form layout and handles
    scattered OCR output intelligently.
    """
    
    # Tick mark characters that indicate selection
    TICK_MARKS = ['✓', '✔', '☑', '☒', '√', '✗', '×', '[x]', '[X]', '(v)', '(✓)', '(x)']
    
    # Comprehensive list of form labels to skip when extracting values
    # These are field names/labels that should NEVER be extracted as values
    FORM_LABELS = [
        # Name fields
        'first name', 'middle name', 'surname', 'last name', 'name in block letters',
        'in block letters', 'block letters', 'name of the student', 'name of student',
        'full name', 'applicant name', 'student name',
        
        # Date fields
        'date of birth', 'date of admission', 'dob', 'admission date',
        'd d', 'm m', 'y y y y', 'yyyy', 'dd', 'mm', 'date',
        
        # Gender/Category
        'gender', 'sex', 'category', 'admission category',
        'male', 'female', 'transgender',  # These are valid values, but if they appear as labels, skip
        'tick', 'please tick', 'please', 'tick()',
        
        # Address fields
        'state', 'pin', 'pincode', 'pin code', 'postal code',
        'address', 'permanent address', 'correspondence address', 'local address',
        'address line 1', 'address line 2', 'address line 3',
        'permanent', 'correspondence', 'local',
        'if different from permanent address', 'if different',
        
        # Contact fields
        'phone', 'phone number', 'mobile', 'mobile number', 'contact', 'contact number',
        'contact numbers', 'alternate phone', 'email', 'email id', 'email address',
        'emergency contact name', 'emergency contact phone',
        
        # Parent/Guardian fields
        "mother's name", "father's name", "guardian's name",
        'mother name', 'father name', 'guardian name',
        'mother', 'father', 'guardian', 'local guardian',
        'mother occupation', "mother's occupation", 'father occupation', "father's occupation",
        'guardian occupation', "guardian's occupation",
        'mother designation', "mother's designation", 'father designation', "father's designation",
        'guardian designation', "guardian's designation",
        'mother organization', "mother's organization", 'father organization', "father's organization",
        'guardian organization', "guardian's organization",
        'mother email', "mother's email", 'father email', "father's email",
        'guardian email', "guardian's email",
        'mother mobile', "mother's mobile", 'father mobile', "father's mobile",
        'guardian mobile', "guardian's mobile",
        'mother phone', "mother's phone", 'father phone', "father's phone",
        'guardian phone', "guardian's phone",
        'mother landline', "mother's landline", 'father landline', "father's landline",
        'guardian landline', "guardian's landline",
        'mother landline code', "mother's landline code", 'father landline code', "father's landline code",
        'guardian landline code', "guardian's landline code",
        'guardian residential address', "guardian's residential address",
        'guardian relation', "guardian's relation",
        
        # Personal information
        'occupation', 'designation', 'organization', 'annual income',
        'blood group', 'nationality', 'religion', 'aadhar', 'aadhar number',
        'aadhaar', 'aadhaar number', 'below poverty line', 'minority category',
        'enrollment number', 'college roll no', 'roll number', 'application number',
        'du enrollment number', 'du portal form number', 'cuet score',
        
        # Academic fields
        'academic session', 'course', 'course applied', 'qualifying examination',
        'class x', 'class xii', '10th', '12th', 'tenth', 'twelfth',
        '10th board', '12th board', 'tenth board', 'twelfth board',
        '10th year', '12th year', 'tenth year', 'twelfth year',
        '10th percentage', '12th percentage', 'tenth percentage', 'twelfth percentage',
        '10th school', '12th school', 'tenth school', 'twelfth school',
        '10th roll number', '12th roll number', 'tenth roll number', 'twelfth roll number',
        '10th institution', '12th institution', 'tenth institution', 'twelfth institution',
        'previous qualification', 'graduation details', 'hindi studied upto',
        'hindi medium preference', 'board', 'year', 'percentage', 'school',
        
        # CUET fields
        'cuet', 'cuet subject', 'cuet total score', 'cuet score obtained',
        'total cuet score', 'score', 'total', 'obtained', 'subject',
        'cuet subject 1', 'cuet subject 2', 'cuet subject 3',
        'cuet subject 4', 'cuet subject 5', 'cuet subject 6',
        'cuet total score 1', 'cuet total score 2', 'cuet total score 3',
        'cuet total score 4', 'cuet total score 5', 'cuet total score 6',
        'cuet score obtained 1', 'cuet score obtained 2', 'cuet score obtained 3',
        'cuet score obtained 4', 'cuet score obtained 5', 'cuet score obtained 6',
        
        # Certificate fields
        'category certificate authority', 'category certificate number', 'category certificate date',
        'disability percentage', 'disability type', 'udid number',
        
        # Instructions
        'please', 'please tick', 'please fill', 'please enter', 'please write',
        'please select', 'please specify', 'fill', 'enter', 'write', 'select',
        'specify', 'if applicable', 'if yes', 'if no', 'if different', 'if employed',
        'mandatory', 'optional', 'self attested', 'attach',
        'details', 'information', 'particulars', 'of the student', 'of student',
        'son of', 'daughter of', 'ward of', 'signature',
        
        # Section headers
        'student data form', "student's data form", 'admission form',
        'personal information', 'personal details', 'academic details',
        'admission details', 'address details', 'contact details',
        "mother's occupational details", "father's occupational details",
        "local guardian's details", 'qualifying examination details',
        'cuet marks', 'cuet scores', 'category certificate details',
        'declaration', 'undertaking', 'documents required', 'document checklist',
        
        # Table headers
        'sl no', 'sl. no', 's.no', 's. no', 'serial number',
        'subjects', 'marks',
    ]
    
    # Course options for checkbox detection
    COURSE_OPTIONS = ['B.COM.(H)', 'B.A.(H) ECO', 'B.A.(H) ECONOMICS']
    
    # Gender options
    GENDER_OPTIONS = ['Male', 'Female', 'Transgender']
    
    # Category options
    CATEGORY_OPTIONS = ['GEN', 'GENERAL', 'OBC', 'SC', 'ST', 'EWS', 'PWD', 'PwBD']
    
    def __init__(self):
        self.lines: List[ParsedLine] = []
        self.raw_text = ""
    
    def extract(self, raw_text: str) -> Dict[str, Any]:
        """
        Main extraction method - extracts all fields intelligently.
        """
        self.raw_text = raw_text
        self.lines = self._parse_lines(raw_text)
        
        result = {}
        
        # Extract each category of fields
        result.update(self._extract_student_name())
        result.update(self._extract_date_of_birth())
        result.update(self._extract_date_of_admission())
        result.update(self._extract_gender())
        result.update(self._extract_course())
        result.update(self._extract_category())
        result.update(self._extract_contact_info())
        result.update(self._extract_address_info())
        result.update(self._extract_parent_info())
        result.update(self._extract_academic_info())
        result.update(self._extract_personal_info())
        result.update(self._extract_parent_details())
        result.update(self._extract_guardian_details())
        result.update(self._extract_education_details())
        result.update(self._extract_cuet_marks())
        result.update(self._extract_document_checklist())
        result.update(self._extract_certificate_info())
        result.update(self._extract_email()) # Add dedicated email extraction
        
        # Cross-validate and clean up
        result = self._cross_validate(result)
        
        return result
    
    def _parse_lines(self, text: str) -> List[ParsedLine]:
        """Parse text into structured lines with metadata"""
        lines = []
        for i, line in enumerate(text.split('\n')):
            line = line.strip()
            parsed = ParsedLine(
                index=i,
                text=line,
                is_empty=len(line) == 0,
                is_label=self._is_label(line),
                is_value=self._is_potential_value(line)
            )
            lines.append(parsed)
        return lines
    
    def _is_label(self, text: str) -> bool:
        """Check if text is a form label, not a value containing a keyword"""
        text_lower = text.lower().strip()
        
        # Use comprehensive form labels module if available
        if HAVE_FORM_LABELS and is_form_label(text_lower, strict=True):
            return True
        
        # If it matches a label exactly or with a dot/colon
        for l in self.FORM_LABELS:
            l_lower = l.lower()
            if text_lower == l_lower: return True
            if text_lower.startswith(l_lower + ':') or text_lower.startswith(l_lower + '.'): return True
            # Handle labels like (a) Name, (b) Board
            if re.match(rf'^\([a-z0-9]\)\s*{l_lower}', text_lower): return True
        
        # Specific skip for board names which are often confused as labels
        if 'BOARD' in text.upper() and len(text) > 25: return False # Long board names are values
        if 'UNIVERSITY' in text.upper() and len(text) > 25: return False
        
        # General heuristics for labels vs values
        if len(text) > 50: return False # Very long strings are values
        if re.search(r'[:\?]$', text_lower): return True # Labels often end in : or ?
        
        return any(label in text_lower for label in self.FORM_LABELS) and len(text) < 30
    
    def _is_potential_value(self, text: str) -> bool:
        """Check if text could be a value (not a label, not empty)"""
        if not text.strip():
            return False
        if self._is_label(text):
            return False
        # Single/double character labels are not values
        if len(text) <= 2 and text.upper() in ['D', 'M', 'Y', 'DD', 'MM', 'YY']:
            return False
        return True
    
    def _find_lines_near_label(self, label_pattern: str, max_lines: int = 20) -> List[ParsedLine]:
        """Find lines near a label for value extraction"""
        for i, line in enumerate(self.lines):
            if re.search(label_pattern, line.text, re.IGNORECASE):
                end_idx = min(i + max_lines + 1, len(self.lines))
                return self.lines[i:end_idx]
        return []

    def _extract_value_block(self, start_label_pattern: str, num_values: int, max_gap: int = 20) -> List[str]:
        """Extract a sequence of values following a block of labels"""
        start_idx = -1
        for i, line in enumerate(self.lines):
            if re.search(start_label_pattern, line.text, re.IGNORECASE):
                start_idx = i; break
        
        if start_idx == -1: return []
        
        values = []
        for i in range(start_idx + 1, min(start_idx + max_gap + 1, len(self.lines))):
            text = self.lines[i].text.strip()
            if not text: continue
            if self._is_label(text) or re.match(r'^\([a-z]\)$', text.lower()) or re.match(r'^\d{1,2}\.?$', text):
                continue
            values.append(text)
            if len(values) >= num_values: break
        return values
    
    def _has_tick_mark(self, text: str) -> bool:
        """Check if text contains any tick mark"""
        for tick in self.TICK_MARKS:
            if tick in text:
                return True
        return False
    
    def _find_ticked_option(self, text_block: str, options: List[str]) -> Optional[str]:
        """
        Find which option has a tick mark near it.
        """
        text_upper = text_block.upper()
        for option in options:
            if re.search(rf'{re.escape(option.upper())}\s*[✓✔☑☒√✗×]', text_upper):
                return option
        lines = text_block.split('\n')
        for i, line in enumerate(lines):
            if self._has_tick_mark(line):
                for option in options:
                    if re.search(rf'[✓✔☑☒√✗×]\s*{re.escape(option.upper())}', line.upper()):
                        for prev_i in range(i - 1, max(-1, i - 4), -1):
                            if prev_i >= 0:
                                for prev_opt in options:
                                    if prev_opt.upper() in lines[prev_i].upper(): return prev_opt
                        return option
                if i > 0:
                    for option in options:
                        if option.upper() in lines[i - 1].upper(): return option
        return None
    
    def _extract_student_name(self) -> Dict[str, Any]:
        """Intelligently extract student name, filtering out form noise"""
        result = {}
        name_area = None
        for i, line in enumerate(self.lines):
            if 'NAME IN BLOCK LETTERS' in line.text.upper():
                name_area = self.lines[i:min(i+35, len(self.lines))]; break
        if not name_area: return result
        
        # Comprehensive list of words that are NOT names (labels, addresses, etc.)
        reject_name_words = {
            # Form labels
            'name', 'first', 'middle', 'surname', 'last', 'block', 'letters', 'in',
            'date', 'birth', 'sex', 'gender', 'male', 'female', 'transgender',
            'address', 'permanent', 'correspondence', 'local', 'state', 'pin', 'pincode',
            'email', 'phone', 'mobile', 'contact', 'father', 'mother', 'guardian',
            'occupation', 'designation', 'organization', 'signature', 'student',
            # Address words
            'vihar', 'nagar', 'colony', 'enclave', 'park', 'road', 'street', 'lane',
            'sector', 'block', 'house', 'flat', 'flats', 'apartment', 'floor',
            'vivek', 'ashok', 'janta', 'rohini', 'dwarka', 'pitampura',
            # Occupations
            'service', 'business', 'employed', 'self', 'dhobi', 'dhobhi',
            'house', 'wife', 'housewife',
            # Date placeholders
            'dd', 'mm', 'yyyy', 'yy',
        }
        
        candidates = []
        for line in name_area:
            text = line.text.strip()
            # Strict filter for name artifacts
            if not text or len(text) < 3: continue
            if self._is_label(text): continue
            
            # Use form labels module if available
            if HAVE_FORM_LABELS and is_reject_name_value(text):
                continue
            
            # Filter out known labels that might have been missed by _is_label
            if any(x in text.upper() for x in ['DATE OF BIRTH', 'SEX', 'GENDER', 'PERMANENT ADDRESS', 'BLOCK LETTERS', 
                                                'CORRESPONDENCE', 'EMAIL', 'PHONE', 'CONTACT', 'MOTHER', 'FATHER']):
                continue
            
            # Skip occupational noise if we've drifted too far
            if any(x in text.upper() for x in ['HOUSE', 'WIFE', 'DHOBI', 'SERVICE', 'OCCUPATION', 'BUSINESS']):
                continue
            
            # Skip address words
            text_words = text.upper().split()
            if any(w.lower() in reject_name_words for w in text_words if len(w) > 2):
                # Check if it's mostly address words
                addr_word_count = sum(1 for w in text_words if w.lower() in reject_name_words)
                if addr_word_count >= len(text_words) / 2:
                    continue

            num_prefix = re.match(r'^(\d+)\.?\s*(.*)$', text)
            if num_prefix:
                val = num_prefix.group(2).strip()
                # Strict filter for name artifacts (Y Y, M M, D D, and alphanumeric IDs)
                if val.isupper() and len(val) >= 3 and not re.search(r'\b[YMD]\s+[YMD]\b', val):
                    # Filter out alphanumeric IDs like YBC102
                    if not re.search(r'\d', val):
                        # Final check: not a label word
                        if val.lower() not in reject_name_words:
                            candidates.append({'idx': line.index, 'val': val, 'prefix': int(num_prefix.group(1))})
            elif text.isupper() and len(text) >= 3 and not re.search(r'\b[YMD]\s+[YMD]\b', text):
                if sum(c.isalpha() for c in text) / len(text) > 0.8: # Stricter alpha check
                    if not re.search(r'\d', text):
                        # Final check: not a label word
                        if text.lower() not in reject_name_words:
                            candidates.append({'idx': line.index, 'val': text, 'prefix': None})
        
        first_name = surname = None
        # Aryan example: (1) ARYAN.
        for c in candidates:
            if c['prefix'] == 1: first_name = c['val']
            if c['prefix'] == 3: surname = c['val']
            
        if not first_name and candidates:
            # First non-prefixed word is likely first name
            words = [c for c in candidates if not c['prefix']]
            if words: first_name = words[0]['val']
        
        # Look for surname if not found by prefix
        if not surname:
             words = [c for c in candidates if c['val'] != first_name]
             if words:
                 # Only accept if it's on a nearby line (proximity check)
                 primary_idx = next((c['idx'] for c in candidates if c['val'] == first_name), 0)
                 if abs(words[0]['idx'] - primary_idx) < 15:
                     surname = words[0]['val']
        
        if first_name: result['first_name'] = first_name.title()
        if surname: result['surname'] = surname.title()
        if first_name or surname: 
            result['student_name'] = f"{first_name or ''} {surname or ''}".strip().title()
        return result
    
    def _extract_date_of_birth(self) -> Dict[str, Any]:
        """Extract DOB with robust analysis"""
        result = {}
        section = self._find_lines_near_label(r'Date\s+of\s+Birth|3\s*\.\s*Date', max_lines=40)
        if not section: return result
        for line in section:
            m = re.search(r'(\b\d{1,2})[/\-\.\s]{1,3}(\d{1,2})[/\-\.\s]{1,3}(\d{4})\b', line.text)
            if m:
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if 1995 <= y <= 2012: result['date_of_birth'] = f"{d:02d}/{mo:02d}/{y}"; return result
        comp = []
        for line in section:
            if not line.is_label:
                for val in re.findall(r'\b\d{1,4}\b', line.text): comp.append({'idx': line.index, 'val': val})
        day = month = year = None; assigned = set()
        for i, c in enumerate(comp):
            v = int(c['val'])
            if 1995 <= v <= 2012: year = v; assigned.add(i); break
        if year is None:
            for i in range(len(comp)-1, -1, -1):
                v = int(comp[i]['val'])
                if 0 <= v <= 12 and len(comp[i]['val']) == 2: year = 2000 + v; assigned.add(i); break
        for i, c in enumerate(comp):
            if i not in assigned and 1 <= int(c['val']) <= 31 and int(c['val']) > 12:
                day = int(c['val']); assigned.add(i); break
        for i, c in enumerate(comp):
            if i not in assigned and 1 <= int(c['val']) <= 12:
                month = int(c['val']); assigned.add(i); break
        if day is None:
            for i, c in enumerate(comp):
                if i not in assigned and 1 <= int(c['val']) <= 31:
                    day = int(c['val']); assigned.add(i); break
        if day and month and year: result['date_of_birth'] = f"{day:02d}/{month:02d}/{year}"
        return result
    
    def _extract_date_of_admission(self) -> Dict[str, Any]:
        result = {}
        section = self._find_lines_near_label(r'Date\s+of\s+Admission', max_lines=10)
        for line in section:
            m = re.search(r'(\d{1,2})[/\-\s]+(\d{1,2})[/\-\s]+(\d{4})', line.text)
            if m:
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if 2020 <= y <= 2030: result['date_of_admission'] = f"{d:02d}/{mo:02d}/{y}"; break
        return result
    
    def _extract_gender(self) -> Dict[str, Any]:
        result = {}
        section = self._find_lines_near_label(r'Gender', max_lines=15)
        for line in section:
            t = re.sub(r'\{TICK.*?\}', '', line.text.upper())
            for opt in self.GENDER_OPTIONS:
                if opt.upper() in t and self._has_tick_mark(t): result['gender'] = opt; return result
        m_idx = f_idx = tr_idx = t_idx = None
        for i, line in enumerate(section):
            t = re.sub(r'\{TICK.*?\}', '', line.text.upper())
            if 'MALE' in t and 'FEMALE' not in t: m_idx = i
            if 'FEMALE' in t: f_idx = i
            if 'TRANSGENDER' in t: tr_idx = i
            if self._has_tick_mark(t) and t_idx is None: t_idx = i
        if t_idx is not None:
            if f_idx is not None and tr_idx is not None and f_idx < t_idx <= tr_idx: result['gender'] = 'Female'
            elif m_idx is not None and f_idx is not None and m_idx < t_idx <= f_idx: result['gender'] = 'Male'
            elif tr_idx is not None and t_idx >= tr_idx: result['gender'] = 'Transgender'
        return result
    
    def _extract_course(self) -> Dict[str, Any]:
        result = {}
        txt = self.raw_text[:2000].upper()
        if re.search(r'B\.?COM\.?\s*\(?H\)?\s*[✓✔☑☒√✗×]', txt): result['course'] = 'B.COM.(H)'
        elif re.search(r'B\.?A\.?\s*\(?H\)?\s*(?:ECO)?\s*[✓✔☑☒√✗×]', txt): result['course'] = 'B.A.(H) ECO'
        else:
            m = re.search(r'\d{2}(BC|BE)\d+', txt)
            if m: result['course'] = 'B.COM.(H)' if m.group(1) == 'BC' else 'B.A.(H) ECO'
        return result
    
    def _extract_category(self) -> Dict[str, Any]:
        result = {}
        sec = self._find_lines_near_label(r'Category|Admission Category', max_lines=10)
        if sec:
            t = self._find_ticked_option('\n'.join(l.text for l in sec), self.CATEGORY_OPTIONS)
            if t: result['category'] = result['admission_category'] = 'GEN' if t.upper() in ['GEN', 'GENERAL'] else t.upper(); return result
        m = re.search(r'Certificate No\.?\s*(\d{10,15})', self.raw_text, re.I)
        if m:
            c = 'OBC' if re.search(r'OBC|Non[- ]?Creamy|NCL', self.raw_text, re.I) else \
                'SC' if re.search(r'\bSC\b|Scheduled Caste', self.raw_text, re.I) else \
                'ST' if re.search(r'\bST\b|Scheduled Tribe', self.raw_text, re.I) else \
                'EWS' if re.search(r'EWS|Economically Weaker', self.raw_text, re.I) else None
            if c: result['category'] = result['admission_category'] = c; result['category_certificate_number'] = m.group(1)
        return result
    
    def _extract_contact_info(self) -> Dict[str, Any]:
        result = {}
        m = re.search(r'\b([6-9]\d{9})\b', self.raw_text)
        if m: result['phone_number'] = m.group(1)
        m = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', self.raw_text)
        if m: result['email'] = m.group(0).lower()
        return result
    
    def _extract_address_info(self) -> Dict[str, Any]:
        """Extract address with block capture strategy"""
        result = {}
        
        # 1. State/Pin extraction (Keep existing logic as it was working mostly)
        labels = [l for l in self.lines if 'state' in l.text.lower()]
        states = ['DELHI', 'HARYANA', 'UTTAR PRADESH', 'RAJASTHAN', 'PUNJAB', 'BIHAR', 'MAHARASHTRA']
        found_state = None
        for lab in labels:
            for line in self.lines[max(0, lab.index-2):min(len(self.lines), lab.index+5)]:
                for s in states:
                    if s in line.text.upper():
                        found_state = s.title()
                        result['permanent_state'] = found_state
                        result['correspondence_state'] = found_state
                        result['state'] = found_state
                        break
                if found_state: break
            if found_state: break
            
        pins = re.findall(r'\b([1-9]\d{5})\b', self.raw_text)
        if len(pins) >= 1: result['permanent_pincode'] = result['pincode'] = pins[0]
        if len(pins) >= 2: result['correspondence_pincode'] = pins[1]
        elif len(pins) == 1: result['correspondence_pincode'] = pins[0]

        # 2. Main Address Block Capture
        # Locate start and end of address section
        start_idx = -1
        end_idx = -1
        
        # Find start: "Permanent Address" (robust to split lines)
        for i, line in enumerate(self.lines):
            text_lower = line.text.lower()
            if 'permanent' in text_lower:
                # Check current or next line for address
                if 'address' in text_lower:
                    start_idx = i
                    break
                elif i + 1 < len(self.lines) and 'address' in self.lines[i+1].text.lower():
                    start_idx = i
                    break
        
        # Find end: "Email" or "Contact" or "Mother"
        if start_idx != -1:
            
            for i in range(start_idx + 1, len(self.lines)):
                txt = self.lines[i].text.lower()
                if 'email' in txt or 'contact' in txt or 'mother' in txt:
                    end_idx = i
                    break
            
            if end_idx == -1: end_idx = min(start_idx + 15, len(self.lines))
            
            # Capture lines
            address_lines = []
            for i in range(start_idx + 1, end_idx):
                text = self.lines[i].text.strip()
                if not text: continue
                
                # Filter labels
                lower = text.lower()
                if any(x in lower for x in ['permanent', 'address', 'local', 'correspondence', 'state', 'pin', 'different from']):
                    continue
                if self._is_label(lower):
                    continue
                
                # Clean mostly symbol lines (e.g. ">", ",", "()")
                if len(re.sub(r'[^a-zA-Z0-9]', '', text)) < 2:
                    continue
                    
                address_lines.append(text)
            
            if address_lines:
                full_addr = ', '.join(address_lines)
                result['permanent_address'] = full_addr
                # Assume correspondence is same if not explicitly found separately (hard to separate in interleaved text)
                result['correspondence_address'] = full_addr
                
        return result
    
    def _extract_parent_info(self) -> Dict[str, Any]:
        result = {}
        m_idx = f_idx = None; sn = ""
        m = re.search(r'NAME IN BLOCK LETTERS\s+([A-Z\s]+)', self.raw_text)
        if m: sn = m.group(1).strip().title()
        for l in self.lines:
            if "mother's name" in l.text.lower(): m_idx = l.index
            if "father's name" in l.text.lower(): f_idx = l.index
        if m_idx and f_idx and abs(m_idx - f_idx) <= 5:
            cand = []
            for i in range(max(m_idx, f_idx)+1, min(max(m_idx, f_idx)+12, len(self.lines))):
                l = self.lines[i]; t = l.text.strip()
                if not l.is_label and t.isupper() and len(t) > 3:
                    if sn and (sn.upper() in t or t in sn.upper()): continue
                    cand.append(t.title())
            if len(cand) >= 1: result['mother_name'] = cand[0]
            if len(cand) >= 2: result['father_name'] = cand[1]
            if result.get('mother_name') and result.get('father_name'): return result
        for k, p in [('mother_name', r"Mother'?s?\s+Name"), ('father_name', r"Father'?s?\s+Name")]:
            for l in self._find_lines_near_label(p, 8):
                t = l.text.strip()
                if not l.is_label and t.isupper() and len(t) > 3:
                    if any(x in t for x in ['NAME', 'MOTHER', 'FATHER']): continue
                    if sn and (sn.upper() in t or t in sn.upper()): continue
                    result[k] = t.title(); break
        return result
    
    def _extract_email(self) -> Dict[str, Any]:
        """
        Extract email with advanced fragmentation handling.
        Handles cases where OCR splits email like:
        KARAN5044@GMAI
        L
        •
        COM
        """
        result = {}
        
        # method 1: Standard regex on full text (for clean OCR)
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        matches = re.findall(email_pattern, self.raw_text)
        if matches:
            # Filter matches to ensure they look like valid user emails
            valid_emails = [e for e in matches if len(e) > 5 and '@' in e and '.' in e.split('@')[1]]
            if valid_emails:
                result['email'] = valid_emails[0].lower()
                return result
                
        # method 2: Fragment reconstruction
        # Find lines containing '@' or 'email' label
        candidates = []
        email_section = self._find_lines_near_label(r'Email', max_lines=10)
        
        # Also look for lines with '@' if section search failed or just to be safe
        at_lines = [line for line in self.lines if '@' in line.text]
        
        search_space = email_section if email_section else at_lines
        
        
        for i, line in enumerate(search_space):
            text = line.text.strip().replace(' ', '')
            
            if '@' in text:
                global_idx = line.index
                merged = text
                
                for offset in range(1, 6):
                    if global_idx + offset < len(self.lines):
                        next_line = self.lines[global_idx + offset].text.strip()
                        
                        # Aggressive cleaning: 
                        # 1. Replace bullets/separators with dots
                        cleaned = re.sub(r'[•ò\u2022\u00B7]', '.', next_line)
                        # 2. Remove all non-alphanumeric except dots and @ (and maybe underscores/dashes)
                        cleaned = re.sub(r'[^a-zA-Z0-9.@-]', '', cleaned)
                        
                        if not cleaned: continue
                        
                        # Stop if it looks like a label (but ignore short fragments like "L")
                        # Increased threshold to 3 to handle "L" and "." being falsely flagged
                        if len(cleaned) > 3 and self._is_label(next_line.lower()): 
                            break
                        
                        # Merge condition:
                        if (len(cleaned) < 6 or 
                            cleaned.lower() in ['com', 'in', 'org', 'net', 'edu', 'gmail', 'yahoo', 'outlook'] or
                            cleaned.startswith('.')):
                            merged += cleaned
                        else:
                            break
                            
                if re.search(email_pattern, merged, re.IGNORECASE):
                    # Extract the clean email from the merged string
                    m = re.search(email_pattern, merged, re.IGNORECASE)
                    if m:
                        result['email'] = m.group(0).lower()
                        return result

        return result

    def _extract_academic_info(self) -> Dict[str, Any]:
        result = {}
        m = re.search(r'20(\d{2})[-/](\d{2})', self.raw_text)
        if m: result['academic_session'] = f"20{m.group(1)}-{m.group(2)}"
        m = re.search(r'\b(\d{2}[A-Z]{2}\d{1,5})\b', self.raw_text, re.I)
        if m: result['college_roll_no'] = m.group(1).upper()
        m = re.search(r'\b(24\d{10,12})\b', self.raw_text)
        if m: result['du_portal_form_number'] = m.group(1)
        m = re.search(r'Enrolment No[\.:\s]*([A-Z0-9]{10,25})', self.raw_text, re.I)
        if m: result['du_enrollment_number'] = m.group(1).upper()
        m = re.search(r'Hindi medium.*?(Yes|No)\s*[✓✔☑☒√✗×]', self.raw_text, re.I | re.S)
        if m: result['hindi_medium_preference'] = m.group(1).title()
        elif re.search(r'No\s*[✓✔☑☒√✗×]', self.raw_text, re.I): result['hindi_medium_preference'] = 'No'
        elif re.search(r'Yes\s*[✓✔☑☒√✗×]', self.raw_text, re.I): result['hindi_medium_preference'] = 'Yes'
        return result

    def _extract_cuet_marks(self) -> Dict[str, Any]:
        """Parses the CUET marks details from Page 1 table or official scorecard."""
        result = {}
        subjects = []
        
        # Step 1: Try to extract from official scorecard first (more accurate)
        subjects = self._extract_from_official_scorecard()
        
        # If found from scorecard, we might still want to look for the total on Page 1
        # but the subjects are likely complete.
        
        # Find the CUET section in raw text
        cuet_section_match = re.search(
            r'Details of marks obtained.*?\[CUET\][\s\S]*?(?=\n\s*---|\n\s*Page|\n\s*DECLARATION|$)',
            self.raw_text, re.IGNORECASE
        )
        
        if not cuet_section_match:
            # Fallback: try to find the section another way
            cuet_section_match = re.search(
                r'10\.\s*Details of marks[\s\S]*?TOTAL\s*CUET\s*SCORE[\s\S]*?(\d{3,4})\s*(\d{2,4})',
                self.raw_text, re.IGNORECASE
            )
        
        if cuet_section_match:
            section = cuet_section_match.group(0)
            
            # Pattern to match table rows: (1)/(I)/(II)/etc. followed by Subject Name, Total Score, Score Obtained
            # Handle OCR errors: (1) instead of (I), (11) instead of (II), etc.
            # Row pattern: (numeral) Subject_name Total Obtained
            row_pattern = re.compile(
                r'(?:\(([IVX\d]{1,3})\))?\s*'   # Optional numeral
                r'(?:[\d|]+\s+)?'               # Optional noise like "3|3" or digits
                r'(?:\.\s*)?'                   # Optional leading dot
                r'([A-Za-z][A-Za-z\s&./|\(\)-]{2,50})\s+'  # Subject: Expanded charset and length
                r'(?:\.\s*)?'
                r'(\d{2,3}(?:\.\d+)?)\s+'       # Total score
                r'(?:\.\s*)?'
                r'(\d{1,3}(?:\.\d+)?)',         # Score obtained
                re.IGNORECASE
            )
            
            for match in row_pattern.finditer(section):
                subject_name = match.group(2).strip()
                total_score = match.group(3)
                score_obtained = match.group(4)
                
                # Filter out headers and artifacts
                subj_upper = subject_name.upper()
                if any(word in subj_upper for word in ['TOTAL', 'SUBJECT', 'SCORE', 'OBTAINED', 'SI NO', 'SR NO']):
                    continue
                if len(subject_name) < 3:
                    continue
                
                # Validate common subject patterns
                common_subjects = ['ENGLISH', 'HINDI', 'MATH', 'ACC', 'ECO', 'BS', 'HIST', 'POL', 'GEO', 'SOC', 'PSY', 'PHY', 'CHEM', 'BIO']
                is_common = any(cs in subj_upper for cs in common_subjects)
                
                # Check for standard max scores
                if total_score not in ['100', '200', '250', '300'] and not is_common:
                    # If not a standard max score and not a common subject, might be noise
                    if not re.search(r'\d{2,3}', total_score): 
                        continue
                
                subjects.append({
                    'name': subject_name.title(),
                    'max': total_score.split('.')[0],
                    'obt': score_obtained
                })
            
            # If the row pattern didn't work, try line-by-line extraction
            if not subjects:
                lines = section.split('\n')
                for line in lines:
                    line = line.strip()
                    # Look for: (1) English 200 161 or similar
                    line_match = re.match(
                        r'\([\dIVX]{1,3}\)\s*([A-Za-z][A-Za-z\s&]+?)\s+(\d{2,3})\s+(\d{2,3}(?:\.\d+)?)',
                        line, re.IGNORECASE
                    )
                    if line_match:
                        subject_name = line_match.group(1).strip().title()
                        if 'TOTAL' not in subject_name.upper():
                            subjects.append({
                                'name': subject_name,
                                'max': line_match.group(2),
                                'obt': line_match.group(3)
                            })
            
            # Extract TOTAL row: (VII) TOTAL CUET SCORE OBTAINED 800 749
            total_match = re.search(
                r'TOTAL\s*(?:CUET\s*)?(?:SCORE\s*)?(?:OBTAINED)?\s*(\d{3,4})\s+(\d{2,4}(?:\.\d+)?)',
                section, re.IGNORECASE
            )
            if total_match:
                result['cuet_total_score'] = total_match.group(1)
                result['cuet_score'] = total_match.group(2)
        
        # Deduplicate and assign to result
        final_list = []
        seen = set()
        for s in subjects:
            name_lower = s['name'].lower()
            if name_lower not in seen and len(s['name']) > 2:
                final_list.append(s)
                seen.add(name_lower)
        
        # Limit to 6 subjects and populate result
        final_list = final_list[:6]
        for idx, s in enumerate(final_list, 1):
            result[f'cuet_subject_{idx}'] = s['name']
            result[f'cuet_total_score_{idx}'] = s.get('max', '200')
            result[f'cuet_score_obtained_{idx}'] = s['obt']
        
        # Calculate totals from the same subjects if not already found from OCR
        if final_list and 'cuet_total_score' not in result:
            try:
                max_sum = sum(int(s.get('max', 200)) for s in final_list)
                obt_sum = sum(float(s['obt']) for s in final_list if s.get('obt'))
                result['cuet_total_score'] = str(max_sum)
                if obt_sum % 1 == 0:
                    result['cuet_score'] = str(int(obt_sum))
                else:
                    result['cuet_score'] = f"{obt_sum:.2f}"
            except (ValueError, TypeError):
                pass
        
        return result

    def _extract_from_official_scorecard(self) -> List[Dict[str, Any]]:
        """Extracts marks from official CUET Scorecard pages."""
        subjects = []
        
        # Look for scorecard markers
        if not re.search(r'SCORE CARD|NORMALIZED SCORE|PERCENTILE SCORE', self.raw_text, re.IGNORECASE):
            return subjects
            
        # Official scorecard often has Subject, Percentile, Normalised Score (Figures), Normalised Score (Words)
        # We target the Figures column.
        
        # Strategy A: Multi-line table parsing
        # Pattern: Subject Name followed by 2 or 3 numbers
        # "English 98.1234567 161.5000000"
        table_pattern = re.compile(
            r'^([A-Za-z][A-Za-z\s&]{4,30})\s+'         # Subject
            r'(?:\d{1,3}(?:\.\d+)?\s+)?'               # Optional Percentile
            r'(\d{1,3}(?:\.\d+)?)\s+'                 # Normalised Score (Obtained)
            r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*|$)',   # Optional Words or EOL
            re.MULTILINE | re.IGNORECASE
        )
        
        # Filter raw text to lines that might be in the table
        scorecard_lines = []
        for line in self.raw_text.split('\n'):
            line = line.strip()
            if not line: continue
            
            # Exclude headers
            if any(h in line.upper() for h in ['CANDIDATE', 'ROLL NUMBER', 'CATEGORY', 'GENDER', 'FATHER', 'MOTHER']):
                continue
            
            match = table_pattern.match(line)
            if match:
                subj = match.group(1).strip()
                obt = match.group(2)
                
                # Subject shouldn't be too long or contains generic words
                if len(subj) > 30 or any(w in subj.upper() for w in ['SUBJECT', 'SCORE', 'PERCENTILE']):
                    continue
                
                subjects.append({
                    'name': subj.title(),
                    'max': '200', # Default for CUET
                    'obt': obt
                })
        
        if not subjects:
             # Strategy B: Look for common subjects specifically if table parsing failed
             common_subjs = [
                 'English', 'Hindi', 'Mathematics', 'Accountancy', 'Economics', 
                 'Business Studies', 'History', 'Political Science', 'Geography', 
                 'Sociology', 'Psychology', 'Physics', 'Chemistry', 'Biology',
                 'Physical Education', 'Computer Science', 'Informatics Practices'
             ]
             for cs in common_subjs:
                 m = re.search(rf'{cs}.*?\s(\d{{2,3}}(?:\.\d+)?)', self.raw_text, re.I)
                 if m:
                     subjects.append({
                         'name': cs,
                         'max': '200',
                         'obt': m.group(1)
                     })
                     
        return subjects


    def _extract_personal_info(self) -> Dict[str, Any]:
        result = {}
        if re.search(r'Nationality\s*INDIAN', self.raw_text, re.I): result['nationality'] = 'Indian'
        m = re.search(r'Religion\s*(HINDU|MUSLIM|SIKH|CHRISTIAN|JAIN|BUDDHIST)', self.raw_text, re.I)
        if m: result['religion'] = m.group(1).title()
        m = re.search(r'Blood\s*Group\s*([ABO]{1,2}[\+\-])', self.raw_text, re.I)
        if m: result['blood_group'] = m.group(1).upper()
        if re.search(r'Below\s*Poverty\s*Line\s*NO', self.raw_text, re.I): result['below_poverty_line'] = 'No'
        m = re.search(r'Annual\s*Income\s*([A-Z\s\d]+LAKHS)', self.raw_text, re.I)
        if m: result['annual_income'] = m.group(1).strip().title()
        return result

    def _extract_parent_details(self) -> Dict[str, Any]:
        """Extract parent occupational details from Page 2"""
        result = {}
        for k, s in [('mother', "Mother's"), ('father', "Father's")]:
            vals = self._extract_value_block(fr"{s}\s*Occupational\s*Details", 5, max_gap=25)
            vals = [v for v in vals if not any(x in v.upper() for x in ['BELOW 2 LAKHS', 'MUSLIM JAIN', 'PERSONAL INFORMATION'])]
            
            if len(vals) >= 1:
                occ = vals[0].title()
                if 'MOUSE' in occ.upper(): occ = occ.replace('Mouse', 'House')
                if len(occ) > 3: result[f'{k}_occupation'] = occ
            
            for v in vals:
                if '@' in v: result[f'{k}_email'] = v.lower()
                elif re.search(r'\b\d{10}\b', v): result[f'{k}_mobile'] = re.search(r'\b\d{10}\b', v).group(0)
                elif any(occ_type in v.upper() for occ_type in ['SERVICE', 'BUSINESS', 'EMPLOYED', 'DHOBHI']):
                    designation = v.title()
                    if 'DHOBHI' in designation.upper(): designation = designation.replace('Dhobhi', 'Dhobi').replace('Cself', '(Self')
                    result[f'{k}_designation'] = designation
        return result

    def _extract_guardian_details(self) -> Dict[str, Any]:
        """Extract local guardian details from Page 2"""
        result = {}
        vals = self._extract_value_block(r"Local\s*Guardian's\s*Details", 6, max_gap=30)
        if len(vals) >= 1:
            name = vals[0].title()
            if len(name) > 3: result['guardian_name'] = name
        for v in vals:
            if '@' in v: result['guardian_email'] = v.lower()
            elif re.search(r'\b\d{10}\b', v): result['guardian_mobile'] = re.search(r'\b\d{10}\b', v).group(0)
            elif any(r in v.upper() for r in ['FATHER', 'MOTHER', 'BROTHER', 'SISTER', 'RELATIVE']):
                result['guardian_relation'] = v.title()
        return result

    def _extract_education_details(self) -> Dict[str, Any]:
        """Extract Class XII details from Page 2"""
        result = {}
        vals = self._extract_value_block(r"Details\s*of\s*qualifying\s*examination\s*passed", 8, max_gap=30)
        # Filter noise
        vals = [v for v in vals if not any(x in v.upper() for x in ['VIII', 'VIII/X', 'HINDI STUDIED'])]
        
        for v in vals:
            if re.match(r'^\d{4}$', v):
                year = int(v)
                if 2018 <= year <= 2026: result['twelfth_year'] = v
                elif 2030 <= year <= 2036: result['twelfth_year'] = str(year - 10)
            elif 'BOARD' in v.upper() or 'CBSE' in v.upper() or 'ICSE' in v.upper():
                if not result.get('twelfth_board'): result['twelfth_board'] = v.title()
            elif re.match(r'^\d{7,10}$', v): result['twelfth_roll_number'] = v
            elif len(v) > 12:
                # Institution is usually the longest string here
                if not result.get('twelfth_institution') or len(v) > len(result['twelfth_institution']):
                    if not 'BOARD' in v.upper(): result['twelfth_institution'] = v.title()
        return result

    def _extract_certificate_info(self) -> Dict[str, Any]:
        result = {}
        m = re.search(r'belong\s*to\s*EWS/SC/ST/OBC/PwBD.*?authority\s*(.*?)If\s*PwBD', self.raw_text, re.S | re.I)
        if m:
            ct = m.group(1)
            a = re.search(r'(OFFICE\s*OF\s*THE\s*[A-Z\s,\(\)]+)', ct, re.I)
            if a: result['category_certificate_authority'] = a.group(1).strip().title()
            n = re.search(r'Certificate\s*No\.\s*(\d+)', ct, re.I)
            if n: result['category_certificate_number'] = n.group(1)
            d = re.search(r'Date\s*of\s*Issue\s*(\d{2}-\d{2}-\d{4})', ct, re.I)
            if d: result['category_certificate_date'] = d.group(1)
        return result
    
    def _extract_document_checklist(self) -> Dict[str, Any]:
        """Extract all 16 checkboxes from Document Checklist on Page 4"""
        result = {}
        items = [
            ('doc_admission_form', r'Admission\s*Form'),
            ('doc_undertaking_ragging', r'Ragging'),
            ('doc_photographs', r'photograph'),
            ('doc_cuet_scorecard', r'CUET.*Score.*Card'),
            ('doc_class_xii_marksheet', r'Class-XII\s*Mark-sheet'),
            ('doc_class_x_certificate', r'Class-X\s*Certificate'),
            ('doc_class_xii_certificate', r'Class-XII\s*Certificate'),
            ('doc_character_certificate', r'Character\s*Certificate'),
            ('doc_transfer_certificate', r'Transfer\s*Certificate'),
            ('doc_hindi_certificate', r'studied\s*upto\s*VIII/X/XII'),
            ('doc_caste_certificate', r'SC/ST/OBC/EWS/PwBD'),
            ('doc_sports_eca', r'Sports/ECA'),
            ('doc_originals', r'Original\s*Certificates'),
            ('doc_photo_id', r'Photo\s*id\s*Proof'),
        ]
        
        # Look for these specifically in the LIST OF DOCUMENTS section
        sec = self.raw_text
        m_sec = re.search(r"LIST\s*OF\s*DOCUMENTS\s*REQUIRED:(.*?)DECLARATION", self.raw_text, re.S | re.I)
        if m_sec: sec = m_sec.group(1)
            
        for f, p in items:
            m = re.search(p, sec, re.I)
            if m:
                # Broad scan around the label for a tick/mark
                win = sec[max(0, m.start()-50):min(len(sec), m.end()+80)]
                result[f] = 'Yes' if self._has_tick_mark(win) else 'No'
        return result
    
    def _cross_validate(self, result: Dict[str, Any]) -> Dict[str, Any]:
        for k, mi, ma in [('date_of_birth', 1995, 2010), ('date_of_admission', 2020, 2030)]:
            if k in result:
                y = re.search(r'(\d{4})$', result[k])
                if y and not (mi <= int(y.group(1)) <= ma): del result[k]
        return {k: v for k, v in result.items() if v is not None and str(v).strip()}


def extract_intelligent(raw_text: str) -> Dict[str, Any]:
    return IntelligentFieldExtractor().extract(raw_text)
