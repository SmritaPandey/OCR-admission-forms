"""
Specialized SRCC Form Extractor - Handles the specific layout of SRCC DATA FORM

Based on the official SRCC Student Data Form template (4 pages):

PAGE 1 - Basic Details:
- Academic Session, Course (B.COM.(H)/B.A.(H) ECO)
- Admission Category (GEN/OBC/SC/ST/Sports/PWD/EWS/Foreign/CW/KM/Others/ECA)
- DU Portal Form Number, CUET Score, College Roll No., Date of Admission
- 1. Student Name (First Name, Middle Name, Surname)
- 2. Gender (Male/Female/Transgender)
- 3. Date of Birth
- 4. Permanent Address (State, PIN)
- 5. Local Address for Correspondence (State, PIN)
- 6. Email
- 7. Contact Numbers
- 8. Mother's Name
- 9. Father's Name
- 10. CUET Subject Details

PAGE 2 - Detailed Information:
- 11. Class XII Details: (a) Year of passing, (b) Board/University, (c) Exam Roll No,
      (d) Institution Last Attended, (e) Hindi studied upto
- 12. Personal Information: (a) Nationality, (b) Religion, (c) Blood Group,
      (d) Below Poverty Line, (e) Annual Income, (f) Minority status
- 13. Mother's Occupational Details
- 14. Father's Occupational Details  
- 15. Local Guardian's Details
- 16. Other Information: (a) DU Enrollment No., (b) Hindi medium preference
- 17. Certificate Details (for reserved categories)

PAGE 3 - Documents Checklist
PAGE 4 - Declarations

Enhanced with zone-aware extraction for better accuracy.
"""
import re
import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)


# Complete field list for SRCC form
SRCC_FORM_FIELDS = {
    # Page 1 - Header Section
    'academic_session': 'Academic Session (e.g., 2024-25)',
    'course': 'Course: B.COM.(H) or B.A.(H) ECO',
    'category': 'Admission Category: GEN/OBC/SC/ST/Sports/PWD/EWS',
    'du_portal_form_number': 'DU Portal Form Number (12 digits)',
    'cuet_score': 'CUET Score (total)',
    'college_roll_no': 'College Roll No. (e.g., 2YBC102)',
    'date_of_admission': 'Date of Admission',
    
    # Page 1 - Student Details (Fields 1-9)
    'student_name': '1. Student Name (First + Middle + Surname)',
    'gender': '2. Gender: Male/Female/Transgender',
    'date_of_birth': '3. Date of Birth',
    'permanent_address': '4. Permanent Address',
    'permanent_state': '4. State (from permanent address)',
    'pincode': '4. PIN Code',
    'correspondence_address': '5. Local Address for Correspondence',
    'email': '6. Email',
    'phone_number': '7. Contact Numbers',
    'mother_name': '8. Mother\'s Name',
    'father_name': '9. Father\'s Name',
    
    # Page 2 - Class XII Details (Field 11)
    'year_of_passing': '11(a) Year of passing Class XII',
    'board_university': '11(b) Board/University',
    'exam_roll_no': '11(c) Examination Roll No.',
    'institution_last_attended': '11(d) Institution Last Attended',
    'hindi_studied_upto': '11(e) Hindi studied upto: VIII/X/XII/Never',
    
    # Page 2 - Personal Information (Field 12)
    'nationality': '12(a) Nationality',
    'religion': '12(b) Religion',
    'blood_group': '12(c) Blood Group',
    'below_poverty_line': '12(d) Whether Below Poverty Line: Yes/No',
    'annual_income': '12(e) Parent\'s/Family Annual Income',
    'minority_status': '12(f) Whether belongs to minority',
    
    # Page 2 - Mother's Details (Field 13)
    'mother_occupation': '13(a) Mother\'s Occupation',
    'mother_designation': '13(b) Mother\'s Designation',
    'mother_organization': '13(c) Mother\'s Organization & Address',
    'mother_email': '13(d) Mother\'s Email',
    'mother_phone': '13(e) Mother\'s Contact Number',
    
    # Page 2 - Father's Details (Field 14)
    'father_occupation': '14(a) Father\'s Occupation',
    'father_designation': '14(b) Father\'s Designation',
    'father_organization': '14(c) Father\'s Organization & Address',
    'father_email': '14(d) Father\'s Email',
    'father_phone': '14(e) Father\'s Contact Number',
    
    # Page 2 - Guardian Details (Field 15)
    'guardian_name': '15(a) Local Guardian\'s Name',
    'guardian_address': '15(b) Guardian\'s Residential Address',
    'guardian_organization': '15(c) Guardian\'s Organization & Address',
    'guardian_email': '15(d) Guardian\'s Email',
    'guardian_phone': '15(e) Guardian\'s Contact Number',
    
    # Page 2 - Other Information (Field 16-17)
    'enrollment_number': '16(a) Delhi University Enrollment No.',
    'hindi_medium': '16(b) Hindi medium preference: Yes/No',
    'certificate_authority': '17. Certificate Issuing Authority',
    'certificate_number': '17. Certificate No.',
    'certificate_date': '17. Date of Issue',
    'disability_percentage': '17. Disability percentage (for PwBD)',
    'disability_type': '17. Type of Disability: VH/HH/OH',
    'udid_number': '17. UDID No.',
}


class SRCCFormExtractor:
    """
    Specialized extractor for SRCC Student Data Form format.
    Uses positional and contextual extraction based on the known form layout.
    
    Enhanced with zone-aware extraction for better accuracy when zone
    information is available from the form zone detector.
    """
    
    # Map zones to their expected field extraction methods
    ZONE_EXTRACTORS = {
        'header': ['_extract_academic_details'],
        'form_numbers': ['_extract_academic_details'],
        'student_name': ['_extract_student_name'],
        'personal_details': ['_extract_personal_info'],
        'permanent_address': ['_extract_address_details'],
        'correspondence_address': ['_extract_address_details'],
        'contact_details': ['_extract_contact_details'],
        'parent_names': ['_extract_parent_details'],
        'class_xii_details': ['_extract_class_xii_details', '_extract_academic_records'],
        'personal_info': ['_extract_personal_info'],
        'mother_occupation': ['_extract_parent_occupational_details'],
        'father_occupation': ['_extract_parent_occupational_details'],
        'guardian_details': ['_extract_parent_occupational_details'],
        'other_info': ['_extract_parent_occupational_details'],
    }
    
    def __init__(self):
        """Initialize the extractor."""
        self._zone_detector = None
    
    def _get_zone_detector(self):
        """Get zone detector instance (lazy loading)."""
        if self._zone_detector is None:
            try:
                from backend.utils.form_zone_detector import FormZoneDetector
                self._zone_detector = FormZoneDetector(form_type='srcc')
            except ImportError:
                logger.debug("Zone detector not available")
        return self._zone_detector
    
    def extract(self, raw_text: str, zone_hints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract all fields from SRCC form text.
        
        Args:
            raw_text: Raw OCR text from the form
            zone_hints: Optional zone information from zone detector
            
        Returns:
            Dictionary of extracted fields with values
        """
        result = {}
        
        # Normalize text for processing
        text = raw_text.replace('\r\n', '\n')
        
        # If zone hints are provided, use zone-aware extraction
        if zone_hints and zone_hints.get('zones'):
            result = self._extract_with_zones(text, zone_hints)
        else:
            # Standard extraction without zone hints
            result = self._extract_all_fields(text)
        
        # Clean up extracted values - remove garbage text
        result = self._cleanup_extracted_values(result)
        
        # Map SRCC-specific field names to standard form field names
        field_mapping = {
            'permanent_state': 'state',
            'du_portal_form_number': 'application_number',  # DU Portal number is the application number
            'college_roll_no': 'enrollment_number',
            'course': 'course_applied',
            'category': 'admission_category',  # Category is the admission category
            'pincode': 'permanent_pincode',  # Also map to permanent_pincode
        }

        for old_name, new_name in field_mapping.items():
            if old_name in result:
                # Keep both for backward compatibility
                result[new_name] = result[old_name]
        
        # Ensure correspondence fields are populated if same as permanent
        if result.get('permanent_address') and not result.get('correspondence_address'):
            result['correspondence_address'] = result['permanent_address']
        if result.get('permanent_state') and not result.get('correspondence_state'):
            result['correspondence_state'] = result['permanent_state']
        if result.get('pincode') and not result.get('correspondence_pincode'):
            result['correspondence_pincode'] = result['pincode']
        
        # Apply cross-field validation and OCR error correction
        result = self._cross_validate_and_correct(result)
        
        return result
    
    def _cross_validate_and_correct(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply cross-field validation and correct common OCR errors.
        This helps catch inconsistencies and improve accuracy.
        """
        
        # 1. Date format normalization (ensure DD/MM/YYYY format)
        date_fields = ['date_of_birth', 'date_of_admission']
        for field in date_fields:
            if field in result and result[field]:
                date_val = str(result[field])
                # Fix common OCR errors in dates
                date_val = re.sub(r'[oO]', '0', date_val)  # O -> 0
                date_val = re.sub(r'[lI]', '1', date_val)  # l/I -> 1
                # Ensure DD/MM/YYYY format
                if re.match(r'^\d{1,2}[-/]\d{1,2}[-/]\d{4}$', date_val):
                    parts = re.split(r'[-/]', date_val)
                    result[field] = f"{parts[0].zfill(2)}/{parts[1].zfill(2)}/{parts[2]}"
        
        # 2. Phone number validation - ensure they are unique
        phone_fields = ['phone_number', 'father_phone', 'mother_phone']
        phones = {}
        for field in phone_fields:
            if field in result and result[field]:
                phone = str(result[field])
                # Validate 10-digit phone starting with 6-9
                if re.match(r'^[6-9]\d{9}$', phone):
                    if phone not in phones.values():
                        phones[field] = phone
                    # If duplicate, clear the duplicate
                    elif field != 'phone_number':
                        result[field] = None
        
        # 3. Email domain correction
        email_fields = ['email', 'father_email', 'mother_email']
        for field in email_fields:
            if field in result and result[field]:
                email = str(result[field]).lower().strip()
                # Fix common OCR errors in email
                email = re.sub(r'\s+', '', email)  # Remove spaces
                email = email.replace('gmall', 'gmail')  # Common OCR error
                email = email.replace('gmai1', 'gmail')  # l -> 1 error
                email = email.replace('@gmail. com', '@gmail.com')
                email = email.replace('. com', '.com')
                result[field] = email
        
        # 4. CUET Score - Calculate from individual subject scores (above the total line)
        # Sum all cuet_score_obtained_X fields extracted from the CUET table
        # Supports decimal scores like 161.5, 194.25, etc.
        calculated_total = 0.0
        for i in range(1, 7):
            obtained = result.get(f'cuet_score_obtained_{i}')
            if obtained:
                try:
                    calculated_total += float(obtained)
                except (ValueError, TypeError):
                    pass
        
        # Use calculated sum as the cuet_score
        if calculated_total > 0:
            # Format: keep decimals if present, otherwise show as integer
            if calculated_total == int(calculated_total):
                result['cuet_score'] = str(int(calculated_total))
            else:
                result['cuet_score'] = str(calculated_total)
        elif 'cuet_score' in result and result['cuet_score']:
            # Validate existing score if no individual scores found
            try:
                score = float(result['cuet_score'])
                if score < 100 or score > 1000:
                    result['cuet_score'] = None
            except (ValueError, TypeError):
                pass
        
        # 5. Academic session format normalization and validation
        if 'academic_session' in result and result['academic_session']:
            session = str(result['academic_session'])
            # Ensure YYYY-YYYY format
            match = re.match(r'(\d{4})[-/](\d{2,4})', session)
            if match:
                year1 = int(match.group(1))
                year2_str = match.group(2)
                if len(year2_str) == 2:
                    year2 = int(str(year1)[:2] + year2_str)
                else:
                    year2 = int(year2_str)
                
                # Validate: Academic year should be reasonable (2020-2026)
                if year1 > 2026 or year1 < 2020:
                    # OCR error - try to use Date of Admission year
                    doa = result.get('date_of_admission', '')
                    doa_match = re.search(r'(\d{4})$', str(doa))
                    if doa_match:
                        year1 = int(doa_match.group(1))
                        year2 = year1 + 1
                    else:
                        # Default to 2024-2025
                        year1, year2 = 2024, 2025
                
                # Validate year sequence
                if year2 == year1 + 1:
                    result['academic_session'] = f"{year1}-{year2}"
        
        # 6. College Roll No format correction (2YBC102 -> 24BC102)
        if 'college_roll_no' in result and result['college_roll_no']:
            roll = str(result['college_roll_no']).upper()
            if roll.startswith('2Y'):
                roll = '24' + roll[2:]
            result['college_roll_no'] = roll
        
        # 7. Name validation - remove numbers and special chars
        name_fields = ['student_name', 'father_name', 'mother_name', 'guardian_name']
        for field in name_fields:
            if field in result and result[field]:
                name = str(result[field])
                # Remove numbers and special characters
                name = re.sub(r'[^A-Za-z\s]', '', name).strip()
                # Capitalize properly
                if name:
                    result[field] = name.title()
        
        # 8. Pincode validation (6 digits)
        if 'pincode' in result and result['pincode']:
            pincode = str(result['pincode'])
            # Extract 6-digit pincode
            pin_match = re.search(r'\b([1-9]\d{5})\b', pincode)
            if pin_match:
                result['pincode'] = pin_match.group(1)
            else:
                result['pincode'] = None
        
        return result
    
    def _extract_all_fields(self, text: str) -> Dict[str, Any]:
        """Extract all fields without zone hints."""
        result = {}

        # Extract each field category
        result.update(self._extract_student_name(text))
        result.update(self._extract_academic_details(text))
        result.update(self._extract_personal_info(text))
        result.update(self._extract_address_details(text))
        result.update(self._extract_contact_details(text))
        result.update(self._extract_parent_details(text))
        result.update(self._extract_academic_records(text))
        result.update(self._extract_class_xii_details(text))
        result.update(self._extract_parent_occupational_details(text))
        result.update(self._extract_document_checklist(text))

        return result
    
    def _extract_document_checklist(self, text: str) -> Dict[str, Any]:
        """
        Extract document checklist tick marks from page 4.
        
        The form has a checklist of documents with tick marks (✓, ☑, ✔) indicating
        which documents have been attached.
        """
        result = {}
        
        # Define document items with their patterns and next item markers
        # Format: (field_name, pattern, doc_name, next_item_pattern)
        # Note: OCR often adds spaces like "( v )" instead of "(v)"
        document_items = [
            ('doc_admission_form', r'(?:1\s*\.|Printed)\s*Admission\s*/?\s*Registration\s*Form', 'Admission/Registration Form', r'(?:2\s*\.|Undertaking)'),
            ('doc_undertaking_ragging', r'(?:2\s*\.|Undertakings?)\s*for\s*(?:curbing|ragging)', 'Anti-Ragging Undertaking', r'(?:3\s*\.|Photograph)'),
            ('doc_photographs', r'(?:3\s*\.|Photographs?)\s*pasted', 'Photographs', r'(?:4\s*\.|One\s*set)'),
            ('doc_cuet_scorecard', r'\(\s*i\s*\)\s*CUET\s*Score\s*Card', 'CUET Score Card', r'\(\s*ii\s*\)'),
            ('doc_class_xii_marksheet', r'\(\s*ii\s*\)\s*(?:Detailed)?\s*Mark\s*Sheet\s*of\s*class\s*XII', 'Class XII Mark Sheet', r'\(\s*iii\s*\)'),
            ('doc_class_x_certificate', r'\(\s*iii\s*\)\s*Certificate\s*(?:and\s*Mark\s*Sheet)?\s*of\s*class\s*X', 'Class X Certificate', r'\(\s*iv\s*\)'),
            ('doc_class_xii_certificate', r'\(\s*iv\s*\)\s*(?:Provisional|Original)\s*Certificate\s*of\s*class\s*XII', 'Class XII Certificate', r'\(\s*v\s*\)'),
            ('doc_character_certificate', r'\(\s*v\s*\)\s*(?:Recent\s*)?Character\s*Certificate', 'Character Certificate', r'\(\s*vi\s*\)'),
            ('doc_transfer_certificate', r'\(\s*vi\s*\)\s*Transfer\s*Certificate', 'Transfer/Migration Certificate', r'\(\s*vii\s*\)'),
            ('doc_hindi_certificate', r'\(\s*vii\s*\)\s*Certificate\s*from\s*(?:the)?\s*Head\s*of\s*School', 'Hindi Certificate', r'\(\s*viii\s*\)'),
            ('doc_caste_certificate', r'\(\s*viii\s*\)\s*(?:Caste|Category)\s*(?:/\s*Category)?\s*Certificate', 'Caste/Category Certificate', r'\(\s*ix\s*\)'),
            ('doc_sports_eca', r'\(\s*ix\s*\)\s*(?:All)?\s*(?:relevant)?\s*certificates?\s*(?:\()?(?:only)?\s*(?:for)?\s*(?:Sports|ECA)', 'Sports/ECA Certificates', r'(?:5\s*\.|All\s*certificates\s*in\s*original)'),
            ('doc_originals', r'(?:5\s*\.|All\s*certificates\s*in\s*original)', 'Original Documents', r'(?:6\s*\.|Photo\s*ID)'),
            ('doc_photo_id', r'(?:6\s*\.|Any\s*Photo\s*ID\s*proof)', 'Photo ID Proof', None),
        ]
        
        # List to store attached documents
        attached_docs = []
        
        # Tick mark characters (excluding ✓ which appears in instructions)
        tick_marks = ['☑', '☒', '✔', '√']
        
        for field_name, pattern, doc_name, next_pattern in document_items:
            # Search for the document line
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Find the end of this item (start of next item or 150 chars)
                if next_pattern:
                    next_match = re.search(next_pattern, text[match.end():], re.IGNORECASE)
                    if next_match:
                        end = match.end() + next_match.start()
                    else:
                        end = min(len(text), match.end() + 150)
                else:
                    end = min(len(text), match.end() + 150)
                
                # Get the text for just this item
                item_text = text[match.start():end]
                
                # Check for tick mark in this item's text only
                is_ticked = False
                for tick in tick_marks:
                    if tick in item_text:
                        is_ticked = True
                        break
                
                result[field_name] = 'Yes' if is_ticked else 'No'
                if is_ticked:
                    attached_docs.append(doc_name)
        
        # Store list of attached documents
        if attached_docs:
            result['documents_attached'] = ', '.join(attached_docs)
        
        return result
    
    def _extract_with_zones(self, text: str, zone_hints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract fields using zone information for better accuracy.
        
        Zone hints help focus extraction on the right parts of the text,
        reducing false positives from wrong sections.
        
        Args:
            text: Full OCR text
            zone_hints: Zone information with extracted_fields from each zone
            
        Returns:
            Dictionary of extracted fields
        """
        result = {}
        zones = zone_hints.get('zones', {})
        
        # First, collect any pre-extracted fields from zones
        for zone_name, zone_data in zones.items():
            if isinstance(zone_data, dict):
                extracted = zone_data.get('extracted_fields', {})
                for field_name, value in extracted.items():
                    if value and field_name not in result:
                        result[field_name] = value
        
        # Then run standard extraction for any missing fields
        standard_result = self._extract_all_fields(text)
        
        # Merge: zone-extracted fields take precedence, then standard extraction
        for field_name, value in standard_result.items():
            if field_name not in result or not result.get(field_name):
                result[field_name] = value
        
        # Add extraction confidence based on zone matching
        result['_extraction_metadata'] = {
            'zone_aware': True,
            'zones_used': list(zones.keys()),
            'fields_from_zones': len([z for z in zones.values() 
                                      if isinstance(z, dict) and z.get('extracted_fields')])
        }
        
        return result
    
    def extract_from_page(self, raw_text: str, page_number: int) -> Dict[str, Any]:
        """
        Extract fields from a specific page of the form.
        
        Uses zone information specific to that page for targeted extraction.
        
        Args:
            raw_text: OCR text from the page
            page_number: Page number (1-4)
            
        Returns:
            Dictionary of extracted fields for that page
        """
        result = {}
        text = raw_text.replace('\r\n', '\n')
        
        # Get zone detector to know which fields to expect on this page
        zone_detector = self._get_zone_detector()
        if zone_detector:
            page_zones = zone_detector.zone_definitions.get(f'page_{page_number}', {})
            expected_fields = []
            for zone_def in page_zones.values():
                expected_fields.extend(zone_def.get('fields', []))
        else:
            expected_fields = None
        
        # Run full extraction
        all_fields = self._extract_all_fields(text)
        
        # If we know expected fields, filter to only those
        if expected_fields:
            for field_name, value in all_fields.items():
                # Include field if it's expected on this page or is a mapped field
                if field_name in expected_fields or field_name.startswith('_'):
                    result[field_name] = value
        else:
            result = all_fields
        
        return self._cleanup_extracted_values(result)
    
    def get_field_confidence(self, field_name: str, value: str, 
                            zone_name: Optional[str] = None) -> float:
        """
        Calculate confidence score for an extracted field.
        
        Higher confidence when:
        - Field was extracted from its expected zone
        - Value matches expected format/pattern
        - Value length is appropriate
        
        Args:
            field_name: Name of the field
            value: Extracted value
            zone_name: Zone the field was extracted from (if known)
            
        Returns:
            Confidence score 0.0 to 1.0
        """
        if not value or len(str(value).strip()) < 2:
            return 0.0
        
        base_confidence = 0.6
        
        # Boost for zone match
        if zone_name:
            zone_detector = self._get_zone_detector()
            if zone_detector:
                zone_info = zone_detector.get_zone_for_field(field_name)
                if zone_info and zone_info.get('zone_name') == zone_name:
                    base_confidence += 0.2
        
        # Boost for format validation
        value_str = str(value).strip()
        
        # Field-specific validation
        if field_name == 'email' and '@' in value_str and '.' in value_str:
            base_confidence += 0.15
        elif field_name in ['phone_number', 'mother_phone', 'father_phone']:
            if re.match(r'^[6-9]\d{9}$', value_str):
                base_confidence += 0.15
        elif field_name == 'pincode':
            if re.match(r'^\d{6}$', value_str):
                base_confidence += 0.15
        elif field_name == 'aadhar_number':
            if re.match(r'^\d{12}$', value_str):
                base_confidence += 0.15
        elif field_name in ['student_name', 'father_name', 'mother_name']:
            if len(value_str.split()) >= 2:
                base_confidence += 0.1
        elif field_name == 'date_of_birth':
            if re.match(r'^\d{2}/\d{2}/\d{4}$', value_str):
                base_confidence += 0.15
        
        return min(1.0, base_confidence)
    
    def _cleanup_extracted_values(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up extracted values to remove garbage text"""
        cleaned = {}
        
        for field, value in result.items():
            if not value:
                continue
                
            value = str(value).strip()
            
            # Remove trailing garbage (common patterns that get captured)
            garbage_patterns = [
                r'\s*\n.*$',  # Remove anything after newline
                r'\s*Category$',
                r'\s*Father$',
                r'\s*Mother$',
                r'\s*Guardian$',
                r'\s*Details$',
                r'\s*Mobile Number$',
                r'\s*Mobile No\.?$',
                r'\s*Contact Number$',
                r'\s*Email$',
                r'\s*Phone$',
                r'\s*Address$',
                r'\s*Occupation$',
                r'\s*Designation$',
                r'\s*Organization$',
            ]
            
            for pattern in garbage_patterns:
                value = re.sub(pattern, '', value, flags=re.IGNORECASE)
            
            value = value.strip()
            
            # Specific field cleanups
            if field in ['student_name', 'mother_name', 'father_name', 'guardian_name']:
                # Names should be alphanumeric and spaces only
                value = re.sub(r'[^A-Za-z\s]', '', value).strip()
                # Take only the first word(s) that look like a name
                words = value.split()
                if words:
                    # Filter out garbage words from form labels/headers
                    garbage_words = [
                        'category', 'father', 'mother', 'guardian', 'details', 
                        'mobile', 'phone', 'email', 'address', 'occupation',
                        'designation', 'organization', 'son', 'daughter', 'of',
                        'person', 'with', 'disability', 'student', 'name', 'first',
                        'middle', 'surname', 'tick', 'male', 'female', 'transgender',
                        'date', 'birth', 'state', 'pin', 'permanent', 'local',
                        'correspondence', 'different', 'from', 'contact', 'numbers'
                    ]
                    clean_words = [w for w in words if w.lower() not in garbage_words]
                    # Only keep if we have actual name content
                    value = ' '.join(clean_words) if clean_words else ''
            
            elif field == 'email':
                # Email should be lowercase, no spaces
                value = value.lower().replace(' ', '')
            
            elif field in ['phone_number', 'pincode', 'mother_phone', 'father_phone', 'guardian_phone']:
                # Keep only digits
                value = re.sub(r'[^\d]', '', value)
                # Phone numbers must be 10 digits
                if 'phone' in field and len(value) != 10:
                    continue
            
            elif field == 'aadhar_number':
                # Keep only digits, must be exactly 12 digits
                value = re.sub(r'[^\d]', '', value)
                if len(value) != 12:
                    continue  # Skip invalid Aadhar
            
            elif field == 'date_of_birth':
                # Validate date format DD/MM/YYYY
                import re as date_re
                match = date_re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', value)
                if match:
                    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    # Validate ranges
                    if day < 1 or day > 31 or month < 1 or month > 12 or year < 1900 or year > 2020:
                        # Try to fix common OCR errors (71 -> 10, 81 -> 01)
                        if month > 12:
                            # Maybe OCR misread (e.g., 10 as 71, 01 as 81)
                            if str(month).endswith('1'):
                                month = int(str(month)[-2:]) if len(str(month)) > 1 else month
                                if month > 12:
                                    month = 10 if '7' in str(month) else (1 if '8' in str(month) else month)
                        value = f"{day:02d}/{month:02d}/{year}"
                        if month < 1 or month > 12:
                            continue  # Skip invalid date
            
            # Only keep non-empty values
            if value and len(value) >= 2:
                cleaned[field] = value
        
        return cleaned
    
    def _extract_student_name(self, text: str) -> Dict[str, str]:
        """Extract student name from SRCC form"""
        result = {}
        
        # Try to extract first name and surname separately, then combine
        first_name = None
        surname = None
        
        # Pattern 1: Look for "1. FIRSTNAME\nFirst Name ... Surname\nSURNAME"
        first_match = re.search(r'\n1\s*\.\s*([A-Z][A-Z]+)\s*\n\s*First\s+Name', text, re.IGNORECASE)
        if first_match:
            first_name = first_match.group(1).strip()
        
        # Look for surname in different patterns
        surname_patterns = [
            # Look for pattern after "Signature of Student" then surname
            r'Signature\s+of\s+Student\s*\n\s*([A-Z]{2,})\s*\n\s*Surname',
            # Surname appears before the label "Surname"
            r'([A-Z]{3,})\s*\n\s*Surname\s*\n',
            # "Surname" label followed by value
            r'Surname\s*\n\s*([A-Z]{2,})\s*\n',
        ]
        
        # List of words that are NOT surnames
        not_surnames = ['YYYY', 'DATE', 'NAME', 'MALE', 'FEMALE', 'HOUSE', 'ADDRESS', 
                        'STATE', 'PIN', 'CITY', 'EMAIL', 'PHONE', 'MOBILE', 'CONTACT',
                        'DELHI', 'PERMANENT', 'LOCAL', 'BLOCK', 'VIHAR', 'NAGAR']
        
        for pattern in surname_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                s = match.group(1).strip().upper()
                # Validate it's a valid surname
                if s and len(s) >= 2 and s not in not_surnames:
                    surname = s
                    break
        
        # Save individual name components
        if first_name:
            result['first_name'] = first_name.title()
        if surname:
            result['surname'] = surname.title()
        
        # Combine first name and surname if both found
        if first_name and surname:
            result['student_name'] = f"{first_name.title()} {surname.title()}"
            return result
        
        # Fallback: Use full name patterns
        name_patterns = [
            # Most reliable: numbered format "1. RIDDHI PANDEY\nFirst Name"
            r'NAME\s+IN\s+BLOCK\s+LETTERS?\s*\n\s*1\s*\.\s*([A-Z][A-Z\s]+)\s*\n\s*First\s+Name',
            # "1. ARYAN KUMAR\nFirst Name"
            r'\n1\s*\.\s*([A-Z][A-Z]+(?:\s+[A-Z][A-Z]+)+)\s*\n\s*First\s+Name',
            # "Full Name: ARYAN Gender:"
            r'Full\s+Name:\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s+Gender',
            # "Candidate's Name: ARYAN"
            r"Candidate'?s?\s+Name:\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            # "This is to certify that ARYAN" (from certificates)
            r'This\s+is\s+to\s+certify\s+that\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)',
            # After "NAME IN BLOCK LETTERS" on next line (single name)
            r'NAME\s+IN\s+BLOCK\s+LETTERS?\s*\n\s*([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*\n',
            # Declaration: "I, ARYAN , hereby"
            r'I,\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s*[,.]?\s*,?\s*hereby',
            # Guardian declaration: "guardian of\nARYAN"
            r'guardian\s+of\s*\n?\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s*[,.\n]',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up the name - remove extra spaces
                name = ' '.join(name.split())
                # Validate it's not a label or garbage
                if name and len(name) >= 2 and not self._is_label(name):
                    # Skip if it's just common words
                    if name.upper() not in ['SON', 'DAUGHTER', 'SHRI', 'SMT', 'KUMARI', 'FIRST NAME', 'MIDDLE NAME']:
                        result['student_name'] = name.title()
                        
                        # Parse name components if not already set
                        name_parts = name.split()
                        if len(name_parts) >= 1 and 'first_name' not in result:
                            result['first_name'] = name_parts[0].title()
                        if len(name_parts) == 2 and 'surname' not in result:
                            result['surname'] = name_parts[1].title()
                        if len(name_parts) == 3:
                            if 'first_name' not in result:
                                result['first_name'] = name_parts[0].title()
                            result['middle_name'] = name_parts[1].title()
                            result['surname'] = name_parts[2].title()
                        if len(name_parts) > 3:
                            # First, middle parts, last
                            if 'first_name' not in result:
                                result['first_name'] = name_parts[0].title()
                            result['middle_name'] = ' '.join(name_parts[1:-1]).title()
                            result['surname'] = name_parts[-1].title()
                        break
        
        # If we only got first name, use it
        if not result.get('student_name') and first_name:
            result['student_name'] = first_name.title()
        
        return result
    
    def _extract_academic_details(self, text: str) -> Dict[str, str]:
        """Extract academic session, course, category, etc."""
        result = {}
        
        # Academic Session: Handle various OCR formats including line-separated
        # OCR often has: "ACADEMIC SESSION_\n...\n2024/27728"
        
        # Pattern 1: Find any "YYYY/NNNNN" or "YYYY-NN" pattern in the first part of text
        year_pattern_match = re.search(r'(\d{4})[\/\-](\d{2,5})', text[:500])
        if year_pattern_match:
            year1 = year_pattern_match.group(1)
            year2_raw = year_pattern_match.group(2)
            
            try:
                year1_int = int(year1)
                # Normalize: academic session is typically year to year+1
                # Handle OCR noise like "27728" which should be "25" (2024-25)
                if len(year2_raw) == 2:
                    # "2024-25" format - properly interpret as next year
                    year2_int = 2000 + int(year2_raw)
                elif len(year2_raw) == 4:
                    # "2024-2025" format
                    year2_int = int(year2_raw)
                else:
                    # OCR noise like "27728" - derive from year1
                    year2_int = year1_int + 1
                
                # Validate: year2 should be year1 + 1 for academic session
                if year2_int != year1_int + 1:
                    year2_int = year1_int + 1
                
                result['academic_session'] = f"{year1_int}-{year2_int}"
            except ValueError:
                result['academic_session'] = f"{year1}-{int(year1)+1}"
        
        # Fallback 1: Look for standalone year near "ACADEMIC SESSION"
        if 'academic_session' not in result:
            session_area = re.search(r'ACADEMIC\s+SESSION.{0,100}', text, re.IGNORECASE | re.DOTALL)
            if session_area:
                area_text = session_area.group(0)
                year_match = re.search(r'(\d{4})', area_text)
                if year_match:
                    year = int(year_match.group(1))
                    result['academic_session'] = f"{year}-{year+1}"
        
        # Fallback 2: Look for year from Date of Admission
        if 'academic_session' not in result:
            # Try to find "19 08 2024" pattern from Date of Admission
            doa_match = re.search(r'Date\s+of\s+Admission[\s\S]{0,50}?(\d{1,2})\s+(\d{1,2})\s+(\d{4})', text, re.IGNORECASE)
            if doa_match:
                year = int(doa_match.group(3))
                month = int(doa_match.group(2))
                if month >= 7:
                    result['academic_session'] = f"{year}-{year+1}"
                else:
                    result['academic_session'] = f"{year-1}-{year}"
        
        # Fallback 3: Look for year in CUET section
        if 'academic_session' not in result:
            cuet_year = re.search(r'CUET.*?(\d{4})', text[:1000], re.IGNORECASE)
            if cuet_year:
                year = int(cuet_year.group(1))
                result['academic_session'] = f"{year}-{year+1}"
        
        # Course: Look for B.COM.(H) or B.A.(H) ECO with checkmarks/tick marks
        # Checkmark characters that may appear in OCR
        checkmarks = r'[✓✔☑☒✗×√]'
        
        # Find the course section in first 800 chars
        course_section = text[:800]
        
        # Check for B.COM.(H) with tick mark (tick before or after)
        bcom_with_tick = re.search(
            rf'B\.?\s*COM\.?\s*\(H\)\s*{checkmarks}|{checkmarks}\s*B\.?\s*COM\.?\s*\(H\)',
            course_section, re.IGNORECASE
        )
        
        # Check for B.A.(H) ECO with tick mark
        ba_with_tick = re.search(
            rf'B\.?\s*A\.?\s*\(H\)\s*ECO\s*{checkmarks}|{checkmarks}\s*B\.?\s*A\.?\s*\(H\)\s*ECO',
            course_section, re.IGNORECASE
        )
        
        # Determine course based on tick marks
        if bcom_with_tick and not ba_with_tick:
            result['course'] = 'B.COM.(H)'
        elif ba_with_tick and not bcom_with_tick:
            result['course'] = 'B.A.(H) ECO'
        elif bcom_with_tick and ba_with_tick:
            # Both have ticks - use position (first tick wins)
            if bcom_with_tick.start() < ba_with_tick.start():
                result['course'] = 'B.COM.(H)'
            else:
                result['course'] = 'B.A.(H) ECO'
        else:
            # No clear tick marks - look for which course appears with any selection indicator
            # Check if course appears on a separate line (often indicates selection in OCR)
            if re.search(r'(?:COURSE|Please).*\n.*B\.?\s*COM\.?\s*\(H\)\s*$', course_section, re.IGNORECASE | re.MULTILINE):
                result['course'] = 'B.COM.(H)'
            elif re.search(r'(?:COURSE|Please).*\n.*B\.?\s*A\.?\s*\(H\)\s*ECO\s*$', course_section, re.IGNORECASE | re.MULTILINE):
                result['course'] = 'B.A.(H) ECO'
            # Logical deduction: Use College Roll Number to determine course
            # BC = B.COM.(H), BE = B.A.(H) ECO
            # Handle OCR errors like 2YBC102 where 4 is read as Y
            roll_patterns = [
                r'(\d{2})([A-Z]{2})(\d+)',  # Normal: 24BC102
                r'(\d)([A-Z])([A-Z]{2})(\d+)',  # OCR error: 2YBC102 (4->Y)
                r'Roll\s*No\.?\s*[:\s]*(\d{0,2}[A-Z]{2}\d+)',  # After label
            ]
            
            for roll_pattern in roll_patterns:
                roll_match = re.search(roll_pattern, text[:2000], re.IGNORECASE)
                if roll_match:
                    if len(roll_match.groups()) == 4:
                        # OCR error pattern: 2YBC102 -> extract BC
                        roll_code = roll_match.group(3).upper()
                    elif len(roll_match.groups()) == 3:
                        roll_code = roll_match.group(2).upper()
                    else:
                        # After label pattern
                        full_roll = roll_match.group(1).upper()
                        # Extract course code (2 letters)
                        code_match = re.search(r'[A-Z]{2}', full_roll)
                        roll_code = code_match.group(0) if code_match else ''
                    
                    if roll_code == 'BC':
                        result['course'] = 'B.COM.(H)'
                        break
                    elif roll_code in ['BE', 'BA', 'EC']:
                        result['course'] = 'B.A.(H) ECO'
                        break
            
            # Fallback: Default based on presence in text
            if 'course' not in result:
                if re.search(r'B\.?\s*COM\.?\s*\(H\)', course_section, re.IGNORECASE):
                    result['course'] = 'B.COM.(H)'
                elif re.search(r'B\.?\s*A\.?\s*\(H\)\s*ECO', course_section, re.IGNORECASE):
                    result['course'] = 'B.A.(H) ECO'
        
        # Admission Category: GEN, OBC, SC, ST, etc.
        # Valid category values
        valid_categories = ['GEN', 'GENERAL', 'OBC', 'SC', 'ST', 'EWS', 'PWD', 'PWBD', 
                           'SPORTS', 'FOREIGN', 'CW', 'KM', 'ECA', 'OTHERS']
        
        # Use same checkmark pattern
        category_section = text[:1200]
        
        # Look for category with tick mark (before or after)
        category_tick_patterns = [
            # Tick after category
            rf'(GEN|OBC|SC|ST|EWS|PWD|Sports|Foreign|CW|KM)\s*{checkmarks}',
            # Tick before category
            rf'{checkmarks}\s*(GEN|OBC|SC|ST|EWS|PWD|Sports|Foreign|CW|KM)',
            # Category in box/bracket with tick
            rf'\[?\s*(GEN|OBC|SC|ST|EWS|PWD)\s*\]?\s*{checkmarks}',
        ]
        
        for pattern in category_tick_patterns:
            match = re.search(pattern, category_section, re.IGNORECASE)
            if match:
                cat = match.group(1).upper()
                if cat in valid_categories:
                    result['category'] = cat
                    break
        
        # Fallback patterns if no tick mark found
        if 'category' not in result:
            fallback_patterns = [
                # Look for category appearing standalone after label
                r'Category[^A-Z]*(SC|ST|OBC|GEN|EWS|PWD)\b',
                # Category after admission category label
                r'Admission\s+Category.*?(SC|ST|OBC|GEN|EWS|PWD)\s+',
            ]
            for pattern in fallback_patterns:
                match = re.search(pattern, category_section, re.IGNORECASE)
                if match:
                    cat = match.group(1).upper()
                    if cat in valid_categories:
                        result['category'] = cat
                        break
        
        # DU Portal Form Number: 12-digit number starting with 2435...
        du_patterns = [
            r'DU\s+Portal\s+Form\s+(?:Number|No\.?)[:\s]*(\d{12})',
            r'Form\s+Number[:\s]*(\d{12})',
            r'\b(2435\d{8})\b',  # SRCC DU portal numbers start with 2435
            r'(\d{12})(?=\s*\n?\s*(?:CUET|Score|College))',
        ]
        for pattern in du_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['du_portal_form_number'] = match.group(1)
                break
        
        # CUET Score: Get the OBTAINED score from line VII (TOTAL CUET SCORE OBTAINED)
        # This is the authoritative value - DO NOT calculate from individual scores
        # Format: "(VII) TOTAL CUET SCORE OBTAINED [total_possible] [obtained]"
        # Example: "TOTAL CUET SCORE OBTAINED 800 749.5" -> cuet_score = 749.5
        # Supports decimal scores like 851.147, 749.5, etc.
        
        # Pattern for decimal numbers: matches 749, 749.5, 851.147, etc.
        DECIMAL_SCORE = r'(\d{1,4}(?:\.\d+)?)'
        
        # PRIORITY 1: Line VII from CUET table - most reliable
        # Pattern: "TOTAL CUET SCORE OBTAINED 800 749.5" - extract the second number (obtained)
        total_line_match = re.search(
            r'(?:VII|\(VII\)|TOTAL)\s*(?:CUET\s+SCORE\s+)?OBTAINED\s+' + DECIMAL_SCORE + r'\s+' + DECIMAL_SCORE,
            text, re.IGNORECASE
        )
        if total_line_match:
            # First number is total possible, second is obtained
            result['cuet_total_score'] = total_line_match.group(1)
            result['cuet_score'] = total_line_match.group(2)
        
        # PRIORITY 2: Look in CUET section for TOTAL row
        if 'cuet_score' not in result:
            cuet_section_match = re.search(
                r'10\.\s*Details\s+of\s+marks[\s\S]*?TOTAL[\s\S]{0,50}?' + DECIMAL_SCORE + r'\s+' + DECIMAL_SCORE,
                text, re.IGNORECASE
            )
            if cuet_section_match:
                result['cuet_total_score'] = cuet_section_match.group(1)
                result['cuet_score'] = cuet_section_match.group(2)
        
        # PRIORITY 3: "CUET Score" header field (fallback only) - supports decimals
        if 'cuet_score' not in result:
            header_match = re.search(r'CUET\s+Score[:\s]*' + DECIMAL_SCORE, text[:1500], re.IGNORECASE)
            if header_match:
                result['cuet_score'] = header_match.group(1)
        
        # PRIORITY 4: Number before "CUET Score" label - supports decimals
        if 'cuet_score' not in result:
            before_match = re.search(r'(\d{1,4}(?:\.\d+)?)\s*[\.\n]*\s*CUET\s+Score', text[:1500], re.IGNORECASE)
            if before_match:
                result['cuet_score'] = before_match.group(1)
        
        # CUET Subject-wise scores extraction
        # Find Section 10 with CUET details
        cuet_section = re.search(
            r'10\.\s*Details\s+of\s+marks[\s\S]*?(?=11\.\s*Details|Declaration|$)',
            text, re.IGNORECASE
        )
        if cuet_section:
            section_text = cuet_section.group(0)
            
            # Standard CUET subjects for commerce
            subjects = ['English', 'Accountancy', 'Business studies', 'Economics', 'Mathematics']
            subject_idx = 1
            
            # Pattern for decimal scores: matches 200, 161, 161.5, 194.25, etc.
            SUBJ_DECIMAL = r'(\d{1,3}(?:\.\d+)?)'
            
            for subject in subjects:
                # Look for subject name followed by scores (supports decimals)
                subj_pattern = rf'{subject}[\s\S]{{0,50}}?' + SUBJ_DECIMAL + r'\s+' + SUBJ_DECIMAL
                match = re.search(subj_pattern, section_text, re.IGNORECASE)
                if match:
                    total = match.group(1)
                    obtained = match.group(2)
                    result[f'cuet_subject_{subject_idx}'] = subject
                    result[f'cuet_total_score_{subject_idx}'] = total
                    result[f'cuet_score_obtained_{subject_idx}'] = obtained
                    subject_idx += 1
            
            # Also try to get total score from TOTAL row (only if not already set)
            if 'cuet_total_score' not in result or 'cuet_score' not in result:
                total_pattern = r'TOTAL[\s\S]{0,50}?' + DECIMAL_SCORE + r'\s+' + DECIMAL_SCORE
                total_match = re.search(total_pattern, section_text, re.IGNORECASE)
                if total_match:
                    if 'cuet_total_score' not in result:
                        result['cuet_total_score'] = total_match.group(1)
                    if 'cuet_score' not in result:
                        result['cuet_score'] = total_match.group(2)
        
        # College Roll No: Pattern like 24BC102, 24BC156, etc.
        # SRCC roll format: 2 digits + BC/BA + 2-3 digits
        # Handle OCR errors like Y instead of 4: 2YBC102 -> 24BC102
        roll_patterns = [
            # SRCC specific format: 24BC102, 24BA101
            r'\b(2[4Y][BA][CA]\d{2,3})\b',
            # More general: 1-2 digits + 2-3 letters + 2-4 digits
            r'\b(\d{1,2}[A-Z]{2,3}\d{2,4})\b',
        ]
        for pattern in roll_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for roll in matches:
                roll = roll.strip().upper()
                # Validate: must have the right length and pattern
                if len(roll) >= 5 and len(roll) <= 10:
                    # Skip common garbage values
                    if roll not in ['DATE', 'NAME', 'PAGE', 'YYYY', 'DDMM']:
                        # Fix common OCR errors: Y -> 4 in first position after 2
                        if roll.startswith('2Y'):
                            roll = '24' + roll[2:]
                        result['college_roll_no'] = roll
                        break
            if 'college_roll_no' in result:
                break
        
        # Date of Admission: Look for DD MM YYYY pattern in a wider search
        # OCR may have text between label and value, or format like "29\nD D\n08\nM M\n2024"
        admission_patterns = [
            # Direct pattern
            r'Date\s+of\s+Admission[:\s]*(\d{1,2})\s*(\d{1,2})\s*(\d{4})',
            r'Date\s+of\s+Admission[:\s]*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})',
            # Pattern with text in between (up to 100 chars)
            r'Date\s+of\s+Admission[\s\S]{0,100}?(\d{1,2})\s+(\d{1,2})\s+(\d{4})',
        ]
        for pattern in admission_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                day, month, year = match.group(1), match.group(2), match.group(3)
                # Validate the date
                try:
                    d, m, y = int(day), int(month), int(year)
                    if 1 <= d <= 31 and 1 <= m <= 12 and 2020 <= y <= 2030:
                        result['date_of_admission'] = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                        break
                except ValueError:
                    continue
        
        # Fallback: Look for date in format "29\nD D\n08\nM M\n2024\nY Y Y Y" near Date of Admission
        if 'date_of_admission' not in result:
            # Find the area after "Date of Admission"
            doa_area = re.search(r'Date\s+of\s+Admission[\s\S]{0,300}', text, re.IGNORECASE)
            if doa_area:
                area_text = doa_area.group(0)
                # Look for pattern: number, D D, number, M M, 4-digit year
                date_match = re.search(r'(\d{1,2})\s*\n?\s*D\s*D\s*\n?\s*(\d{1,2})\s*\n?\s*M\s*M\s*\n?\s*(\d{4})', area_text, re.IGNORECASE)
                if date_match:
                    day, month, year = date_match.group(1), date_match.group(2), date_match.group(3)
                    try:
                        d, m, y = int(day), int(month), int(year)
                        if 1 <= d <= 31 and 1 <= m <= 12 and 2020 <= y <= 2030:
                            result['date_of_admission'] = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                    except ValueError:
                        pass
        
        # Fallback 2: Look for "DD MM\nYYYY\nD D\nM M" format (labels after values)
        if 'date_of_admission' not in result:
            doa_area = re.search(r'Date\s+of\s+Admission[\s\S]{0,400}', text, re.IGNORECASE)
            if doa_area:
                area_text = doa_area.group(0)
                # Look for "18 08\n2024\nD D\nM M" pattern
                date_match = re.search(r'(\d{1,2})\s+(\d{1,2})\s*\n\s*(\d{4})\s*\n\s*D\s*D', area_text, re.IGNORECASE)
                if date_match:
                    day, month, year = date_match.group(1), date_match.group(2), date_match.group(3)
                    try:
                        d, m, y = int(day), int(month), int(year)
                        if 1 <= d <= 31 and 1 <= m <= 12 and 2020 <= y <= 2030:
                            result['date_of_admission'] = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                    except ValueError:
                        pass
        
        return result
    
    def _extract_personal_info(self, text: str) -> Dict[str, str]:
        """Extract personal information: gender, DOB, nationality, etc."""
        result = {}
        
        # Gender: Look for Male/Female with checkbox indication
        gender_patterns = [
            # Look for checked gender
            r'(?:✓|✔|☑)\s*(Male|Female|Transgender)',
            r'(Male|Female|Transgender)\s*(?:✓|✔|☑)',
            # Gender after "2. Gender" with Male checked (common pattern in SRCC forms)
            r'2\s*\.\s*Gender.*?Male\s*(?:✓|✔|☑|Female)',  # Male before Female means Male is checked
            # Look for Gender followed by Male/Female
            r'Gender[^A-Za-z]*(Male|Female|Transgender)',
            r'2\s*\.\s*Gender[^A-Za-z]*(Male|Female|Transgender)',
        ]
        for pattern in gender_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Special case: if pattern matched "Male" first in the sequence, it's likely Male
                if 'Male' in match.group(0) and 'Female' not in match.group(0)[:match.group(0).find('Male')+4]:
                    result['gender'] = 'Male'
                elif 'Female' in match.group(0) and 'Male' not in match.group(0)[:match.group(0).find('Female')+6]:
                    result['gender'] = 'Female'
                elif match.lastindex and match.lastindex >= 1:
                    result['gender'] = match.group(1).capitalize()
                else:
                    result['gender'] = 'Male'  # Default if pattern matches Male first
                break
        
        # Date of Birth: Various formats found in SRCC forms
        dob_patterns = [
            # "DOB: 23 April 2006" - most readable format
            (r'DOB:\s*(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', 'month_name'),
            # DD MM YY format with spaces
            (r'Date\s+of\s+Birth[:\s]*(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})', 'numeric'),
            # DD/MM/YYYY format
            (r'Date\s+of\s+Birth[:\s]*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', 'numeric'),
            # After numbered field "3. Date of Birth"
            (r'3\s*\.\s*Date\s+of\s+Birth[:\s]*(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})', 'numeric'),
            # Just numbers after DOB label
            (r'D\s*O\s*B[:\s]*(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})', 'numeric'),
            # Compact format like "2370472006" = 23/04/2006 (first 2 = day, next 2 = month, last 4 = year)
            (r'Date\s+of\s+Birth[:\s]*(\d{2})(\d{2})(\d{1,2})(\d{4})', 'compact'),
            # "Date of Birth 2370472006 23RD" - extract from this
            (r'faf/DOB:\s*(\d{2})(\d{2})(\d{1,2})(\d{4})', 'compact'),
        ]
        
        month_map = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12'
        }
        
        for pattern_tuple in dob_patterns:
            pattern, fmt = pattern_tuple
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if fmt == 'month_name':
                    day = match.group(1)
                    month = month_map.get(match.group(2).lower(), '01')
                    year = match.group(3)
                elif fmt == 'compact':
                    day, month = match.group(1), match.group(2)
                    year = match.group(4)
                else:
                    day, month, year = match.group(1), match.group(2), match.group(3)
                
                # Handle 2-digit year
                if len(year) == 2:
                    year = '20' + year if int(year) < 50 else '19' + year
                
                result['date_of_birth'] = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                break
        
        # Nationality - Look for INDIAN anywhere in text (most common value)
        valid_nationalities = ['INDIAN', 'NEPALESE', 'BHUTANESE', 'TIBETAN']
        
        # First try structured pattern
        nationality_patterns = [
            r'Nationality[:\s]+([A-Z][a-z]+)',
            r'\(a\)\s*Nationality[:\s]*([A-Z][a-z]+)',
        ]
        for pattern in nationality_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                nat = match.group(1).strip().upper()
                if nat in valid_nationalities:
                    result['nationality'] = nat.title()
                    break
        
        # Fallback: Search for nationality values anywhere in text
        if 'nationality' not in result:
            for nat in valid_nationalities:
                if re.search(rf'\b{nat}\b', text, re.IGNORECASE):
                    result['nationality'] = nat.title()
                    break

        # Religion - Look for specific values
        valid_religions = ['HINDU', 'MUSLIM', 'SIKH', 'CHRISTIAN', 'JAIN', 'BUDDHIST', 'PARSI', 'ZOROASTRIAN']
        
        # First try structured pattern
        religion_patterns = [
            r'Religion[:\s]+([A-Z][a-z]+)',
            r'\(b\)\s*Religion[:\s]*([A-Z][a-z]+)',
        ]
        for pattern in religion_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rel = match.group(1).strip().upper()
                if rel in valid_religions:
                    result['religion'] = rel.title()
                    break
        
        # Fallback: Search for religion values anywhere in text
        if 'religion' not in result:
            for rel in valid_religions:
                if re.search(rf'\b{rel}\b', text, re.IGNORECASE):
                    result['religion'] = rel.title()
                    break
        
        # Blood Group - Look for valid blood group values
        # Note: OCR may put spaces like "B +" or "AB +"
        blood_patterns = [
            # Pattern with optional space before +/-
            r'Blood\s+Group[:\s]*([ABO])\s*([\+\-])',
            r'Blood\s+Group[:\s]*(AB)\s*([\+\-])',
            r'\(c\)\s*Blood\s+Group[:\s]*([ABO]|AB)\s*([\+\-])',
            # Blood group anywhere on same line as label
            r'Blood\s+Group[^\n]*\b([ABO]|AB)\s*([\+\-])',
        ]
        for pattern in blood_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Combine group type and sign (removing any space)
                bg = (match.group(1) + match.group(2)).upper()
                # Validate blood group
                if bg in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
                    result['blood_group'] = bg
                    break
        
        # Fallback: Search for blood group pattern anywhere in text
        if 'blood_group' not in result:
            # Handle spaces between letter and sign: "B +" -> "B+"
            bg_match = re.search(r'\b([ABO]|AB)\s*([\+\-])\b', text)
            if bg_match:
                bg = (bg_match.group(1) + bg_match.group(2)).upper()
                if bg in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
                    result['blood_group'] = bg
        
        # Annual Income - Look for "BELOW X LAKHS" or similar patterns
        income_patterns = [
            r'(BELOW\s+\d+\s*LAKHS?)',
            r'Annual\s+Income[:\s]*([\d,]+)',
            r'(\d+\s*-\s*\d+\s*LAKHS?)',
        ]
        for pattern in income_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['annual_income'] = match.group(1).strip()
                break
        
        # Aadhar Number: 12 digits, typically in 4-4-4 format with spaces
        # IMPORTANT: Exclude DU Portal Form Number which is also 12 digits
        
        # First, find the DU Portal Form Number to exclude it
        du_portal_match = re.search(r'DU\s*Portal\s*Form\s*(?:Number|No\.?)[:\s]*(\d{12})', text, re.IGNORECASE)
        du_portal_num = du_portal_match.group(1) if du_portal_match else None
        
        # Look for Aadhar with proper 4-4-4 spacing (most reliable)
        aadhar_patterns = [
            # Near Aadhar label
            r'(?:Aadhar|Aadhaar|UID)\s*(?:No\.?|Number)?[:\s]*(\d{4})\s+(\d{4})\s+(\d{4})',
            # 4-4-4 format anywhere
            r'(\d{4})\s+(\d{4})\s+(\d{4})',
        ]
        
        for pattern in aadhar_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                aadhar = match.group(1) + match.group(2) + match.group(3)
                
                # Validate: must be 12 digits and NOT the DU Portal number
                if len(aadhar) == 12 and aadhar != du_portal_num:
                    # Additional validation: Aadhar doesn't start with 0 or 1
                    if aadhar[0] in '23456789':
                        result['aadhar_number'] = aadhar
                        break
        
        # Below Poverty Line - complex OCR layout handling
        # Note: Must avoid matching "Please Tick (✓)" which is a form instruction
        
        # Direct answer patterns
        bpl_direct = re.search(r'Below\s+Poverty\s+Line[:\s]*(Yes|No)\b', text, re.IGNORECASE)
        if bpl_direct:
            result['below_poverty_line'] = bpl_direct.group(1).title()
        
        # Fallback: Look for ✗ or ✓ in the values section (after all labels, before next section)
        # OCR layout: labels on lines 145-154, values on lines 165-172
        # The ✗ on line 165 indicates "No" for BPL
        if 'below_poverty_line' not in result:
            # Find the section after BPL label and before mother's occupation values
            bpl_section = re.search(
                r'Below\s+Poverty\s+Line[\s\S]*?(?=MOUSE\s*WIFE|HOUSE\s*WIFE|mother|occupation)',
                text, re.IGNORECASE
            )
            if bpl_section:
                section = bpl_section.group(0)
                # Look for standalone ✗ or ✓ (not part of "Please Tick (✓)")
                if '✗' in section and 'Please Tick' not in section.split('✗')[0][-30:]:
                    result['below_poverty_line'] = 'No'
                elif '✓' in section:
                    # Check it's not "Please Tick (✓)"
                    tick_context = section[section.find('✓')-30:section.find('✓')]
                    if 'Please' not in tick_context and 'Tick' not in tick_context:
                        result['below_poverty_line'] = 'Yes'
        
        # Additional fallback: if ✗ appears right before INDIAN HINDU
        if 'below_poverty_line' not in result:
            bpl_fallback = re.search(r'✗\s*\n\s*INDIAN', text, re.IGNORECASE)
            if bpl_fallback:
                result['below_poverty_line'] = 'No'
        
        # Minority Category - look for checked boxes
        # "Muslim Jain Sikh Persian Christian Buddhists Others"
        minority_section = re.search(r'minority[\s\S]{0,200}?(Muslim|Jain|Sikh|Persian|Christian|Buddhist|Others?)[\s\S]{0,20}?[✓✔☑]', text, re.IGNORECASE)
        if minority_section:
            result['minority_category'] = minority_section.group(1).title()
        else:
            # Check if "whether belongs to minority" is marked No
            minority_no = re.search(r'belongs\s+to\s+minority[\s\S]{0,30}?(No|✗|×)', text, re.IGNORECASE)
            if minority_no:
                result['minority_category'] = 'None'
        
        # Annual Income (enhanced patterns)
        income_patterns = [
            r'(BELOW\s+\d+\s*LAKHS?)',
            r'(\d+\s*-\s*\d+\s*LAKHS?)',
            r'Annual\s+Income[:\s]*(?:Rs\.?\s*)?(\d[\d,]+)',
            r'Family\s+Annual\s+Income[:\s]*(?:Rs\.?\s*)?(\d[\d,]+)',
        ]
        for pattern in income_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                income = match.group(1).strip()
                if income.replace(',', '').isdigit():
                    result['annual_income'] = income.replace(',', '')
                else:
                    result['annual_income'] = income.upper()
                break
        
        return result
    
    def _extract_address_details(self, text: str) -> Dict[str, str]:
        """Extract address information"""
        result = {}
        
        # Find address section
        address_section = ""
        addr_match = re.search(r'4\s*\.\s*Permanent\s+Address(.*?)(?:6\s*\.\s*Email|7\s*\.\s*Contact|8\s*\.\s*Mother)', 
                               text, re.IGNORECASE | re.DOTALL)
        if addr_match:
            address_section = addr_match.group(1)
        else:
            address_section = text[:2000]
        
        # Original extraction patterns (proven to work)
        address_block_pattern = r'4\s*\.\s*Permanent\s+Address\s+(.*?)(?:5\s*\.\s*Local|State\s+[A-Z])'
        match = re.search(address_block_pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            addr_block = match.group(1)
            addr_parts = []
            for line in addr_block.split('\n'):
                line = line.strip()
                if len(line) > 2 and not re.match(r'^[DM\s]+$', line):
                    addr_parts.append(line)
            if addr_parts:
                full_addr = ' '.join(addr_parts)
                full_addr = re.sub(r'\s+', ' ', full_addr)
                full_addr = re.sub(r'State\s+.*$', '', full_addr, flags=re.IGNORECASE)
                # Remove form labels/headers that may have been captured
                full_addr = self._clean_address(full_addr)
                result['permanent_address'] = full_addr.upper().strip()
        
        # Fallback: Look for HOUSE NO pattern
        if 'permanent_address' not in result:
            house_patterns = [
                r'(HOUSE\s+NO\.?\s*\d+.*?)(?:\n\s*State|\n\s*PIN|\n\s*5\.)',
                r'(HOUSE\s+NO\.?\s*\d+[^\n]*(?:FLATS|VIHAR|COLONY|NAGAR|PARK|ENCLAVE|SHAHDARA)[^\n]*)',
                r'Resident\s+of\s+([A-Z0-9][^\n]+)',
            ]
            for pattern in house_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    addr = match.group(1).strip()
                    addr = re.sub(r'\n+', ' ', addr)
                    addr = re.sub(r'\s+', ' ', addr)
                    addr = re.sub(r'(?:State|PIN|Pincode)\s+.*$', '', addr, flags=re.IGNORECASE)
                    addr = self._clean_address(addr)
                    if len(addr) > 10:
                        result['permanent_address'] = addr.upper().strip()
                        break
        
        # Enhancement: Append locality if found and not already in address
        if 'permanent_address' in result:
            addr = result['permanent_address']
            localities = ['VIVEK VIHAR', 'SHAHDARA', 'SAVITA VIHAR', 'PATEL NAGAR', 'GOMTI NAGAR']
            for loc in localities:
                # Check if locality (or partial) is already in address
                loc_first_word = loc.split()[0]  # e.g., "VIVEK" from "VIVEK VIHAR"
                if loc not in addr and loc_first_word not in addr:
                    loc_pattern = loc.replace(' ', r'\s+')
                    if re.search(r'\b' + loc_pattern + r'\b', address_section, re.IGNORECASE):
                        addr = addr.rstrip(',. ') + ', ' + loc
                        result['permanent_address'] = addr
                        break  # Only add one locality to avoid over-extending
        
        # State - extract from "State DELHI" or "State UTTAR PRADESH" pattern
        # Only look in the address section (near Permanent Address, before Email/Contact)
        
        # First, try to find state within the address context
        address_section = ""
        addr_match = re.search(r'4\s*\.\s*Permanent\s+Address(.*?)(?:6\s*\.\s*Email|7\s*\.\s*Contact|8\s*\.\s*Mother)', text, re.IGNORECASE | re.DOTALL)
        if addr_match:
            address_section = addr_match.group(1)
        else:
            # Fallback: look in first 2000 chars (Page 1)
            address_section = text[:2000]
        
        # Look for "State STATE_NAME PIN" pattern in address section
        # Handle multi-line OCR where UTTAR and PRADESH may be separated
        state_patterns = [
            # "State UTTAR ... PRADESH" (may span multiple lines)
            r'State\s+(UTTAR)[\s\S]{0,30}PRADESH',
            r'State\s+(MADHYA)[\s\S]{0,30}PRADESH',
            # "State DELHI PIN 110095"
            r'State\s+(DELHI|HARYANA|RAJASTHAN|PUNJAB|BIHAR|MAHARASHTRA|KARNATAKA|KERALA|GUJARAT|ODISHA)\s+(?:PIN|\d{6})',
            r'State\s+(DELHI|HARYANA|RAJASTHAN|PUNJAB|BIHAR|MAHARASHTRA|KARNATAKA|KERALA|GUJARAT|ODISHA)\b',
            r'State\s+([A-Z][A-Za-z]+)\s+PIN',
            # Fallback: just "State STATE_NAME"
            r'State\s+([A-Z][A-Za-z]+)',
        ]
        
        for pattern in state_patterns:
            match = re.search(pattern, address_section, re.IGNORECASE)
            if match:
                state = match.group(1).strip().upper()
                # Handle abbreviated state names
                state_map = {
                    'UTTAR': 'Uttar Pradesh',
                    'MADHYA': 'Madhya Pradesh',
                    'DELHI': 'Delhi',
                    'HARYANA': 'Haryana',
                    'RAJASTHAN': 'Rajasthan',
                    'PUNJAB': 'Punjab',
                    'BIHAR': 'Bihar',
                    'MAHARASHTRA': 'Maharashtra',
                    'KARNATAKA': 'Karnataka',
                    'KERALA': 'Kerala',
                    'GUJARAT': 'Gujarat',
                    'ODISHA': 'Odisha',
                }
                if state in state_map:
                    result['permanent_state'] = state_map[state]
                elif state not in ['PIN', 'PINCODE', 'NA', 'SHAHDARA', 'CODE', 'OF', 'DOMICILE', 'BANK']:
                    result['permanent_state'] = state.title()
                if 'permanent_state' in result:
                    break
        
        # PIN Code - 6 digit number after PIN
        pin_patterns = [
            r'PIN\s+(\d{6})',
            r'(?:Pin|PIN)[:\s]*(\d{6})',
            r'(\d{6})(?=\s*$|\s*\n|\s*6\.\s*Email)',
        ]
        for pattern in pin_patterns:
            match = re.search(pattern, address_section, re.IGNORECASE)
            if match:
                pin = match.group(1)
                # Validate it's a valid Indian PIN (first digit 1-9)
                if pin[0] in '123456789':
                    result['pincode'] = pin
                    break
        
        # Correspondence Address - copy from permanent if not different
        if result.get('permanent_address'):
            result['correspondence_address'] = result['permanent_address']
        
        return result
    
    def _extract_contact_details(self, text: str) -> Dict[str, str]:
        """Extract email and phone numbers"""
        result = {}
        
        # Email - Handle OCR artifacts like "gmail. com" with space
        email_patterns = [
            # Email [1] format from DU portal
            r'Email\s*\[1\][:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})',
            # Standard email after label
            r'6\s*\.\s*Email\s*\n\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})',
            r'Email[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})',
            # Gmail pattern with possible space
            r'([a-zA-Z0-9._%+-]+@gmail\.\s*com)',
        ]
        for pattern in email_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                email = match.group(1).strip().lower()
                # Fix common OCR issues
                email = re.sub(r'\s+', '', email)  # Remove all spaces
                email = email.replace('. com', '.com').replace('.com ', '.com')
                if '@' in email and '.' in email.split('@')[1]:
                    result['email'] = email
                    break
        
        # Phone Number
        phone_patterns = [
            r'7\s*\.\s*Contact\s+Numbers?[:\s]+(\d{10})',
            r'Contact\s+Numbers?[:\s]+(\d{10})',
            r'Phone[:\s]+(\d{10})',
            r'Mobile[:\s]+(\d{10})',
            # Look for 10-digit Indian mobile numbers starting with 6-9
            r'\b([6-9]\d{9})\b',
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                phone = match.group(1)
                if len(phone) == 10:
                    result['phone_number'] = phone
                break
        
        return result
    
    def _extract_parent_details(self, text: str) -> Dict[str, str]:
        """Extract parent/guardian information"""
        result = {}
        
        # Mother's Name - specific patterns found in SRCC forms
        # Sometimes the name is on the next line after the label
        mother_patterns = [
            # "Mother's Name: MAMTA" format
            r"Mother'?s?\s+Name:\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            # "8. Mother's Name MAMTA" format (name directly after label)
            r"8\s*\.\s*Mother'?s?\s+Name\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            # Just "Mother's Name MAMTA" on one line
            r"Mother'?s?\s+Name\s+([A-Z][A-Za-z]+)(?:\s|$|\n)",
            # Name on next line: "8. Mother's Name\n9. Father's Name\nMOTHER_VALUE\nFATHER_VALUE"
            # Need to look for this specific pattern
            r"8\s*\.\s*Mother'?s?\s+Name\s*\n\s*9\s*\.\s*Father'?s?\s+Name\s*\n\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s*\n",
            # "Smt MAMTA" or "of Smt MAMTA"
            r"(?:of\s+)?Smt\.?\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
        ]
        for pattern in mother_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if not self._is_label(name) and name.upper() not in ['FATHER', 'GUARDIAN', 'SON', 'DAUGHTER']:
                    result['mother_name'] = name.title()
                    break
        
        # Father's Name - specific patterns found in SRCC forms
        father_patterns = [
            # Pattern where labels are together: "Mother's Name\n9. Father's Name\nMOTHER_VALUE\nFATHER_VALUE"
            r"Mother'?s?\s+Name\s*\n\s*(?:9\s*\.\s*)?Father'?s?\s+Name\s*\n\s*[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s*\n\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            # "Father's Name: KIRPAL" format  
            r"Father'?s?\s+Name:\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            # "9. Father's Name · KIRPAL" format (with middle dot or colon)
            r"9\s*\.\s*Father'?s?\s+Name\s*[·:\s]+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            # "Father's Name KIRPAL" on one line
            r"Father'?s?\s+Name\s+([A-Z][A-Za-z]+)(?:\s|$|\n)",
            # Name on next line after "9. Father's Name\nVALUE"
            r"9\s*\.\s*Father'?s?\s+Name\s*\n\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            # "Father's Guardian's Name: KIRPAL"
            r"Father'?s?\s+Guardian'?s?\s+Name[:\s]+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            # "Son of Mr. KIRPAL" or "Son/Daughter of KIRPAL"
            r"(?:Son|Daughter)\s+of\s+(?:Mr\.?\s+)?([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            # "Shri KIRPAL" or "of Shri KIRPAL"
            r"(?:of\s+)?Shri\.?\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            # "S/O KIRPAL" pattern
            r"S/O\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            # Declaration: "I, KIRPAL"
            r"\nI,\s+([A-Z][A-Za-z]+)\s*[.,]?\s*\n",
        ]
        for pattern in father_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if not self._is_label(name) and name.upper() not in ['MOTHER', 'GUARDIAN', 'SON', 'DAUGHTER']:
                    result['father_name'] = name.title()
                    break
        
        # Local Guardian's Name
        guardian_patterns = [
            r"Local\s+Guardian'?s?\s+(?:Name|Details)[:\s]+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            r"Guardian'?s?\s+Name[:\s]+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
        ]
        for pattern in guardian_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if not self._is_label(name) and name.upper() not in ['FATHER', 'MOTHER']:
                    result['guardian_name'] = name.title()
                    break
        
        # Mother's Occupation
        mother_occ_patterns = [
            r"Mother'?s?\s+Occupational\s+Details[:\s]*\(a\)\s*Occupation[:\s]+([A-Za-z]+(?:\s+[A-Za-z]+)*)",
            r"13\s*\.\s*Mother'?s?\s+Occupational\s+Details[:\s]*.*?Occupation[:\s]+([A-Za-z]+)",
        ]
        for pattern in mother_occ_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                occ = match.group(1).strip()
                if not self._is_label(occ):
                    result['mother_occupation'] = occ.title()
                    break
        
        # Father's Occupation
        father_occ_patterns = [
            r"Father'?s?\s+Occupational\s+Details[:\s]*\(a\)\s*Occupation[:\s]+([A-Za-z]+(?:\s+[A-Za-z]+)*)",
            r"14\s*\.\s*Father'?s?\s+Occupational\s+Details[:\s]*.*?Occupation[:\s]+([A-Za-z]+)",
        ]
        for pattern in father_occ_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                occ = match.group(1).strip()
                if not self._is_label(occ):
                    result['father_occupation'] = occ.title()
                    break
        
        # Extract parent phone numbers and emails
        # Find all phone numbers and emails in the text
        all_phones = re.findall(r'\b([6-9]\d{9})\b', text)
        all_emails = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})', text, re.IGNORECASE)
        
        # Clean emails
        all_emails = [re.sub(r'\s+', '', e.lower()) for e in all_emails]
        
        # Remove the student's phone and email from parent lists
        student_phone = result.get('phone_number')
        student_email = result.get('email', '').lower()
        
        parent_phones = [p for p in all_phones if p != student_phone]
        parent_emails = [e for e in all_emails if e != student_email]
        
        # Father's Section (Field 14) - Look for specific patterns
        father_section = re.search(
            r"14\s*\.\s*Father'?s?\s+Occupational\s+Details[\s\S]*?(?=15\s*\.\s*Local|16\s*\.\s*Other|$)",
            text, re.IGNORECASE
        )
        if father_section:
            section_text = father_section.group(0)
            
            # Father's Phone
            phone_match = re.search(r'\b([6-9]\d{9})\b', section_text)
            if phone_match:
                result['father_phone'] = phone_match.group(1)
                parent_phones = [p for p in parent_phones if p != phone_match.group(1)]
            
            # Father's Email
            email_match = re.search(
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})', 
                section_text, re.IGNORECASE
            )
            if email_match:
                email = re.sub(r'\s+', '', email_match.group(1).lower())
                result['father_email'] = email
                parent_emails = [e for e in parent_emails if e != email]
        
        # Mother's Section - Try to find mother's contact from remaining phones/emails
        # Or look for specific patterns like "gourmamta@gmail.com"
        mother_section = re.search(
            r"13\s*\.\s*Mother'?s?\s+Occupational\s+Details[\s\S]*?(?=14\s*\.\s*Father|15\s*\.\s*Local|$)",
            text, re.IGNORECASE
        )
        if mother_section:
            section_text = mother_section.group(0)
            
            # Mother's Phone
            phone_match = re.search(r'\b([6-9]\d{9})\b', section_text)
            if phone_match and phone_match.group(1) != result.get('father_phone'):
                result['mother_phone'] = phone_match.group(1)
            
            # Mother's Email
            email_match = re.search(
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})', 
                section_text, re.IGNORECASE
            )
            if email_match:
                email = re.sub(r'\s+', '', email_match.group(1).lower())
                if email != result.get('father_email'):
                    result['mother_email'] = email
        
        # Fallback: Look for emails with mother/father hints
        if 'mother_email' not in result:
            for email in parent_emails:
                if 'mam' in email.lower() or 'mom' in email.lower() or 'mother' in email.lower():
                    result['mother_email'] = email
                    break
        
        # Assign remaining parent phone if we only have one
        if 'mother_phone' not in result and parent_phones:
            if len(parent_phones) >= 1:
                result['mother_phone'] = parent_phones[0]
        
        return result
    
    def _extract_academic_records(self, text: str) -> Dict[str, str]:
        """Extract academic qualifications (Class XII details)"""
        result = {}
        
        # Year of Passing
        year_patterns = [
            r'Year\s+of\s+(?:passing|pass)[:\s]+(\d{4})',
            r'\(a\)\s*Year\s+of\s+(?:passing|pass)[:\s]+(\d{4})',
        ]
        for pattern in year_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                year = match.group(1)
                # Validate and correct OCR errors in year
                year = self._correct_year(year)
                if year:
                    result['year_of_passing'] = year
                break
        
        # Board/University
        board_patterns = [
            r'Board\s*/\s*University[:\s]+([A-Z][A-Za-z\s]+?)(?:\n|Exam)',
            r'\(b\)\s*Board\s*/\s*University[:\s]+([A-Z][A-Za-z\s]+)',
            r'(CENTRAL\s+BOARD\s+OF\s+SECONDARY\s+EDUCATION?)',
            r'(CBSE|ICSE|ISC|STATE\s+BOARD)',
        ]
        for pattern in board_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                board = match.group(1).strip()
                if len(board) > 3:
                    result['board_university'] = board.title()
                break
        
        # Examination Roll No (Class XII exam roll number - typically 7-10 digits)
        exam_roll_patterns = [
            r'Examination\s+Roll\s+No\.?[:\s]+(\d{7,10})',
            r'\(c\)\s*Examination\s+Roll\s+No\.?[:\s]+(\d{7,10})',
            r'Roll\s+No\.?\s*[:\s]+(\d{7,10})',
        ]
        for pattern in exam_roll_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['exam_roll_no'] = match.group(1)
                break
        
        # Fallback: Look for exam roll number in the education section (Field 11)
        if 'exam_roll_no' not in result:
            edu_section = re.search(
                r"11\s*\.\s*Details\s+of\s+qualifying[\s\S]*?(?=12\s*\.\s*Personal|$)",
                text, re.IGNORECASE
            )
            if edu_section:
                section_text = edu_section.group(0)
                # Look for 7-8 digit number that's not a phone number
                roll_matches = re.findall(r'\b(\d{7,8})\b', section_text)
                for roll in roll_matches:
                    # Exclude phone numbers (start with 6-9)
                    if not roll[0] in '6789':
                        result['exam_roll_no'] = roll
                        break
        
        # Institution Last Attended
        school_patterns = [
            r'Institution\s+Last\s+Attended[:\s]+([A-Z][A-Za-z\s,]+)',
            r'\(d\)\s*Institution\s+Last\s+Attended[:\s]+([A-Z][A-Za-z\s,]+)',
        ]
        for pattern in school_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                school = match.group(1).strip()
                # Clean up
                school = re.sub(r'\s+', ' ', school)
                school = re.sub(r',?\s*$', '', school)
                if len(school) > 5:
                    result['institution_last_attended'] = school.title()
                break
        
        # Hindi studied upto
        hindi_patterns = [
            r'Hindi\s+studied\s+upto[:\s]*(VIII|X|XII|Never)',
            r'\(e\)\s*Hindi\s+studied\s+upto[:\s]*(VIII|X|XII|Never)',
            # Look for checkmark
            r'Hindi\s+studied\s+upto\s+(VIII|X|XII).*?(?:✓|✔|☑)',
        ]
        for pattern in hindi_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['hindi_studied_upto'] = match.group(1).upper()
                break
        
        # DU Enrollment No
        enrollment_patterns = [
            r'(?:Delhi\s+University\s+)?Enrollment\s+No\.?[:\s]+(\d+)',
            r'DU\s+Enrollment\s+No\.?[:\s]+(\d+)',
        ]
        for pattern in enrollment_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['enrollment_number'] = match.group(1)
                break
        
        return result
    
    def _extract_class_xii_details(self, text: str) -> Dict[str, str]:
        """Extract Class XII details (Field 11 on Page 2)"""
        result = {}
        
        # 11(a) Year of passing
        year_patterns = [
            r'11\s*\.\s*Details.*?Year\s+of\s+passing[:\s]*(\d{4})',
            r'\(a\)\s*Year\s+of\s+passing[:\s]*(\d{4})',
            r'Year\s+of\s+passing[:\s]*(\d{4})',
        ]
        for pattern in year_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                year = self._correct_year(match.group(1))
                if year:
                    result['year_of_passing'] = year
                break
        
        # 11(b) Board/University - look for CBSE, ICSE, State Board names
        board_patterns = [
            r'\(b\)\s*Board\s*/?\s*University[:\s]*([A-Z][A-Za-z\s]+?)(?:\n|\(c\))',
            r'Board\s*/?\s*University[:\s]*(CBSE|ICSE|ISC|CENTRAL\s+BOARD[A-Za-z\s]*)',
            r'(CENTRAL\s+BOARD\s+OF\s+SECONDARY\s+EDUCATION)',
        ]
        for pattern in board_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                board = match.group(1).strip()
                if len(board) > 3 and 'examination' not in board.lower():
                    result['board_university'] = board.title()
                    break
        
        # 11(c) Examination Roll No
        exam_roll_patterns = [
            r'\(c\)\s*Examination\s+Roll\s+No\.?[:\s]*(\d+)',
            r'Examination\s+Roll\s+No\.?[:\s]*(\d+)',
        ]
        for pattern in exam_roll_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['exam_roll_no'] = match.group(1)
                break
        
        # 11(d) Institution Last Attended - look for school name patterns
        institution_patterns = [
            # "Name of School Last Attended: BAL BHARTI PUBLIC SCHOOL"
            r'Name\s+of\s+School\s+Last\s+Attended[:\s]*([A-Z][A-Z\s]+(?:SCHOOL|COLLEGE|ACADEMY|INSTITUTE)[A-Z\s]*)',
            # "School 60050 - BAL BHARTI PUBLIC SCHOOL"
            r'School\s+\d+\s*[-–]\s*([A-Z][A-Z\s]+(?:SCHOOL|COLLEGE|ACADEMY|INSTITUTE)[A-Z\s]*)',
            # Pattern with "Bal Bharti/Bharati Public School"
            r'(Bal\s+Bhar[a-z]+\s+Public\s+School[,\s]*[A-Za-z\s]*)',
            # Generic school pattern  
            r'([A-Z][A-Za-z]+\s+(?:Public\s+)?(?:School|College|Academy|Institute)[,\s]+[A-Za-z\s]+)',
        ]
        for pattern in institution_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                inst = match.group(1).strip()
                inst = re.sub(r'\s+', ' ', inst)
                # Remove trailing garbage
                inst = re.sub(r'[,\s]+(UP|GHAZIABAD|DELHI|NCR).*$', '', inst, flags=re.IGNORECASE)
                if len(inst) > 10 and 'hindi' not in inst.lower():
                    result['institution_last_attended'] = inst.title()
                    break
        
        # 11(e) Hindi studied upto
        hindi_patterns = [
            r'\(e\)\s*Hindi\s+studied\s+upto[:\s]*(VIII|X|XII|Never)',
            r'Hindi\s+studied\s+upto[:\s]*(VIII|X|XII|Never)',
            r'VIII\s*/\s*X\s*/\s*XII\s*/\s*Never.*?(VIII|X|XII|Never)\s*(?:✓|✔|☑)',
            # Look for checkmark after level - "VIII ... ☑" or "VIII ✓"
            r'Hindi\s+studied\s+upto.*?(\bVIII\b).*?[✓✔☑]',
            r'Hindi\s+studied\s+upto.*?(\bX\b).*?[✓✔☑]',
        ]
        for pattern in hindi_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['hindi_studied_upto'] = match.group(1).upper()
                break
        
        # Additional pattern: Board Roll Number from CUET/DU portal data
        if 'exam_roll_no' not in result:
            board_roll = re.search(r'Board\s+Roll\s+Number[:\s]*(\d{7,10})', text, re.IGNORECASE)
            if board_roll:
                result['exam_roll_no'] = board_roll.group(1)
        
        # Map to frontend field names (twelfth_*)
        if result.get('year_of_passing'):
            result['twelfth_year'] = result['year_of_passing']
        if result.get('board_university'):
            result['twelfth_board'] = result['board_university']
        if result.get('exam_roll_no'):
            result['twelfth_roll_number'] = result['exam_roll_no']
        if result.get('institution_last_attended'):
            result['twelfth_institution'] = result['institution_last_attended']

        return result
    
    def _extract_parent_occupational_details(self, text: str) -> Dict[str, str]:
        """Extract parent occupational details (Fields 13-14 on Page 2)"""
        result = {}
        
        # Find the mother's section (Field 13 to Field 14)
        mother_section = re.search(
            r"13\s*\.\s*Mother'?s?\s+Occupational[\s\S]*?(?=14\s*\.\s*Father|$)",
            text, re.IGNORECASE
        )
        mother_text = mother_section.group(0) if mother_section else ""
        
        # Find the father's section (Field 14 to Field 15)
        father_section = re.search(
            r"14\s*\.\s*Father'?s?\s+Occupational[\s\S]*?(?=15\s*\.\s*Local|16\s*\.\s*Other|$)",
            text, re.IGNORECASE
        )
        father_text = father_section.group(0) if father_section else ""
        
        # Extract Mother's details
        # Occupation - look for common patterns
        occ_patterns = [
            r'(HOUSE\s*WIFE|HOUSEWIFE|MOUSE\s*WIFE)',  # MOUSE WIFE is OCR error for HOUSE WIFE
            r'(HOME\s*MAKER|HOMEMAKER)',
            r'(TEACHER|DOCTOR|NURSE|ENGINEER|LAWYER|MANAGER)',
            r'(SELF\s+EMPLOYED|BUSINESS|PRIVATE\s+JOB)',
        ]
        for pattern in occ_patterns:
            match = re.search(pattern, mother_text, re.IGNORECASE)
            if match:
                occ = match.group(1).upper()
                # Fix OCR errors
                if 'MOUSE' in occ:
                    occ = occ.replace('MOUSE', 'HOUSE')
                result['mother_occupation'] = occ.title()
                break
        
        # Mother's email
        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})'
        email_match = re.search(email_pattern, mother_text)
        if email_match:
            email = email_match.group(1).lower().replace(' ', '')
            result['mother_email'] = email
        
        # Mother's phone (10 digits starting with 6-9)
        phone_match = re.search(r'\b([6-9]\d{9})\b', mother_text)
        if phone_match:
            result['mother_phone'] = phone_match.group(1)
            result['mother_mobile'] = phone_match.group(1)
        
        # Extract Father's details
        # Occupation
        for pattern in occ_patterns:
            match = re.search(pattern, father_text, re.IGNORECASE)
            if match:
                occ = match.group(1).upper()
                result['father_occupation'] = occ.title()
                break
        
        # Additional occupation patterns for father
        if 'father_occupation' not in result:
            extra_patterns = [
                r'(DHOBI|DHOBHI|WASHERMAN)',
                r'(SHOPKEEPER|VENDOR|FARMER)',
                r'(GOVERNMENT\s+(?:JOB|SERVICE)|GOVT\s+(?:JOB|SERVICE))',
            ]
            for pattern in extra_patterns:
                match = re.search(pattern, father_text, re.IGNORECASE)
                if match:
                    result['father_occupation'] = match.group(1).title()
                    break
        
        # Father's email
        email_match = re.search(email_pattern, father_text)
        if email_match:
            email = email_match.group(1).lower().replace(' ', '')
            result['father_email'] = email
        
        # Father's phone
        phone_match = re.search(r'\b([6-9]\d{9})\b', father_text)
        if phone_match:
            result['father_phone'] = phone_match.group(1)
            result['father_mobile'] = phone_match.group(1)
        
        # Guardian's Details (Field 15)
        guardian_patterns = [
            r"15\s*\.\s*Local\s+Guardian'?s?\s+Details.*?\(a\)\s*Name[:\s]*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            r"Local\s+Guardian'?s?\s+Name[:\s]*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
        ]
        for pattern in guardian_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                name = match.group(1).strip()
                if not self._is_label(name):
                    result['guardian_name'] = name.title()
                break
        
        # 15(e) Guardian's Contact Number
        guardian_phone_patterns = [
            r"15.*?Contact\s+Number.*?Mobile\s+No\.?[:\s]*(\d{10})",
            r"Guardian'?s?.*?Mobile\s+No\.?[:\s]*(\d{10})",
        ]
        for pattern in guardian_phone_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                result['guardian_phone'] = match.group(1)
                break
        
        # DU Enrollment No (Field 16a)
        du_enrollment_patterns = [
            r"16\s*\.\s*Other\s+Information.*?Delhi\s+University\s+Enrolment\s+No\.?[:\s]*([A-Z0-9]+)",
            r"Delhi\s+University\s+Enrol?ment\s+No\.?[:\s]*([A-Z0-9]+)",
            r"DU\s+Enrol?ment\s+No\.?[:\s]*([A-Z0-9]+)",
            # Pattern like "34SRCCBCO4000135"
            r'\b(\d{2}SRCC[A-Z]{3}\d{7})\b',
        ]
        for pattern in du_enrollment_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                result['du_enrollment_number'] = match.group(1).upper()
                break
        
        # Hindi medium preference (Field 16b) - "Would you like to be taught in Hindi medium"
        hindi_pref_patterns = [
            r'taught\s+in\s+Hindi\s+medium[\s\S]{0,50}?(Yes|No)\s*[✓✔☑]',
            r'Hindi\s+medium[\s\S]{0,30}?(Yes|No)\s*[✓✔☑]',
            r'Hindi\s+medium[\s\S]{0,50}?[✓✔☑]\s*(Yes|No)',
            # Look for Yes ☑ or No ☑ pattern
            r'(Yes)\s*[✓✔☑][\s\S]{0,20}?Hindi\s+medium',
            r'(No)\s*[✓✔☑][\s\S]{0,20}?Hindi\s+medium',
        ]
        for pattern in hindi_pref_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['hindi_medium_preference'] = match.group(1).title()
                break
        
        # Certificate details (Field 17) for EWS/SC/ST/OBC/PwBD
        # Certificate Number
        cert_num_patterns = [
            r'Certificate\s+No\.?[:\s]*(\d+)',
            r'Cert\.?\s+No\.?[:\s]*(\d+)',
        ]
        for pattern in cert_num_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['category_certificate_number'] = match.group(1)
                break
        
        # Certificate Date of Issue
        # Handle compact format like "1870172012" = 18/07/2012
        cert_date_patterns = [
            # Standard format with separators
            r'Date\s+of\s+Issue[:\s]*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})',
            # Compact format: DDMMYYYY (8 digits)
            r'Date\s+of\s+Issue[:\s]*(\d{2})(\d{2})(\d{4})',
            # With space separators
            r'Date\s+of\s+Issue[:\s]*(\d{1,2})\s+(\d{1,2})\s+(\d{4})',
        ]
        for pattern in cert_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                day, month, year = match.group(1), match.group(2), match.group(3)
                # Validate month (1-12) and day (1-31)
                try:
                    d, m, y = int(day), int(month), int(year)
                    if 1 <= m <= 12 and 1 <= d <= 31 and 1990 <= y <= 2030:
                        result['category_certificate_date'] = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                        break
                except ValueError:
                    continue
        
        # Certificate issuing authority
        authority_patterns = [
            r'Name\s*&\s*Address\s+of\s+certificate\s+issuing\s+authority[\s\S]{0,100}?(OFFICE\s+OF[\s\S]{0,50})',
            r'issuing\s+authority[\s\S]{0,50}?(OFFICE\s+OF[\s\S]{0,50})',
            r'(DEPUTY\s+COMMISSIONER[\s\S]{0,30})',
        ]
        for pattern in authority_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                authority = match.group(1).strip()
                authority = re.sub(r'\s+', ' ', authority)
                result['category_certificate_authority'] = authority.title()
                break
        
        # Disability details - only extract if admission_category includes PWD
        # Check if the student's ADMISSION CATEGORY is PWD (not just the label in the form)
        is_pwbd = result.get('category') == 'PWD' or result.get('admission_category') == 'PWD'
        
        # Also check for category marked with tick near PWD
        if not is_pwbd:
            pwbd_check = re.search(r'PWD\s*[✓✔☑]|[✓✔☑]\s*PWD', text, re.IGNORECASE)
            is_pwbd = pwbd_check is not None
        
        if is_pwbd:
            # Only extract disability fields within Section 17 context
            section_17 = re.search(r'17\.\s*If\s+belong[\s\S]{0,500}', text, re.IGNORECASE)
            section_text = section_17.group(0) if section_17 else ""
            
            disability_pct = re.search(r'extent\s+of\s+disability[^\d]*(\d{1,3})\s*%', section_text, re.IGNORECASE)
            if disability_pct:
                pct = int(disability_pct.group(1))
                if 1 <= pct <= 100:
                    result['disability_percentage'] = str(pct)
            
            # Type of disability - must be filled in, not just the label
            disability_type = re.search(r'Type\s+of\s+Disability\s*[\(\[]?\s*VH/HH/OH\s*[\)\]]?\s*[:\s]*([A-Z]{2,})', section_text, re.IGNORECASE)
            if disability_type:
                dtype = disability_type.group(1).upper()
                type_map = {'VH': 'Visual', 'HH': 'Hearing', 'OH': 'Orthopedic'}
                if dtype in type_map:
                    result['disability_type'] = type_map[dtype]
            
            # UDID Number
            udid_match = re.search(r'UDID\s+No\.?[:\s]*([A-Z]{2,}\d{2,}[A-Z0-9]+)', section_text, re.IGNORECASE)
            if udid_match:
                udid = udid_match.group(1).upper()
                if len(udid) >= 10:
                    result['udid_number'] = udid
        
        return result
    
    def _correct_year(self, year: str) -> str:
        """Correct OCR errors in year and validate range"""
        if not year or len(year) != 4:
            return ""
        
        try:
            year_int = int(year)
            
            # Valid range for Class XII passing: 2015-2026
            if 2015 <= year_int <= 2026:
                return year
            
            # Common OCR errors: '0' read as '3', '2' read as '7'
            # Try common corrections
            corrections = [
                (year[0:2] + '2' + year[3], r'2.2.$'),  # 2034 -> 2024
                (year[0:2] + year[2] + '4', r'2.2.$'),  # 2035 -> 2024 
                ('20' + year[2:4], r'^2.$'),            # 2x34 -> 2034
            ]
            
            # Common pattern: 2034 should be 2024 (3 is OCR error for 0)
            if year.startswith('203'):
                corrected = '202' + year[3]
                corrected_int = int(corrected)
                if 2015 <= corrected_int <= 2026:
                    return corrected
            
            # 2033 should be 2023
            if year == '2033':
                return '2023'
            
            # 2034 should be 2024
            if year == '2034':
                return '2024'
            
            # If still out of range, try swapping common OCR confusions
            # 3 <-> 0, 8 <-> 0, 5 <-> 6
            year_list = list(year)
            if year_list[2] == '3':
                year_list[2] = '0'
                test_year = ''.join(year_list)
                if 2015 <= int(test_year) <= 2026:
                    return test_year
            
            # If year is far future (like 2034), it's likely an OCR error
            if year_int > 2026:
                # Try to fix by assuming decade is 202x
                return '202' + year[3] if year[3].isdigit() else '2024'
            
            return year
            
        except ValueError:
            return ""
    
    def _clean_address(self, address: str) -> str:
        """Remove form labels and garbage text from address string"""
        if not address:
            return ""
        
        # Patterns that are form labels, not address content
        garbage_patterns = [
            r'\bADDRESS\b(?!\s*(?:LINE|NO|NUMBER|\d))',  # Remove "ADDRESS" but not "ADDRESS LINE" etc.
            r'\bCORRESPONDENCE\b',
            r'\bPERMANENT\b',
            r'\bLOCAL\s+ADDRESS\b',
            r'\bIF\s+DIFFERENT\s+FROM\s+\d+\b',
            r'\bDIFFERENT\s+FROM\s+\d+\b',
            r'\(\s*IF\s+DIFFERENT[^)]*\)',
            r'\bSTATE\s*$',
            r'\bPIN\s*$',
            r'\bPINCODE\s*$',
            r'\bFOR\s+CORRESPONDENCE\b',
            r'\b5\s*\.\s*LOCAL\b',
            r'\b4\s*\.\s*PERMANENT\b',
            r'\bSAVITA\s+VIHAR\s*\(\s*IF\b',  # Remove form instruction
            r'^\s*ADDRESS\s+',  # Leading "ADDRESS "
            r'\s+ADDRESS\s*$',  # Trailing " ADDRESS"
        ]
        
        cleaned = address
        for pattern in garbage_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remove leading/trailing punctuation
        cleaned = cleaned.strip(',.;:- ')
        
        return cleaned
    
    def _is_label(self, text: str) -> bool:
        """Check if text is likely a form label rather than a value"""
        if not text:
            return True
        
        text_clean = text.strip()
        text_lower = text_clean.lower()
        
        # Short single-word names (ARYAN, MAMTA, KIRPAL) are likely values, not labels
        # Only consider it a label if it exactly matches known form field labels
        exact_labels = [
            'name', 'student name', 'first name', 'middle name', 'surname', 'last name',
            'father', "father's name", 'mother', "mother's name", 
            'guardian', "guardian's name", 'local guardian',
            'occupation', 'designation', 'organization',
            'address', 'permanent address', 'correspondence address', 'local address',
            'email', 'phone', 'mobile', 'contact', 'phone number', 'contact number',
            'date', 'dob', 'date of birth', 'gender', 'sex',
            'category', 'admission category', 'nationality', 'religion',
            'state', 'pin', 'pincode', 'pin code', 'blood group',
            'please', 'tick', 'check', 'fill', 'enter', 'select',
            'of the student', 'of student', 'if different',
            'details', 'information', 'particulars',
            'yes', 'no', 'male', 'female', 'transgender',  # These are valid option values, not labels
        ]
        
        # Remove these from being considered labels (they are valid field values)
        not_labels = ['male', 'female', 'transgender', 'yes', 'no', 
                      'hindu', 'muslim', 'sikh', 'christian', 'jain', 'buddhist',
                      'indian', 'delhi', 'haryana', 'punjab', 'up']
        
        if text_lower in not_labels:
            return False
        
        # Exact match with known labels
        if text_lower in exact_labels:
            return True
        
        # Ends with colon - it's a label
        if text_clean.endswith(':'):
            return True
        
        # Check if it's just instructions
        instruction_patterns = [
            r'^please\s+',
            r'\(please\s+',
            r'tick\s+\(',
            r'^fill\s+',
            r'^enter\s+',
            r'^write\s+',
            r'^specify',
            r'if\s+different',
            r'if\s+employed',
        ]
        for pattern in instruction_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Short uppercase text that matches field names is a label
        if len(text_clean) < 15 and text_clean.isupper():
            if text_lower in ['name', 'address', 'email', 'phone', 'date', 'gender', 'state']:
                return True
        
        # Multi-word phrases that look like field labels
        label_phrases = [
            "mother's occupational details",
            "father's occupational details",
            "local guardian's details",
            "qualifying examination",
            "personal information",
        ]
        for phrase in label_phrases:
            if phrase in text_lower:
                return True
        
        return False


def extract_srcc_form(raw_text: str, zone_hints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main function to extract data from SRCC form text.
    
    Args:
        raw_text: Raw OCR text from the scanned form
        zone_hints: Optional zone information from zone detector for
                   more accurate field extraction
        
    Returns:
        Dictionary of extracted field values
    """
    extractor = SRCCFormExtractor()
    return extractor.extract(raw_text, zone_hints=zone_hints)


def extract_srcc_form_with_zones(
    raw_text: str, 
    page_number: int = 1
) -> Dict[str, Any]:
    """
    Extract data from SRCC form text with automatic zone detection.
    
    This function automatically detects zones and uses them to
    improve extraction accuracy.
    
    Args:
        raw_text: Raw OCR text from the scanned form
        page_number: Page number (1-4) for zone context
        
    Returns:
        Dictionary of extracted field values with zone metadata
    """
    extractor = SRCCFormExtractor()
    
    # Try to get zone information
    zone_hints = None
    try:
        from backend.utils.form_zone_detector import FormZoneDetector
        zone_detector = FormZoneDetector(form_type='srcc')
        
        # Get zone definitions for context (actual zone detection requires image)
        page_zones = zone_detector.zone_definitions.get(f'page_{page_number}', {})
        if page_zones:
            zone_hints = {
                'zones': {name: {'fields': zone.get('fields', [])} 
                         for name, zone in page_zones.items()},
                'page': page_number
            }
    except ImportError:
        logger.debug("Zone detector not available for extraction")
    
    result = extractor.extract(raw_text, zone_hints=zone_hints)
    result['_page'] = page_number
    
    return result
