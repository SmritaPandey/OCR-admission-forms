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
        # Basic Details - Improved patterns to avoid labels
        'student_name': [
            # Pattern: "NAME IN BLOCK LETTERS" followed by name on next line(s) - but skip the label itself
            r'(?:name\s+in\s+block\s+letters|name\s+in\s+block)\s*\n\s*(?!.*(?:in\s+block\s+letters|block\s+letters))([A-Z][A-Z\s]{2,30}?)(?:\n|first\s+name|middle\s+name|surname|date|dob|gender)',
            # Pattern: Name field with actual name (not labels) - explicitly exclude "in block letters"
            r'(?:name|student\s+name|applicant\s+name|full\s+name)[:\s]*\n\s*(?!.*(?:in\s+block\s+letters|block\s+letters))([A-Z][A-Z\s]{2,30}?)(?:\n|first|middle|surname|date|dob|gender|phone|email)',
        ],
        'first_name': [
            r'(?:first\s+name)[:\s]*\n?\s*([A-Z][A-Z\s]{2,20}?)(?:\n|middle|surname|date|dob|gender)',
            r'^([A-Z]{2,})\s+(?=[A-Z]{2,})',  # First word of a name
        ],
        'surname': [
            r'(?:surname|last\s+name)[:\s]*\n?\s*([A-Z][A-Z\s]{2,20}?)(?:\n|first|middle|date|dob)',
        ],
        'middle_name': [
            r'(?:middle\s+name)[:\s]*\n?\s*([A-Z][A-Z\s]{2,20}?)(?:\n|first|surname|date)',
        ],
        'date_of_birth': [
            # Pattern: Date scattered across lines (DD MM YYYY format) - handled in _extract_scattered_values
            # Pattern: Standard date format
            r'(?:dob|date\s+of\s+birth|birth\s+date)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            r'(?:dob|date\s+of\s+birth)[:\s]+(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
        ],
        'gender': [
            # Pattern: Look for checked gender option near "Gender" label
            r'(?:gender|sex)[:\s]*\n?.*?(male|female|transgender)\s*[✓√]',
            r'(?:gender|sex)[:\s]*\n?\s*(male|female|transgender)\s*[✓√]',
            # Pattern: Standard gender field
            r'(?:gender|sex)[:\s]+(male|female|other|transgender|m|f)',
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
            # Pattern: Contact Numbers field followed by scattered digits
            r'(?:contact\s+numbers?)[:\s]*\n?(?:\s*\d+\s*){10,15}',
            # Pattern: Standard phone number (10-15 digits)
            r'(?:phone|mobile|contact|tel|phone\s+no|mobile\s+no)[:\s]+([+\d\s\-()]{10,15})',
            # Pattern: Direct phone number match
            r'(?:^|\n)\s*(\d{10,15})\s*(?:\n|email|mother|father|guardian|$)',
        ],
        'alternate_phone': [
            r'(?:alternate\s+phone|alt\s+phone|alternate\s+mobile|secondary\s+phone)[:\s]+([+\d\s\-()]{10,15})',
            r'(?:alternate|alt)[:\s]+(\d{10,15})',
        ],
        'email': [
            # Pattern: Email scattered across lines (reconstructed by _extract_scattered_values)
            r'(?:email|e-mail)[:\s]*\n?.*?([a-zA-Z0-9\s]+@[a-zA-Z0-9\s]+\.[a-zA-Z0-9\s]+)',
            # Pattern: Standard email format
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
            # Pattern: "Father's Name" followed by name (can be scattered across lines)
            r'(?:father\'?s\s+name|father\s+name)[:\s]*\n?\s*([A-Z][A-Z\s]{2,30}?)(?:\n|mother|guardian|details|occupation|phone|0\.)',
            # Pattern: Look for name after "Father's Name" label, collect from multiple lines
            r'(?:father\'?s\s+name)[:\s]*\n\s*([A-Z]{2,})\s*\n\s*([A-Z]{2,})',
            r'(?:father)[:\s]+([A-Z][A-Z\s]{2,30}?)(?:\n|mother|guardian)',
        ],
        'father_occupation': [
            r'(?:father\'?s\s+occupation|father\s+occupation)[:\s]+([A-Za-z\s]+)',
        ],
        'father_phone': [
            r'(?:father\'?s\s+phone|father\s+phone|father\s+contact)[:\s]+([+\d\s\-()]{10,15})',
        ],
        'mother_name': [
            # Pattern: "Mother's Name" followed by name (can be scattered across lines)
            r'(?:mother\'?s\s+name|mother\s+name)[:\s]*\n?\s*([A-Z][A-Z\s]{2,30}?)(?:\n|father|guardian|details|occupation|phone|0\.)',
            # Pattern: Look for name after "Mother's Name" label, collect from multiple lines
            r'(?:mother\'?s\s+name)[:\s]*\n\s*([A-Z0-9]{2,})\s*\n\s*([A-Z]{1,})\s*\n\s*([A-Z]{2,})\s*\n\s*([A-Z]{2,})',
            r'(?:mother)[:\s]+([A-Z][A-Z\s]{2,30}?)(?:\n|father|guardian|details)',
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
        'enrollment_number': [
            r'(?:enrollment\s+no|enrollment\s+number|enrol\s+no|enrolment\s+number|roll\s+no|roll\s+number)[:\s]+([A-Z0-9\-\/]+)',
            r'(?:enrollment|enrolment|roll)[:\s]+([A-Z0-9\-\/]+)',
        ],
        'admission_date': [
            r'(?:admission\s+date|date\s+of\s+admission)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        ],
        
        # Academic & Admission Details
        'academic_session': [
            r'(?:academic\s+session|session|academic\s+year)[:\s]*\n?\s*(\d{4}[\-]\d{2,4})',
            r'(?:academic\s+session)[:\s]*\n\s*(\d{4}[\-]\d{2,4})',  # On next line after label
            # Don't match CUET score pattern (887-3301) - must be year pattern (2025-28)
            r'^(\d{4}[\-]\d{2})$',  # Standalone pattern like 2025-28 (2-digit end)
        ],
        'college_roll_no': [
            r'(?:college\s+roll\s+no|college\s+roll|roll\s+no|roll\s+number)[:\s]*\n?\s*([A-Z0-9]{4,10})',
            r'(\d{2}[A-Z]{2}\d{3})',  # Pattern like 25BC528
            r'([A-Z0-9]{4,10})(?=\s*(?:date|admission|km|others|eca))',  # Before date/admission category
        ],
        'cuet_score': [
            # Pattern: CUET Score field - look for pattern like "887-3301" after "CUET Score" label
            r'(?:cuet\s+score)[:\s]*\n?\s*(\d{3,4}[\-]\d{3,4})',  # Pattern like 887-3301
            # Pattern: Look for score before "College Roll No"
            r'(\d{3,4}[\-]\d{3,4})(?=\s*(?:college\s+roll|date\s+of\s+admission))',
        ],
        'du_portal_form_number': [
            r'(?:ou\s+portal\s+form\s+number|du\s+portal\s+form|portal\s+form\s+number)[:\s]+([A-Z0-9]+)',
        ],
        'admission_category': [
            r'(?:admission\s+category)[:\s]+(gen|obc|sc|st|sports|pwd|ews|foreign|cw|km|others|eca)',
        ],
        'course': [
            r'(?:course)[:\s]+(b\.com\.?\s*\(?h\)?|b\.a\.?\s*\(?h\)?\s*eco)',
            r'(b\.com|b\.a|commerce|economics)',
        ],
        
        # CUET Marks - Improved extraction
        'cuet_subject_1': [
            r'\(1\)\s*ENGLISH',
        ],
        'cuet_score_obtained_1': [
            r'\(1\)\s*ENGLISH.*?(\d{3,6}\.?\d*)',  # Extract score after ENGLISH
            r'ENGLISH.*?(\d{3,6}\.?\d*)',
        ],
        'cuet_subject_2': [
            r'\(11\)\s*ACCOUNTANCY',
        ],
        'cuet_score_obtained_2': [
            r'\(11\)\s*ACCOUNTANCY.*?(\d{3,6}\.?\d*)',
            r'ACCOUNTANCY.*?(\d{3,6}\.?\d*)',
        ],
        'cuet_subject_3': [
            r'\(1\)\s*BUSINESS\s+STUDIES',
        ],
        'cuet_score_obtained_3': [
            r'\(1\)\s*BUSINESS\s+STUDIES.*?(\d{3,6}\.?\d*)',
            r'BUSINESS\s+STUDIES.*?(\d{3,6}\.?\d*)',
        ],
        'cuet_subject_4': [
            r'\(IV\)\s*ECONOMICS',
        ],
        'cuet_score_obtained_4': [
            r'\(IV\)\s*ECONOMICS.*?(\d{3,6}\.?\d*)',
            r'ECONOMICS.*?(\d{3,6}\.?\d*)',
        ],
        'cuet_subject_5': [
            r'\(V\)\s*MATHEMATICS',
        ],
        'cuet_score_obtained_5': [
            r'\(V\)\s*MATHEMATICS.*?(\d{3,6}\.?\d*)',
            r'MATHEMATICS.*?(\d{3,6}\.?\d*)',
        ],
        'cuet_total_score': [
            r'(?:total\s+cuet\s+score\s+obtained|total\s+score)[:\s]*\n?\s*(\d+[\-]?\d*)',
            r'(\d{3,6}[\-]\d{3,6})',  # Pattern like 887-3301
        ],
        
        # Parent Details - Extended
        'father_organization': [
            r'(?:father.*?organization|father.*?address)[:\s]+([^\n]{5,200})',
        ],
        'father_designation': [
            r'(?:father.*?designation)[:\s]+([A-Za-z\s]+)',
        ],
        'mother_organization': [
            r'(?:mother.*?organization|mother.*?address)[:\s]+([^\n]{5,200})',
        ],
        'mother_designation': [
            r'(?:mother.*?designation)[:\s]+([A-Za-z\s]+)',
        ],
        'guardian_residential_address': [
            r'(?:guardian.*?residential\s+address|guardian.*?address)[:\s]+([^\n]{5,200})',
        ],
        'guardian_organization': [
            r'(?:guardian.*?organization)[:\s]+([^\n]{5,200})',
        ],
        
        # Certificate Details
        'category_certificate_authority': [
            r'(?:certificate\s+issuing\s+authority|authority)[:\s]+([^\n]{3,200})',
        ],
        'category_certificate_number': [
            r'(?:certificate\s+no)[:\s]+([A-Z0-9]+)',
        ],
        'category_certificate_date': [
            r'(?:date\s+of\s+issue)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        ],
        'du_enrollment_number': [
            r'(?:delhi\s+university\s+enrollment\s+no|du\s+enrollment)[:\s]+([A-Z0-9]+)',
        ],
        'hindi_studied_upto': [
            r'(?:hindi\s+studied\s+upto)[:\s]+(viii|x|xii|never)',
        ],
        'hindi_medium_preference': [
            r'(?:hindi\s+medium|teach\s+in\s+hindi)[:\s]+(yes|no)',
        ],
        'twelfth_roll_number': [
            r'(?:examination\s+roll\s+no|exam\s+roll\s+no)[:\s]+([A-Z0-9]+)',
        ],
        'twelfth_institution': [
            r'(?:institution\s+last\s+attended)[:\s]+([^\n]{3,200})',
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
        
        # Keep original lines for multi-line extraction
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        # First, extract structured fields that need special handling
        parsed.update(self._extract_name_fields(raw_text, lines))
        parsed.update(self._extract_scattered_values(raw_text, lines))
        
        # Normalize text for pattern matching (but keep original for special cases)
        text_normalized = re.sub(r'\s+', ' ', text)
        
        # Extract each field using patterns
        for field_name, patterns in self.FIELD_PATTERNS.items():
            # Skip if already extracted by special handlers
            if field_name not in parsed:
                value = self._extract_field(text_normalized, text_lower, lines, patterns, field_name)
                if value:
                    parsed[field_name] = value
        
        return parsed
    
    def _extract_name_fields(self, raw_text: str, lines: list) -> Dict[str, Any]:
        """Extract name fields from NAME IN BLOCK LETTERS section"""
        result = {}
        
        # Find "NAME IN BLOCK LETTERS" section
        name_section_start = None
        for i, line in enumerate(lines):
            if 'name in block letters' in line.lower():
                name_section_start = i
                break
        
        if name_section_start is not None:
            # Look for name components in next few lines
            name_parts = []
            for i in range(name_section_start + 1, min(name_section_start + 8, len(lines))):
                line = lines[i].strip()
                line_lower = line.lower()
                
                # Stop at labels - including "in block letters" itself
                if any(label in line_lower for label in ['first name', 'middle name', 'surname', 'signature', 'gender', 'date of birth', 'dob', 'in block letters', 'block letters']):
                    break
                
                # Skip if this line is just the label text
                if 'in block letters' in line_lower or 'block letters' in line_lower:
                    continue
                
                # Collect name parts (all caps words, 2+ chars, not single letters)
                words = re.findall(r'\b[A-Z]{2,}\b', line)
                # Filter out common non-name words and label words
                filtered_words = [w for w in words if w not in ['DD', 'MM', 'YYYY', 'PIN', 'STATE', 'EMAIL', 'CONTACT', 'BLOCK', 'LETTERS', 'NAME', 'IN']]
                if filtered_words:
                    name_parts.extend(filtered_words)
            
            if len(name_parts) >= 2:
                # In Indian forms, typically: SURNAME FIRST_NAME (e.g., HANFI SARA)
                # But we want: FIRST_NAME SURNAME (e.g., SARA HANFI)
                # Check form structure - if "First Name" label comes after, then first part is surname
                # Look for "First Name" label after name section
                has_first_name_label = False
                for i in range(name_section_start, min(name_section_start + 10, len(lines))):
                    if 'first name' in lines[i].lower():
                        has_first_name_label = True
                        break
                
                if has_first_name_label:
                    # Form has separate First/Middle/Surname fields
                    # First part in NAME IN BLOCK LETTERS is usually SURNAME
                    surname = name_parts[0]
                    first_name = name_parts[-1] if len(name_parts) > 1 else ''
                    middle_name = ' '.join(name_parts[1:-1]) if len(name_parts) > 2 else ''
                    # Full name: first middle surname
                    full_name_parts = [first_name]
                    if middle_name:
                        full_name_parts.append(middle_name)
                    full_name_parts.append(surname)
                    full_name = ' '.join(full_name_parts)
                else:
                    # No separate fields - assume normal order
                    first_name = name_parts[0]
                    surname = name_parts[-1]
                    middle_name = ' '.join(name_parts[1:-1]) if len(name_parts) > 2 else ''
                    full_name = ' '.join(name_parts)
                
                result['student_name'] = full_name
                result['first_name'] = first_name
                result['surname'] = surname
                if middle_name:
                    result['middle_name'] = middle_name
        
        return result
    
    def _extract_scattered_values(self, raw_text: str, lines: list) -> Dict[str, Any]:
        """Extract values that are scattered across multiple lines in OCR"""
        result = {}
        
        # Extract scattered email (look for @ symbol and reconstruct)
        # Find "Email" section
        email_start = None
        for i, line in enumerate(lines):
            if 'email' in line.lower() and '@' not in line:
                email_start = i
                break
        
        if email_start is not None:
            # Collect email parts from next few lines (reconstruct scattered email)
            email_chars = []
            found_at = False
            for i in range(email_start + 1, min(email_start + 25, len(lines))):
                line = lines[i].strip()
                line_lower = line.lower()
                
                # Stop if we hit Contact Numbers section
                if 'contact numbers' in line_lower or 'contact number' in line_lower:
                    break
                # Stop at other major sections
                if any(section in line_lower for section in ['mother', 'father', 'guardian', 'details', '---', '0.']):
                    break
                
                # Skip empty lines
                if not line:
                    continue
                
                if '@' in line:
                    found_at = True
                    # Found @ - collect all valid email chars including @
                    # Extract email pattern from this line
                    email_match = re.search(r'([a-zA-Z0-9\s]+@[a-zA-Z0-9\s]+\.[a-zA-Z0-9\s]+)', line, re.IGNORECASE)
                    if email_match:
                        # Try to extract complete email
                        email_candidate = email_match.group(1).replace(' ', '').replace('\n', '').lower()
                        email_candidate = email_candidate.replace('о', 'o').replace('а', 'a')
                        # Clean and validate
                        if '@' in email_candidate:
                            parts = email_candidate.split('@')
                            if len(parts) == 2:
                                local = re.sub(r'[^a-z0-9._+-]', '', parts[0])
                                domain = parts[1]
                                # Extract valid domain.tld
                                domain_match = re.search(r'([a-z0-9.-]+\.(?:com|net|org|edu|in|co\.in))', domain)
                                if domain_match:
                                    domain_clean = domain_match.group(1)
                                    if len(local) > 0 and len(domain_clean) > 3:
                                        result['email'] = f'{local}@{domain_clean}'
                                        break
                    # Also collect chars for reconstruction
                    line_chars = re.findall(r'[a-zA-Z0-9.@]', line)
                    email_chars.extend(line_chars)
                elif found_at:
                    # Collect domain part after @
                    line_chars = re.findall(r'[a-zA-Z0-9.]', line)
                    if line_chars:
                        email_chars.extend(line_chars)
                    # Stop if we hit "contact" or line is too long (not email)
                    if 'contact' in line_lower or (len(line) > 15 and not any(c in line for c in ['.', '@'])):
                        break
                else:
                    # Collect local part before @ (short lines likely email parts)
                    if len(line) <= 10:
                        line_chars = re.findall(r'[a-zA-Z0-9.]', line)
                        if line_chars:
                            email_chars.extend(line_chars)
            
            # Reconstruct email from collected chars if not already found
            if 'email' not in result and email_chars:
                email_str = ''.join(email_chars).lower()
                email_str = email_str.replace('о', 'o').replace('а', 'a')
                # Extract valid email - look for @ and domain
                if '@' in email_str:
                    # Find @ position
                    at_pos = email_str.find('@')
                    local = email_str[:at_pos]
                    local = re.sub(r'[^a-z0-9._+-]', '', local)
                    domain_part = email_str[at_pos+1:]
                    # Extract domain.tld
                    domain_match = re.search(r'([a-z0-9.-]+\.(?:com|net|org|edu|in|co\.in))', domain_part)
                    if domain_match:
                        domain = domain_match.group(1)
                        # Stop at "contact" if present
                        if 'contact' in domain:
                            domain = domain.split('contact')[0]
                        if len(local) > 0 and len(domain) > 3 and '.' in domain:
                            result['email'] = f'{local}@{domain}'
        
        # Fallback: try pattern matching with better cleanup
        if 'email' not in result:
            # Look for email pattern in the text
            email_pattern = r'([a-zA-Z0-9\s]+@[a-zA-Z0-9\s]+\.[a-zA-Z0-9\s]+)'
            email_matches = re.findall(email_pattern, raw_text, re.IGNORECASE)
            if email_matches:
                for email_candidate in email_matches:
                    email = email_candidate.replace(' ', '').replace('\n', '').lower()
                    email = email.replace('о', 'o').replace('а', 'a')
                    # Clean up - extract only valid email part, stop at invalid characters
                    # Find @ symbol
                    if '@' in email:
                        at_pos = email.find('@')
                        # Extract local part (before @)
                        local = email[:at_pos]
                        # Remove invalid characters from local
                        local = re.sub(r'[^a-z0-9._+-]', '', local)
                        # Extract domain part (after @)
                        domain_part = email[at_pos+1:]
                        # Find first valid domain.tld
                        domain_match = re.search(r'([a-z0-9.-]+\.[a-z]{2,})', domain_part)
                        if domain_match:
                            domain = domain_match.group(1)
                            # Stop at "contact" or other invalid words
                            if 'contact' in domain:
                                domain = domain.split('contact')[0]
                            if len(local) > 0 and len(domain) > 3 and '.' in domain:
                                result['email'] = f'{local}@{domain}'
                                break
        
        # Extract scattered phone numbers (look for 10+ digit sequences)
        # Find "Contact Numbers" section
        contact_start = None
        for i, line in enumerate(lines):
            if 'contact numbers' in line.lower() or 'contact number' in line.lower():
                contact_start = i
                break
        
        if contact_start is not None:
            # Collect digits from next few lines
            digits = []
            for i in range(contact_start + 1, min(contact_start + 12, len(lines))):
                line = lines[i].strip()
                # Stop if we hit another section
                if any(section in line.lower() for section in ['mother', 'father', 'guardian', 'details', '---', '0.']):
                    break
                # Extract all digits
                line_digits = re.findall(r'\d+', line)
                digits.extend(line_digits)
            
            # Combine digits and find valid phone numbers
            combined = ''.join(digits)
            # Look for phone number patterns - prefer 10 digit numbers
            # Try to find separate phone numbers first
            phone_numbers = re.findall(r'\d{10}', combined)
            if phone_numbers:
                # Take the first valid 10-digit number
                result['phone_number'] = phone_numbers[0]
            else:
                # Fallback: look for 10-15 digit sequences
                phone_match = re.search(r'(\d{10,15})', combined)
                if phone_match:
                    phone = phone_match.group(1)
                    # If too long, take first 10 digits
                    if len(phone) > 10:
                        phone = phone[:10]
                    result['phone_number'] = phone
        
        # Extract scattered date of birth
        # Look for "Date of Birth" section
        dob_start = None
        for i, line in enumerate(lines):
            if 'date of birth' in line.lower() or ('dob' in line.lower() and 'date' in line.lower()):
                dob_start = i
                break
        
        if dob_start is not None:
            # Date values are AFTER the "Date of Birth" label but before "Permanent Address"
            # Look specifically between "Date of Birth" (line 33) and "Permanent" (line 34)
            # But date values might be on lines 38, 39, 42 (after some other content)
            date_parts = []
            permanent_found = False
            
            for i in range(dob_start + 1, min(dob_start + 15, len(lines))):
                line = lines[i].strip()
                line_lower = line.lower()
                
                # Mark when we hit "Permanent"
                if 'permanent' in line_lower:
                    permanent_found = True
                    continue  # Skip "Permanent" line itself
                
                # Stop if we hit address section (after permanent)
                if permanent_found and 'address' in line_lower:
                    break
                
                # Skip label lines and section headers
                if any(label in line_lower for label in ['dd', 'mm', 'yyyy', 'd d', 'm m', 'y y y y', 'middle name', 'surname', 'first name']):
                    continue
                
                # Skip gender-related lines
                if any(gender_word in line_lower for gender_word in ['male', 'female', 'transgender', 'gender']):
                    continue
                
                # Extract standalone numbers (likely date parts)
                # Look for lines that are JUST numbers
                if line.isdigit():
                    if len(line) == 4 and 1900 <= int(line) <= 2100:
                        # 4-digit year (prefer 2006 over 2025 for DOB)
                        if int(line) < 2010:  # DOB years are typically before 2010 for students
                            date_parts.append(line)
                    elif len(line) <= 2 and int(line) <= 31 and int(line) > 0:
                        # Day or month (1-31)
                        date_parts.append(line)
            
            # Try to construct date (DD/MM/YYYY format)
            if len(date_parts) >= 3:
                # Separate year from day/month
                year = None
                day_month = []
                for part in date_parts:
                    if len(part) == 4 and 1900 <= int(part) <= 2100:
                        year = part
                    else:
                        day_month.append(part)
                
                if year and len(day_month) >= 2:
                    # We have year and at least 2 day/month parts
                    day = day_month[0].zfill(2)
                    month = day_month[1].zfill(2)
                    # Validate - swap if needed
                    if int(day) > 31:
                        day, month = month, day
                    if int(month) > 12:
                        # Month invalid - try swapping
                        if int(day) <= 12:
                            day, month = month, day
                        else:
                            # Both invalid - use first as day, second as month anyway
                            pass
                    result['date_of_birth'] = f'{day}/{month}/{year}'
                elif len(day_month) >= 3:
                    # No 4-digit year, but have 3+ parts - last might be year
                    day = day_month[0].zfill(2)
                    month = day_month[1].zfill(2)
                    year_part = day_month[-1]
                    if len(year_part) == 2:
                        year_int = int(year_part)
                        year = '20' + year_part if year_int < 50 else '19' + year_part
                    elif len(year_part) == 4:
                        year = year_part
                    else:
                        return result  # Invalid year
                    # Validate day/month
                    if int(day) > 31:
                        day, month = month, day
                    if int(month) > 12:
                        month = '01'
                    result['date_of_birth'] = f'{day}/{month}/{year}'
        
        # Extract CUET marks from table
        result.update(self._extract_cuet_marks(raw_text, lines))
        
        # Extract parent names from scattered text
        result.update(self._extract_parent_names(raw_text, lines))
        
        # Extract gender from checked option
        gender_extracted = self._extract_gender(raw_text, lines)
        if gender_extracted:
            result['gender'] = gender_extracted
        
        return result
    
    def _extract_gender(self, raw_text: str, lines: list) -> Optional[str]:
        """Extract gender from checked option"""
        # Find "Gender" section
        gender_start = None
        for i, line in enumerate(lines):
            if 'gender' in line.lower():
                gender_start = i
                break
        
        if gender_start is not None:
            # Look for checked option in next few lines
            # Check lines after "Gender {Tick()}" label
            for i in range(gender_start + 1, min(gender_start + 10, len(lines))):
                line = lines[i].strip()
                line_lower = line.lower()
                
                # Stop if we hit another section
                if any(section in line_lower for section in ['date of birth', 'dob', 'permanent', 'address']):
                    break
                
                # Check for checkmark patterns
                if 'female' in line_lower and ('✓' in line or '√' in line):
                    return 'FEMALE'
                elif 'male' in line_lower and ('✓' in line or '√' in line):
                    return 'MALE'
                elif 'transgender' in line_lower and ('✓' in line or '√' in line):
                    return 'TRANSGENDER'
                
                # Also check if line contains just the gender word
                if line_lower.strip() in ['male', 'female', 'transgender']:
                    # Check same line and next few lines for checkmark
                    check_lines = [line] + lines[i+1:min(i+3, len(lines))]
                    for check_line in check_lines:
                        if '✓' in check_line or '√' in check_line:
                            return line.upper()
                    # No checkmark found - skip (don't guess)
        
        return None
    
    def _extract_parent_names(self, raw_text: str, lines: list) -> Dict[str, Any]:
        """Extract parent names that may be scattered across lines"""
        result = {}
        
        # Extract Father's Name
        father_start = None
        for i, line in enumerate(lines):
            if "father's name" in line.lower() or "father name" in line.lower():
                father_start = i
                break
        
        if father_start is not None:
            name_parts = []
            for i in range(father_start + 1, min(father_start + 6, len(lines))):
                line = lines[i].strip()
                # Stop at next section
                if any(section in line.lower() for section in ['mother', 'guardian', 'details', '0.', 'occupation']):
                    break
                # Collect name parts (all caps words)
                words = re.findall(r'\b[A-Z]{2,}\b', line)
                if words:
                    name_parts.extend(words)
            
            if len(name_parts) >= 2:
                result['father_name'] = ' '.join(name_parts)
        
        # Extract Mother's Name
        mother_start = None
        for i, line in enumerate(lines):
            if "mother's name" in line.lower() or "mother name" in line.lower():
                mother_start = i
                break
        
        if mother_start is not None:
            name_parts = []
            for i in range(mother_start + 1, min(mother_start + 8, len(lines))):
                line = lines[i].strip()
                # Stop at next section
                if any(section in line.lower() for section in ['father', 'guardian', 'details', '0.', 'occupation', 'contact']):
                    break
                # Collect name parts (all caps words, may include numbers like U2M)
                words = re.findall(r'\b[A-Z0-9]{2,}\b', line)
                # Filter out non-name words
                filtered = [w for w in words if w not in ['DD', 'MM', 'YYYY', 'PIN', 'EMAIL', 'CONTACT']]
                if filtered:
                    name_parts.extend(filtered)
            
            if len(name_parts) >= 2:
                # Clean up - remove numbers from middle if present
                cleaned_parts = []
                for part in name_parts:
                    # Remove leading numbers (like U2M -> U M)
                    if part[0].isdigit():
                        continue
                    # Split alphanumeric parts
                    if any(c.isdigit() for c in part) and any(c.isalpha() for c in part):
                        # Split like "U2M" -> ["U", "M"]
                        alpha_parts = re.findall(r'[A-Z]+', part)
                        cleaned_parts.extend(alpha_parts)
                    else:
                        cleaned_parts.append(part)
                
                if len(cleaned_parts) >= 2:
                    # Try to reconstruct proper name (U M HA FI -> UMA HANFI)
                    # Look for common patterns
                    if len(cleaned_parts) == 4 and all(len(p) == 1 for p in cleaned_parts[:2]):
                        # Pattern like "U M HA FI" -> "UMA HANFI"
                        first = cleaned_parts[0] + cleaned_parts[1]  # Combine single letters
                        last = cleaned_parts[2] + cleaned_parts[3] if len(cleaned_parts) > 3 else cleaned_parts[2]
                        result['mother_name'] = f'{first} {last}'
                    else:
                        result['mother_name'] = ' '.join(cleaned_parts)
        
        return result
    
    def _extract_cuet_marks(self, raw_text: str, lines: list) -> Dict[str, Any]:
        """Extract CUET marks from the marks table"""
        result = {}
        
        # Find CUET marks section
        cuet_start = None
        for i, line in enumerate(lines):
            if 'details of marks obtained' in line.lower() or 'cuet' in line.lower():
                cuet_start = i
                break
        
        if cuet_start is not None:
            # Look for subject patterns and scores
            subjects = {
                'cuet_subject_1': ['english', r'\(1\)'],
                'cuet_subject_2': ['accountancy', r'\(11\)'],
                'cuet_subject_3': ['business studies', r'\(1\)\s+business'],
                'cuet_subject_4': ['economics', r'\(IV\)'],
                'cuet_subject_5': ['mathematics', r'\(V\)'],
            }
            
            for i in range(cuet_start, min(cuet_start + 30, len(lines))):
                line = lines[i].upper()
                
                # Extract subject scores
                for field, patterns in subjects.items():
                    subject_name = patterns[0]
                    if subject_name.upper() in line:
                        # Look for score pattern: number with optional decimal
                        score_match = re.search(r'(\d{3,6}\.?\d*)', line)
                        if score_match and field.replace('subject', 'score_obtained') not in result:
                            score_field = field.replace('subject', 'score_obtained')
                            result[score_field] = score_match.group(1)
                            result[field] = subject_name.title()
                
                # Extract total score
                if 'TOTAL CUET SCORE' in line or 'TOTAL CUET SCORE OBTAINED' in line:
                    total_match = re.search(r'(\d{3,6}[\-]?\d*)', line)
                    if total_match:
                        result['cuet_total_score'] = total_match.group(1)
                    # Also check next line for total
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        next_match = re.search(r'(\d{3,6}[\-]?\d*)', next_line)
                        if next_match:
                            result['cuet_total_score'] = next_match.group(1)
        
        # Also extract CUET score from the main "CUET Score" field (not total)
        cuet_score_match = re.search(r'(?:cuet\s+score)[:\s]*\n?\s*(\d{3,4}[\-]\d{3,4})', raw_text, re.IGNORECASE)
        if cuet_score_match and 'cuet_score' not in result:
            result['cuet_score'] = cuet_score_match.group(1)
        
        return result
    
    def _extract_field(self, text: str, text_lower: str, lines: list, 
                      patterns: list, field_name: str) -> Optional[str]:
        """Extract a single field using multiple patterns"""
        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match:
                    # Special handling for gender - extract the actual gender value
                    if field_name == 'gender':
                        # Look for which option is checked
                        match_text = match.group(0)
                        # Check for checkmark patterns (case-insensitive)
                        match_lower = match_text.lower()
                        if 'female' in match_lower and ('✓' in match_text or '√' in match_text or 'check' in match_lower):
                            return 'FEMALE'
                        elif 'male' in match_lower and ('✓' in match_text or '√' in match_text or 'check' in match_lower):
                            return 'MALE'
                        elif 'transgender' in match_lower and ('✓' in match_text or '√' in match_text or 'check' in match_lower):
                            return 'TRANSGENDER'
                        # Fallback: check for gender value in group
                        if match.lastindex >= 1:
                            gender_val = match.group(1).lower()
                            if 'female' in gender_val or gender_val == 'f':
                                return 'FEMALE'
                            elif 'male' in gender_val or gender_val == 'm':
                                return 'MALE'
                            elif 'transgender' in gender_val:
                                return 'TRANSGENDER'
                        # Reject if it's just "TICK()" or similar
                        if 'tick' in match_lower and '()' in match_text:
                            continue
                        continue
                    
                    # Handle multiple groups (e.g., for dates: DD MM YYYY)
                    if match.lastindex and match.lastindex >= 3:
                        # Reconstruct from multiple groups (e.g., date parts)
                        if field_name == 'date_of_birth':
                            day = match.group(1).zfill(2)
                            month = match.group(2).zfill(2)
                            year = match.group(3)
                            if len(year) == 2:
                                year = '20' + year
                            value = f'{day}/{month}/{year}'
                        elif field_name in ['father_name', 'mother_name']:
                            # Combine multiple name parts
                            name_parts = [g for g in match.groups() if g and len(g) > 1]
                            value = ' '.join(name_parts) if name_parts else None
                        else:
                            value = ' '.join(match.groups())
                    elif match.lastindex >= 1:
                        value = match.group(1)
                    else:
                        value = match.group(0)
                    
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
                          'emergency_contact_name', 'first_name', 'middle_name', 'surname']:
            # Clean names - remove extra spaces, handle all caps
            value = re.sub(r'\s+', ' ', value).strip()
            # If all caps, convert to title case; otherwise preserve
            if value.isupper() and len(value.split()) <= 4:
                value = ' '.join(word.capitalize() for word in value.split())
            elif not any(c.islower() for c in value):
                # Mixed case but no lowercase - convert to title
                value = ' '.join(word.capitalize() for word in value.split())
        
        elif field_name in ['city', 'state', 'nationality', 'religion']:
            # Title case for locations
            value = ' '.join(word.capitalize() for word in value.split())
        
        elif field_name == 'email':
            # Remove all spaces and newlines from email
            value = value.replace(' ', '').replace('\n', '').lower().strip()
            # Fix common OCR errors
            value = value.replace('о', 'o').replace('а', 'a')  # Cyrillic to Latin
        
        elif field_name in ['phone_number', 'guardian_phone', 'father_phone', 'mother_phone',
                           'alternate_phone', 'emergency_contact_phone']:
            # Remove all non-digit characters
            value = re.sub(r'[^\d]', '', value)
            # Keep only 10-15 digits
            if len(value) > 15:
                value = value[:15]
            elif len(value) < 10:
                value = ''  # Invalid phone number
        
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
        
        value_lower = value.lower().strip()
        value_upper = value.upper().strip()
        
        # Reject common label patterns
        label_patterns = [
            'signature of', 'signature of student', 'signature of candidate',
            'name in block letters', 'in block letters', 'block letters', 'please', 'tick', 'check', 'enter', 'fill',
            'details', 'information', 'particulars', 'mandatory', 'optional',
            'all informations need', 'academic session', 'admission category'
        ]
        
        for pattern in label_patterns:
            if pattern in value_lower:
                return False
        
        # Reject single uppercase letters or very short labels
        if len(value) <= 3 and value == value_upper:
            if value_lower in ['dob', 'dd', 'mm', 'yyyy', 'pin', 'no', 'yes']:
                return False
        
        if field_name in ['student_name', 'guardian_name', 'father_name', 'mother_name', 
                         'emergency_contact_name', 'first_name', 'middle_name', 'surname']:
            # Name should be 2-50 chars, contain letters
            if not (2 <= len(value) <= 50 and re.search(r'[a-zA-Z]', value)):
                return False
            # Reject if it's clearly a label (all caps short phrases with label words)
            if value == value_upper and len(value.split()) <= 3:
                if any(label in value_lower for label in ['name', 'signature', 'student', 'applicant', 'first', 'middle', 'surname', 'block', 'letters']):
                    return False
            # Reject if value contains "in block letters" or similar label text
            if 'in block letters' in value_lower or 'block letters' in value_lower:
                return False
            # Reject single letters or numbers
            if len(value.split()) == 1 and len(value) <= 2:
                return False
            return True
        
        if field_name in ['city', 'state']:
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
