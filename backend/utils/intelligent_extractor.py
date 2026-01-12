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
    
    # Common form labels to skip when extracting values
    FORM_LABELS = [
        'first name', 'middle name', 'surname', 'name in block letters',
        'date of birth', 'date of admission', 'gender', 'category',
        'd d', 'm m', 'y y y y', 'yyyy', 'dd', 'mm',
        'male', 'female', 'transgender', 'tick', 'please tick',
        'state', 'pin', 'pincode', 'address', 'permanent', 'correspondence',
        'phone', 'mobile', 'email', 'contact', 'signature',
        "mother's name", "father's name", "guardian's name",
        'occupation', 'designation', 'organization', 'annual income',
        'blood group', 'nationality', 'religion', 'aadhar',
        'class x', 'class xii', 'board', 'year', 'percentage', 'school',
        'cuet', 'score', 'total', 'obtained', 'subject',
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
        
        candidates = []
        for line in name_area:
            text = line.text.strip()
            # Strict filter for name artifacts
            if not text or len(text) < 3: continue
            if self._is_label(text): continue
            
            # Filter out known labels that might have been missed by _is_label
            if any(x in text.upper() for x in ['DATE OF BIRTH', 'SEX', 'GENDER', 'PERMANENT ADDRESS', 'BLOCK LETTERS']):
                continue
            
            # Skip occupational noise if we've drifted too far
            if any(x in text.upper() for x in ['HOUSE', 'WIFE', 'DHOBI', 'SERVICE', 'OCCUPATION']):
                continue

            num_prefix = re.match(r'^(\d+)\.?\s*(.*)$', text)
            if num_prefix:
                val = num_prefix.group(2).strip()
                # Strict filter for name artifacts (Y Y, M M, D D, and alphanumeric IDs)
                if val.isupper() and len(val) >= 3 and not re.search(r'\b[YMD]\s+[YMD]\b', val):
                    # Filter out alphanumeric IDs like YBC102
                    if not re.search(r'\d', val):
                        candidates.append({'idx': line.index, 'val': val, 'prefix': int(num_prefix.group(1))})
            elif text.isupper() and len(text) >= 3 and not re.search(r'\b[YMD]\s+[YMD]\b', text):
                if sum(c.isalpha() for c in text) / len(text) > 0.8: # Stricter alpha check
                    if not re.search(r'\d', text):
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
        result = {}
        labels = [l for l in self.lines if 'state' in l.text.lower()]
        states = ['DELHI', 'HARYANA', 'UTTAR PRADESH', 'RAJASTHAN', 'PUNJAB', 'BIHAR', 'MAHARASHTRA']
        for lab, k in zip(labels[:2], ['permanent_state', 'correspondence_state']):
            for line in self.lines[max(0, lab.index-2):min(len(self.lines), lab.index+5)]:
                for s in states:
                    if s in line.text.upper():
                        result[k] = s.title()
                        if k == 'permanent_state': result['state'] = s.title()
                        break
        pins = re.findall(r'\b([1-9]\d{5})\b', self.raw_text)
        if len(pins) >= 1: result['permanent_pincode'] = result['pincode'] = pins[0]
        if len(pins) >= 2: result['correspondence_pincode'] = pins[1]
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
        """Parses the CUET marks details strictly from Page 1 table, enriched by scorecard."""
        result = {}; subjects = []
        
        # 1. Surgical Scorecard Extraction (Reference Data Only)
        scorecard_db = []
        sc_start = self.raw_text.find("Score Card Details")
        if sc_start == -1: sc_start = self.raw_text.find("Candidate's Name")
        
        if sc_start != -1:
            raw_sc = self.raw_text[sc_start:sc_start+4000]
            clean_sc = re.sub(r'(301|305|309|319|101|501)\s*\n', r'\1 ', raw_sc)
            
            # Pattern A: Code Name Max Marks
            p1 = re.findall(r'(\d{3})\s+([A-Z\s/]{5,50})\s+(200|250|100)\s+([\d\.]+)', clean_sc)
            for code, name_raw, mx, s in p1:
                name = name_raw.strip().replace('\n', ' ').title()
                if any(x in name.upper() for x in ['CONDUCT', 'DETAILS', 'TOTAL', 'MARKS']): continue
                scorecard_db.append({
                    'name': name,
                    'obt': s.split('.')[0] + '.' + s.split('.')[1][:2] if '.' in s else s,
                    'max': mx,
                    'code': code
                })
            
            # Pattern B: Fragmented
            for code in ['101', '301', '305', '309', '319', '501']:
                if code not in [s.get('code') for s in scorecard_db if s.get('code')]:
                    m = re.search(r'([A-Z\s/&#]{5,40})\s+' + code + r'\s+(200|250|100)\s+([\d\.]+)', clean_sc, re.S)
                    if m:
                        name = m.group(1).strip().replace('\n', ' ').title()
                        scorecard_db.append({'name': name, 'obt': m.group(3), 'max': m.group(2)})

        # 2. Form Table Extraction (Page 1) - THE SOURCE OF TRUTH
        s_idx = -1
        # Look for the table header specifically
        for i, l in enumerate(self.lines):
            if 'Details of marks obtained' in l.text or 'Examination: [CUET]' in l.text: s_idx = i; break
        
        if s_idx != -1:
            for i in range(1, 60):
                if s_idx + i >= len(self.lines): break
                t = self.lines[s_idx + i].text.strip()
                if 'TOTAL' in t.upper() and i > 5: break
                
                # Exclude lines that are clearly scores, dates, or noise
                if re.match(r'^[\d\.]+$', t) or re.match(r'^\d{2}/\d{2}/\d{4}$', t): continue

                # Match subject names in the table (e.g. "(1) English" or just "English")
                m_sub = re.match(r'^(?:\(?([IVX]+|\d+)\)?\s+)?([A-Za-z\s/&]+?)$', t)
                if m_sub:
                    name = m_sub.group(2).strip().title()
                    # Filter out common noise in table headers/footers
                    if name and len(name) > 2 and not any(x in name.upper() for x in ['DETAILS', 'QUALIFYING', 'TOTAL', 'MARKS', 'SCORE', 'OBTAINED', 'MAXIMUM']):
                        sub = {'name': name, 'obt': None, 'max': '200'}
                        
                        # A. Try to find score in table (handwritten/printed nearby)
                        for j in range(1, 15):
                            if s_idx + i + j < len(self.lines):
                                line_score = self.lines[s_idx + i + j].text.strip()
                                m_score = re.search(r'\b(200|250|100)\s+([\d\.]+)\b', line_score)
                                if m_score:
                                    sub['max'], sub['obt'] = m_score.groups()
                                    break
                        
                        # B. If not found in table, lookup in Scorecard DB (Enrichment)
                        if not sub['obt']:
                            sc_match = next((s for s in scorecard_db if sub['name'].lower() in s['name'].lower() or s['name'].lower() in sub['name'].lower()), None)
                            if sc_match:
                                sub['obt'] = sc_match['obt']
                                sub['max'] = sc_match['max']
                                # Optional: Standardize name from scorecard for cleaner text?
                                # sub['name'] = sc_match['name'] 
                        
                        # Only add if it's a valid subject entry from the table
                        subjects.append(sub)

        # 3. Finalization
        # Use whatever we found in the table. If table was empty, subjects is empty.
        final_list = []
        seen = set()
        for s in subjects:
            if s['name'].lower() not in seen:
                final_list.append(s); seen.add(s['name'].lower())
        
        # Populate result (Dynamic up to 10)
        for idx, s in enumerate(final_list[:10], 1):
            result[f'cuet_subject_{idx}'] = s['name']
            result[f'cuet_total_score_{idx}'] = s.get('max', "200")
            result[f'cuet_score_obtained_{idx}'] = s['obt']
        
        # Total score
        total_matches = list(re.finditer(r'TOTAL\s*(?:CUET\s*SCORE\s*)?(?:OBTAINED)?.*?(\d{3,4})[\s:]*?(\d{2,4}(?:\.\d+)?)', self.raw_text, re.I | re.S))
        
        # Calculate from table subjects
        if final_list:
            try:
                obt_sum = sum(float(s['obt']) for s in final_list if s.get('obt'))
                max_sum = sum(int(s.get('max', 200)) for s in final_list)
                result['cuet_total_score'] = str(max_sum)
                result['cuet_score'] = f"{obt_sum:.2f}" if obt_sum % 1 != 0 else str(int(obt_sum))
            except Exception: pass
            
        # Override with explicit Total from text if valid
        if total_matches:
            for m in reversed(total_matches):
                t_max, t_obt = m.groups()
                try:
                    tm = int(t_max); to = float(t_obt)
                    if tm >= 400 and tm % 10 == 0 and to >= 100 and to < tm:
                        # Only override if the calculated sum is wildly different or missing
                        if 'cuet_score' not in result or abs(float(result['cuet_score']) - to) > 10:
                            result['cuet_total_score'] = str(tm)
                            result['cuet_score'] = str(to) if to % 1 == 0 else f"{to:.2f}"
                        break
                except: continue
            
        return result


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
            vals = self._extract_value_block(f"{s}\s*Occupational\s*Details", 5, max_gap=25)
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
        vals = self._extract_value_block("Local\s*Guardian's\s*Details", 6, max_gap=30)
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
        vals = self._extract_value_block("Details\s*of\s*qualifying\s*examination\s*passed", 8, max_gap=30)
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
