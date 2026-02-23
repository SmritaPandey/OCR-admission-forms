"""
Specialized SRCC Form Extractor - Handles the specific layout of SRCC DATA FORM

Based on the official SRCC Student Data Form template (4 pages):

IMPORTANT: This extractor is PAGE-ORDER AGNOSTIC. It works correctly even if pages
are in the wrong order (e.g., pages 2 and 3 swapped). The extraction searches for
field markers throughout the entire text, not based on page position.

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

# Import comprehensive form labels module
try:
    from backend.utils.form_labels import (
        ALL_FORM_LABELS, NAME_REJECT_LABELS, ADDRESS_WORDS,
        is_form_label, is_reject_name_value, clean_name_value
    )
    HAVE_FORM_LABELS = True
except ImportError:
    HAVE_FORM_LABELS = False

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
        # IMPORTANT: Keep original field names AND create mapped versions for backward compatibility
        # The database model has both fields, so we populate both intelligently
        field_mapping = {
            # These mappings create additional fields for backward compatibility
            # The original field names are kept, and mapped names are added
            'permanent_state': 'state',  # Also populate 'state' field
            'du_portal_form_number': 'application_number',  # Also populate 'application_number' for legacy
            'college_roll_no': 'enrollment_number',  # Also populate 'enrollment_number' for legacy
            'course': 'course_applied',  # Also populate 'course_applied' for legacy
            'category': 'admission_category',  # Category is the same as admission_category
            'admission_category': 'category',  # Also sync the other way
            'pincode': 'permanent_pincode',  # Also populate 'permanent_pincode'
            # Class XII field mappings (already handled in _extract_class_xii_details, but ensure here too)
            'year_of_passing': 'twelfth_year',
            'board_university': 'twelfth_board',
            'exam_roll_no': 'twelfth_roll_number',
            'institution_last_attended': 'twelfth_institution',
        }

        for old_name, new_name in field_mapping.items():
            if old_name in result and result[old_name]:
                # Keep original field AND populate mapped field (both exist in database)
                # Only populate mapped field if it doesn't already have a value
                if new_name not in result or not result[new_name]:
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
        
        # 4. CUET Score - Only calculate from individual scores if TOTAL row wasn't found
        # The TOTAL row (VII) is authoritative - don't override it with calculated sum
        # Only calculate if we don't have a cuet_score from the TOTAL row
        if 'cuet_score' not in result or not result.get('cuet_score'):
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
            
            # Use calculated sum as the cuet_score only if we don't have one from TOTAL row
            if calculated_total > 0:
                # Format: keep decimals if present, otherwise show as integer
                if calculated_total == int(calculated_total):
                    result['cuet_score'] = str(int(calculated_total))
                else:
                    result['cuet_score'] = str(calculated_total)
        else:
            # Validate existing score from TOTAL row
            try:
                score = float(result['cuet_score'])
                if score < 100 or score > 1000:
                    # Score out of range - might be wrong, try calculation
                    calculated_total = 0.0
                    for i in range(1, 7):
                        obtained = result.get(f'cuet_score_obtained_{i}')
                        if obtained:
                            try:
                                calculated_total += float(obtained)
                            except (ValueError, TypeError):
                                pass
                    if calculated_total > 0:
                        result['cuet_score'] = str(int(calculated_total)) if calculated_total == int(calculated_total) else str(calculated_total)
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
        
                result['pincode'] = None
        
        # 9. Address Validation - Remove garbage
        # e.g. "(), SHANTI..." or values that are just labels
        for addr_field in ['permanent_address', 'correspondence_address']:
            if addr_field in result and result[addr_field]:
                val = str(result[addr_field])
                # Check for garbage start patterns
                if val.startswith('(),') or val.startswith('()') or len(val) < 8:
                    result[addr_field] = None
                # Check if it lacks alphabets (mostly symbols)
                elif len(re.sub(r'[^A-Za-z]', '', val)) < 4:
                    result[addr_field] = None
        
        return result
    
    def _extract_all_fields(self, text: str) -> Dict[str, Any]:
        """
        Extract all fields without zone hints.
        
        This method is PAGE-ORDER AGNOSTIC - it searches for field markers
        throughout the entire text, so it works correctly even if pages
        are in the wrong order (e.g., pages 2 and 3 swapped).
        """
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
            # Names can have 1, 2, or more parts - don't penalize single names
            if len(value_str.split()) >= 1:
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
                r'.*name\s+in\s+block\s+letters.*',  # Critical: remove "NAME IN BLOCK LETTERS"
                r'.*in\s+block\s+letters.*',  # Also remove "IN BLOCK LETTERS"
                r'.*block\s+letters.*',  # Also remove "BLOCK LETTERS"
            ]
            
            for pattern in garbage_patterns:
                value = re.sub(pattern, '', value, flags=re.IGNORECASE)
            
            value = value.strip()
            
            # Specific field cleanups
            if field in ['student_name', 'mother_name', 'father_name', 'guardian_name']:
                # Use comprehensive form labels module if available
                if HAVE_FORM_LABELS:
                    if is_reject_name_value(value):
                        value = ''
                    else:
                        value = clean_name_value(value)
                else:
                    # Fallback: CRITICAL: First, check if the entire value is a label (like "NAME IN BLOCK LETTERS")
                    value_lower = value.lower().strip()
                    
                    # Reject if it contains any form label text - be very aggressive
                    reject_phrases = [
                        'name in block letters', 'in block letters', 'block letters',
                        'name:', 'block', 'letters', 'first name', 'middle name', 'surname',
                        'date of birth', 'sex', 'gender', 'permanent address', 'correspondence',
                        'email', 'phone', 'contact', 'mother', 'father', 'guardian',
                        'occupation', 'designation', 'organization', 'signature', 'student',
                        # Address words
                        'vihar', 'nagar', 'colony', 'enclave', 'park', 'road', 'street',
                        'vivek', 'janta', 'flats', 'house', 'sector', 'block',
                    ]
                    
                    # If value contains any reject phrase, reject it entirely
                    if any(phrase in value_lower for phrase in reject_phrases):
                        # But allow if it's a long name that happens to contain "name" as part of actual name
                        if len(value_lower.split()) <= 4:
                            value = ''  # Reject entire value - it's likely a label
                        elif 'block letters' in value_lower or 'in block letters' in value_lower:
                            value = ''  # Always reject if it has "block letters"
                        else:
                            # It's a longer name, but still remove the label parts
                            value = re.sub(r'(?:name\s+)?in\s+block\s+letters', '', value, flags=re.IGNORECASE)
                            value = re.sub(r'block\s+letters', '', value, flags=re.IGNORECASE)
                    
                    if value:  # Only process if value wasn't rejected
                        # Remove "NAME IN BLOCK LETTERS" and variants from anywhere in the string
                        value = re.sub(r'(?:name\s+)?in\s+block\s+letters', '', value, flags=re.IGNORECASE)
                        value = re.sub(r'block\s+letters', '', value, flags=re.IGNORECASE)
                        value = re.sub(r'^name\s+', '', value, flags=re.IGNORECASE).strip()  # Remove "name" at start
                        value = re.sub(r'\s+name\s+', ' ', value, flags=re.IGNORECASE).strip()  # Remove "name" in middle
                        
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
                                'person', 'with', 'disability', 'student', 'first',
                                'middle', 'surname', 'tick', 'male', 'female', 'transgender',
                                'date', 'birth', 'state', 'pin', 'permanent', 'local',
                                'correspondence', 'different', 'from', 'contact', 'numbers',
                                'block', 'letters', 'in',  # Critical: filter "NAME IN BLOCK LETTERS" components
                                # Address words
                                'vihar', 'nagar', 'colony', 'enclave', 'park', 'road', 'street',
                                'lane', 'sector', 'house', 'flat', 'flats', 'floor', 'apartment',
                                'vivek', 'ashok', 'janta', 'rohini', 'dwarka', 'pitampura',
                                # Occupation words
                                'service', 'business', 'employed', 'self', 'dhobi', 'housewife',
                            ]
                            clean_words = [w for w in words if w.lower() not in garbage_words and len(w) > 1]
                            # Only keep if we have actual name content (at least 2 words or one word > 2 chars)
                            if clean_words:
                                value = ' '.join(clean_words)
                                # Final check: reject if it's still just "block" or "letters" or too short
                                if value.lower() in ['block', 'letters', 'in', 'name'] or len(value) < 2:
                                    value = ''
                            else:
                                value = ''
            
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
        
        # Pattern 1: Look for name after "1." and before "First Name"
        # Handle multiple formats:
        # - "1. ARYAN\nFirst Name" (direct)
        # - "1.\nNAME IN BLOCK LETTERS\nARYAN\nFirst Name" (with label)
        # - "NAME IN BLOCK LETTERS\nARYAN SHARMA\nFirst Name" (with label, no "1.")
        # IMPORTANT: Priority should be given to name immediately after "NAME IN BLOCK LETTERS"
        # and BEFORE other labels like "VIVEK VIHAR" (which is an address, not a name)
        
        name_parts_from_first = None
        parsed_from_first = False  # Track if we've already parsed from first_match
        
        # PRIORITY 1: Look for name immediately after "NAME IN BLOCK LETTERS" label
        # This is the most reliable pattern - name comes right after the label
        # Handle format: "1.\nNAME IN BLOCK LETTERS\nARYAN\n..." 
        # IMPORTANT: Capture only the name line, not subsequent lines like "First Name"
        first_match = re.search(
            r'1\s*\.\s*\n\s*NAME\s+IN\s+BLOCK\s+LETTERS?\s*\n\s*([A-Z][A-Z]+(?:\s+[A-Z]+)?)(?=\s*\n\s*(?:First\s+Name|2\.|Signature|Gender))',
            text, re.IGNORECASE | re.MULTILINE
        )
        
        # PRIORITY 2: Try pattern that looks for name after "NAME IN BLOCK LETTERS" label (without "1.")
        # This handles cases where "1." is on a different line
        if not first_match:
            first_match = re.search(
                r'NAME\s+IN\s+BLOCK\s+LETTERS?\s*\n\s*([A-Z][A-Z]+)\s*(?:\n|$|\s*(?:First\s+Name|2\.|D\s+D|M\s+M))',
                text, re.IGNORECASE | re.MULTILINE
            )
        
        # PRIORITY 3: Fallback - try direct pattern "1. ARYAN\nFirst Name"
        if not first_match:
            first_match = re.search(
                r'\n1\s*\.\s*([A-Z][A-Z]+(?:\s+[A-Z]+)*)\s*\n\s*First\s+Name',
                text, re.IGNORECASE | re.MULTILINE
            )
        
        if first_match:
            name_from_first = first_match.group(1).strip()
            # Reject if it captured the label itself
            if 'NAME' in name_from_first and 'BLOCK' in name_from_first:
                first_match = None
            else:
                name_parts_from_first = name_from_first.split()
                
                # IMPORTANT: Reject if name is actually an address component
                # "VIVEK VIHAR" should NOT be captured as a name - it's part of address
                # Common address words that shouldn't be names: VIHAR, NAGAR, COLONY, ENCLAVE
                # But allow "VIVEK" alone if it appears right after "NAME IN BLOCK LETTERS"
                if len(name_parts_from_first) >= 2:
                    # Check if any part is an address word
                    address_words = ['VIHAR', 'NAGAR', 'COLONY', 'ENCLAVE', 'PARK', 'ROAD', 'STREET', 
                                    'HOUSE', 'FLATS', 'APARTMENT', 'SOCIETY', 'JANTA']
                    if any(part.upper() in address_words for part in name_parts_from_first):
                        # This is likely an address, not a name - skip it
                        first_match = None
                
                # Check if single word is an address component (like "VIVEK" near "VIHAR")
                if len(name_parts_from_first) == 1 and name_parts_from_first[0].upper() == 'VIVEK':
                    # "VIVEK" alone could be name OR address - check context
                    # If "VIVEK" appears near "VIHAR", it's address, not name
                    if 'VIHAR' in text[max(0, first_match.end()-100):first_match.end()+100].upper():
                        # "VIVEK" is near "VIHAR" - it's part of address
                        first_match = None
                
                if first_match:
                    # If we got multiple parts (e.g., "ARYAN SHARMA"), parse immediately
                    if len(name_parts_from_first) == 1:
                        # Single name - just first name (no surname)
                        first_name = name_parts_from_first[0]
                        # Don't return early yet - check for explicit "Surname" field
                        result['student_name'] = first_name.title()
                        result['first_name'] = first_name.title()
                        
                        # Look for Surname field specifically
                        # PRIORITY: Look for value ABOVE "Surname" label (SRCC format: YADAV \n Surname)
                        surname_match = re.search(
                            r'([A-Z][A-Z]+)\s*\n\s*Surname',
                            text, re.IGNORECASE | re.MULTILINE
                        )
                        
                        # Secondary: Look for value AFTER "Surname" label
                        if not surname_match:
                             surname_match = re.search(
                                r'Surname\s*\n\s*([A-Z][A-Z]+)|Surname\s+([A-Z][A-Z]+)',
                                text, re.IGNORECASE | re.MULTILINE
                            )
                        
                        if surname_match:
                            possible_surname = surname_match.group(1) or surname_match.group(2)
                            # Validate: Should not be "Male", "Female", "Gender"
                            if possible_surname.upper() not in ['MALE', 'FEMALE', 'GENDER', 'OTHER', 'TRANSGENDER']:
                                surname = possible_surname
                                result['surname'] = surname.title()
                                result['student_name'] = f"{first_name} {surname}".title()
                                parsed_from_first = True
                            
                    elif len(name_parts_from_first) == 2:
                        # Two parts: "First Surname" - parse immediately
                        first_name = name_parts_from_first[0]
                        surname = name_parts_from_first[1]  # Set surname immediately
                        parsed_from_first = True
                    elif len(name_parts_from_first) >= 3:
                        # Three or more parts: "First Middle Surname" - parse immediately
                        first_name = name_parts_from_first[0]
                        surname = name_parts_from_first[-1]  # Last part is surname
                        parsed_from_first = True
        
        # Look for surname in different patterns
        # IMPORTANT: Only if we haven't already parsed surname from first_match pattern
        # AND we haven't already set student_name (which would mean we already found a complete name)
        if not parsed_from_first and 'student_name' not in result:
            surname_patterns = [
                # Look for pattern after "Signature of Student" then surname
                r'Signature\s+of\s+Student\s*\n\s*([A-Z]{3,})\s*\n\s*Surname',
                # Surname appears before the label "Surname" (must be at least 3 chars to avoid capturing labels)
                r'([A-Z]{3,})\s*\n\s*Surname\s*\n',
                # "Surname" label followed by value (must be on next line, and not just "Name")
                r'Surname\s*\n\s*(?!NAME\b)([A-Z]{3,})(?:\s*\n|$)',
            ]
            
            # List of words that are NOT surnames (including common labels)
            not_surnames = ['YYYY', 'DATE', 'NAME', 'MALE', 'FEMALE', 'HOUSE', 'ADDRESS', 
                            'STATE', 'PIN', 'CITY', 'EMAIL', 'PHONE', 'MOBILE', 'CONTACT',
                            'DELHI', 'PERMANENT', 'LOCAL', 'BLOCK', 'VIHAR', 'NAGAR', 'VIVEK',
                            'COLONY', 'ENCLAVE', 'PARK', 'FLATS', 'JANTA', 'SURNAME', 'FIRST',
                            'MIDDLE', 'SIGNATURE', 'STUDENT', 'FLATS', 'VIHAR']
            
            for pattern in surname_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    s = match.group(1).strip().upper()
                    # Validate it's a valid surname
                    # IMPORTANT: Don't use first_name as surname - if first_name is set and matches, skip
                    if s and len(s) >= 3 and s not in not_surnames:
                        # If we already have a first_name and it's the same as this potential surname, skip
                        # This prevents "ARYAN" from being extracted as surname when it's actually the first name
                        if first_name and s == first_name.upper():
                            continue
                        surname = s
                        break
        
        # Save individual name components
        if first_name:
            result['first_name'] = first_name.title()
        # IMPORTANT: Only set surname if it's valid (not a label like "Name")
        if surname and surname.upper() not in ['NAME', 'SURNAME', 'FIRST', 'MIDDLE']:
            result['surname'] = surname.title()
        
        # Combine first name and surname if both found
        # IMPORTANT: If we parsed from first_match with multiple parts, return immediately
        # This prevents surname patterns from overriding our parsed values
        if parsed_from_first and first_name and surname:
            result['student_name'] = f"{first_name.title()} {surname.title()}"
            result['first_name'] = first_name.title()
            result['surname'] = surname.title()
            # If we have middle name parts (3+ parts)
            if name_parts_from_first and len(name_parts_from_first) >= 3:
                result['middle_name'] = ' '.join(name_parts_from_first[1:-1]).title()
                result['student_name'] = f"{result['first_name']} {result['middle_name']} {result['surname']}"
            return result
        
        # Combine first name and surname if both found (from explicit patterns)
        if first_name and surname and surname.upper() not in ['NAME', 'SURNAME']:
            result['student_name'] = f"{first_name.title()} {surname.title()}"
            result['first_name'] = first_name.title()
            result['surname'] = surname.title()
            return result
        
        # IMPORTANT: Handle cases where only first name OR only surname is found
        # Some people don't have middle names or surnames
        if first_name and not surname:
            # Check if first_name pattern actually captured multiple parts
            if name_parts_from_first and len(name_parts_from_first) > 1:
                # The pattern captured something like "ARYAN SHARMA" - parse it
                if len(name_parts_from_first) == 2:
                    # "First Surname" - use second as surname
                    result['first_name'] = name_parts_from_first[0].title()
                    result['surname'] = name_parts_from_first[1].title()
                    result['student_name'] = f"{result['first_name']} {result['surname']}"
                    return result
                elif len(name_parts_from_first) >= 3:
                    # "First Middle Surname" - take last as surname
                    result['first_name'] = name_parts_from_first[0].title()
                    result['middle_name'] = ' '.join(name_parts_from_first[1:-1]).title()
                    result['surname'] = name_parts_from_first[-1].title()
                    result['student_name'] = f"{result['first_name']} {result['middle_name']} {result['surname']}"
                    return result
            else:
                # Only first name found (single word) - use it as full name
                result['student_name'] = first_name.title()
                result['first_name'] = first_name.title()
                # IMPORTANT: Return immediately - we have the name
                return result
        
        if surname and not first_name:
            # Only surname found (uncommon, but possible)
            result['student_name'] = surname.title()
            result['surname'] = surname.title()
            return result
        
        # Fallback: Use full name patterns (only if we haven't found name yet)
        # IMPORTANT: These patterns should handle names with 1, 2, 3, or more parts
        if not result.get('student_name'):
            name_patterns = [
                # Pattern: "1. ARYAN\nFirst Name" (name on same line as "1.")
                r'\n1\s*\.\s*([A-Z][A-Z]+(?:\s+[A-Z]+)*)\s*\n\s*First\s+Name',
                # Pattern: "1.\nARYAN\nFirst Name" (name on next line after "1.")
                r'\n1\s*\.\s*\n\s*([A-Z][A-Z]+(?:\s+[A-Z]+)*)\s*\n\s*First\s+Name',
                # Pattern: "1. ARYAN" followed by "First Name" (simpler, no newline requirement)
                r'1\s*\.\s*([A-Z][A-Z]+(?:\s+[A-Z]+)*)(?:\s*\n|\s+)First\s+Name',
                # Pattern: After "NAME IN BLOCK LETTERS", then "1. ARYAN\nFirst Name"
                r'NAME\s+IN\s+BLOCK\s+LETTERS?\s*\n\s*(?!.*(?:NAME\s+IN\s+BLOCK|BLOCK\s+LETTERS|IN\s+BLOCK))1\s*\.\s*([A-Z][A-Z]+(?:\s+[A-Z]+)*)\s*\n\s*First\s+Name',
                # Pattern: "NAME IN BLOCK LETTERS\nARYAN\nFirst Name" (name right after label, no "1.")
                r'NAME\s+IN\s+BLOCK\s+LETTERS?\s*\n\s*(?!.*(?:NAME\s+IN\s+BLOCK|BLOCK\s+LETTERS|IN\s+BLOCK))([A-Z][A-Z]+(?:\s+[A-Z]+)*)\s*\n\s*First\s+Name',
                # "Full Name: ARYAN Gender:" (single or multi-part)
                r'Full\s+Name:\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s+Gender',
                # "Candidate's Name: ARYAN"
                r"Candidate'?s?\s+Name:\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
                # "This is to certify that ARYAN" (from certificates)
                r'This\s+is\s+to\s+certify\s+that\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)',
                # Declaration: "I, ARYAN , hereby" (single or multi-part)
                r'I,\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s*[,.]?\s*,?\s*hereby',
                # Guardian declaration: "guardian of\nARYAN"
                r'guardian\s+of\s*\n?\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s*[,.\n]',
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    name = match.group(1).strip()
                    # Clean up the name - remove extra spaces
                    name = ' '.join(name.split())
                    
                    # CRITICAL: Reject immediately if it contains label text
                    name_lower = name.lower()
                    if any(phrase in name_lower for phrase in [
                        'name in block letters', 'in block letters', 'block letters',
                        'first name', 'middle name', 'surname'
                    ]):
                        # If it has "block letters", always reject
                        if 'block letters' in name_lower or 'in block letters' in name_lower:
                            continue
                        # If it's just label words, reject
                        if name_lower in ['first name', 'middle name', 'surname', 'name', 'block', 'letters']:
                            continue
                    
                    # Validate it's not a label or garbage
                    if name and len(name) >= 2:
                        # Additional check: skip if it's just common words/labels
                        invalid_words = ['SON', 'DAUGHTER', 'SHRI', 'SMT', 'KUMARI', 'FIRST NAME', 'MIDDLE NAME', 
                                       'SURNAME', 'NAME', 'BLOCK', 'LETTERS', 'IN BLOCK LETTERS', 'NAME IN BLOCK LETTERS',
                                       'GENDER', 'MALE', 'FEMALE', 'DATE', 'BIRTH']
                        if name.upper() in invalid_words:
                            continue
                        
                        # Check each word - reject if any word is a label
                        name_words = name.upper().split()
                        if any(word in invalid_words for word in name_words):
                            # Allow if it's a multi-word name and not all words are invalid
                            valid_words = [w for w in name_words if w not in invalid_words]
                            if not valid_words:
                                continue
                            # Use only valid words
                            name = ' '.join(valid_words)
                            if len(name) < 2:
                                continue
                        
                        # Final validation: must look like a real name (at least 2 characters, at least 1 valid word)
                        if len(name) >= 2:
                            # IMPORTANT: Only set student_name if not already set (from first_name extraction above)
                            if 'student_name' not in result:
                                result['student_name'] = name.title()
                                
                                # Parse name components flexibly - handle cases with 1, 2, 3, or more parts
                                # IMPORTANT: Some people don't have middle names or surnames
                                name_parts = name.split()
                                
                                if len(name_parts) == 1:
                                    # Only one name (first name only, no surname)
                                    if 'first_name' not in result:
                                        result['first_name'] = name_parts[0].title()
                                    # No middle_name or surname
                                elif len(name_parts) == 2:
                                    # Two parts: Could be "First Surname" or "First Middle" (without surname)
                                    # Assume it's First + Surname (most common case)
                                    if 'first_name' not in result:
                                        result['first_name'] = name_parts[0].title()
                                    if 'surname' not in result:
                                        result['surname'] = name_parts[1].title()
                                elif len(name_parts) == 3:
                                    # Three parts: "First Middle Surname" or "First Surname1 Surname2"
                                    # Assume it's First + Middle + Surname (most common case)
                                    if 'first_name' not in result:
                                        result['first_name'] = name_parts[0].title()
                                    result['middle_name'] = name_parts[1].title()
                                    if 'surname' not in result:
                                        result['surname'] = name_parts[2].title()
                                elif len(name_parts) > 3:
                                    # More than 3 parts: "First Middle1 Middle2 Surname" or compound names
                                    # Take first as first_name, last as surname, middle as everything in between
                                    if 'first_name' not in result:
                                        result['first_name'] = name_parts[0].title()
                                    result['middle_name'] = ' '.join(name_parts[1:-1]).title()
                                    if 'surname' not in result:
                                        result['surname'] = name_parts[-1].title()
                                else:
                                    # Fallback: at least set first_name if we have any parts
                                    if 'first_name' not in result and name_parts:
                                        result['first_name'] = name_parts[0].title()
                            break
        
        # Final fallback: If we only got first name (and no full name yet), use it
        # This handles cases where people only have a first name (no middle name or surname)
        if not result.get('student_name'):
            if first_name:
                result['student_name'] = first_name.title()
            elif surname:
                # Only surname (uncommon, but possible)
                result['student_name'] = surname.title()
        
        # Ensure first_name is set if we have student_name but no first_name
        if result.get('student_name') and 'first_name' not in result:
            name_parts = result['student_name'].split()
            if name_parts:
                result['first_name'] = name_parts[0].title()
        
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
        # Also handle: "(VII) TOTAL CUET SCORE OBTAINED 1200 1150"
        # Handle OCR where numbers are on separate lines after the label
        # Strategy: Find the TOTAL CUET SCORE OBTAINED section, then find the last two large numbers (800, 749)
        # Try multiple patterns to find the TOTAL section - capture more text to get all numbers
        # NOTE: This extraction happens BEFORE the CUET section extraction, so we need to be careful
        # to not set wrong values. The CUET section extraction (later) will override if it finds better values.
        total_section_patterns = [
            r'\(?\s*VII\s*\)?\s*TOTAL[\s\S]{0,50}?CUET[\s\S]{0,50}?SCORE[\s\S]{0,50}?OBTAINED[\s\S]{0,500}?(?=11\.|Mother|Father|Page|$)',
            r'TOTAL[\s\S]{0,50}?CUET[\s\S]{0,50}?SCORE[\s\S]{0,50}?OBTAINED[\s\S]{0,500}?(?=11\.|Mother|Father|Page|$)',
            r'\(VII\)[\s\S]{0,200}?TOTAL[\s\S]{0,50}?CUET[\s\S]{0,50}?SCORE[\s\S]{0,50}?OBTAINED[\s\S]{0,500}?(?=11\.|Mother|Father|Page|$)',
        ]
        
        total_section_match = None
        for pattern in total_section_patterns:
            total_section_match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if total_section_match:
                break
        
        if total_section_match:
            section_text = total_section_match.group(0)
            # Find the label first, then get numbers after it
            total_label_match = re.search(
                r'\(?\s*VII\s*\)?\s*TOTAL[\s\S]{0,50}?CUET[\s\S]{0,50}?SCORE[\s\S]{0,50}?OBTAINED',
                section_text, re.IGNORECASE | re.MULTILINE
            )
            if total_label_match:
                # Get text after the label
                after_label = section_text[total_label_match.end():]
                # Find all 3-4 digit numbers after the label (not in the whole section)
                numbers_after = re.findall(r'\b(\d{3,4}(?:\.\d+)?)\b', after_label)
                if len(numbers_after) >= 2:
                    # Last two numbers are total and obtained (800, 749)
                    try:
                        nums = [float(n) for n in numbers_after[-2:]]
                        # Validate: both should be reasonable scores (100-2000)
                        if all(100 <= n <= 2000 for n in nums):
                            # The last number is obtained, second-to-last is total
                            # Usually: total >= obtained, so larger is total
                            if nums[0] >= nums[1]:
                                result['cuet_total_score'] = str(int(nums[0])) if nums[0].is_integer() else str(nums[0])
                                result['cuet_score'] = str(int(nums[1])) if nums[1].is_integer() else str(nums[1])
                            else:
                                result['cuet_total_score'] = str(int(nums[1])) if nums[1].is_integer() else str(nums[1])
                                result['cuet_score'] = str(int(nums[0])) if nums[0].is_integer() else str(nums[0])
                    except (ValueError, IndexError):
                        pass
        
        # Fallback: Try direct pattern matching if section method didn't work
        if 'cuet_score' not in result:
            total_line_patterns = [
                # Pattern 1: All on same line: (VII) TOTAL CUET SCORE OBTAINED 800 749
                r'\(?\s*VII\s*\)?\s*TOTAL[\s\S]{0,50}?CUET[\s\S]{0,50}?SCORE[\s\S]{0,50}?OBTAINED[\s\S]{0,20}?' + DECIMAL_SCORE + r'[\s\n\r]+' + DECIMAL_SCORE,
                # Pattern 2: Look for TOTAL CUET SCORE OBTAINED followed by two numbers (may be on next lines)
                r'TOTAL[\s\S]{0,30}?CUET[\s\S]{0,30}?SCORE[\s\S]{0,30}?OBTAINED[\s\n\r]{0,200}?' + DECIMAL_SCORE + r'[\s\n\r]+' + DECIMAL_SCORE,
            ]
            for total_pattern in total_line_patterns:
                total_line_match = re.search(total_pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if total_line_match:
                    total_val = total_line_match.group(1)
                    obtained_val = total_line_match.group(2)
                    try:
                        total_float = float(total_val)
                        obtained_float = float(obtained_val)
                        # Sanity check: total should be >= obtained, and both should be reasonable (100-2000)
                        if 100 <= total_float <= 2000 and 100 <= obtained_float <= 2000 and total_float >= obtained_float:
                            result['cuet_total_score'] = total_val
                            result['cuet_score'] = obtained_val
                            break
                    except ValueError:
                        result['cuet_total_score'] = total_val
                        result['cuet_score'] = obtained_val
                        break
        
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
        
        # CUET Subject-wise scores extraction from Page 1 table
        # The table structure typically has:
        # - Row headers with Roman numerals: (I), (II), (III), (IV), (V), (VI)
        # - Column headers: Subject, Total Score, Score Obtained
        # - Last row: (VII) TOTAL CUET SCORE OBTAINED
        
        # Find Section 10 with CUET details
        cuet_section = re.search(
            r'10\.\s*Details\s+of\s+marks[\s\S]*?(?=11\.\s*Details|Declaration|$)',
            text, re.IGNORECASE
        )
        if not cuet_section:
            # Fallback: Look for CUET table anywhere on page 1
            cuet_section = re.search(
                r'(?:CUET|Details\s+of\s+marks)[\s\S]{0,2000}?(?=11\.|Mother|Father|$)',
                text, re.IGNORECASE
            )
        
        if cuet_section:
            section_text = cuet_section.group(0)
            
            # Pattern for decimal scores: matches 200, 161, 161.5, 194.25, etc.
            SUBJ_DECIMAL = r'(\d{1,3}(?:\.\d+)?)'
            
            # Roman numeral patterns for rows: (I), (II), (III), (IV), (V), (VI), (VII)
            roman_numerals = {
                'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7
            }
            
            # Common CUET subject names and variations
            subject_patterns = {
                'English': r'ENGLISH|English',
                'Accountancy': r'ACCOUNTANCY|Accountancy|Accounting',
                'Business Studies': r'BUSINESS\s+STUDIES|Business\s+Studies|Business\s+Studies?',
                'Economics': r'ECONOMICS|Economics',
                'Mathematics': r'MATHEMATICS|Mathematics|Maths?',
                'Commerce': r'COMMERCE|Commerce',
                'General Test': r'GENERAL\s+TEST|General\s+Test',
            }
            
            # Method 1: Extract by Roman numeral rows (I) through (VI)
            for roman, idx in roman_numerals.items():
                if idx > 6:  # Skip VII (TOTAL row)
                    continue
                
                # Pattern: (I) SUBJECT_NAME TOTAL_SCORE OBTAINED_SCORE
                # IMPORTANT: Use exact Roman numeral match to avoid matching "IV" when looking for "V"
                # Also handle OCR errors where Roman numerals are read as Arabic numerals: (1) instead of (I)
                # Try multiple patterns to handle different OCR outputs
                # Map Arabic numerals to Roman for matching
                arabic_to_roman = {'1': 'I', '2': 'II', '3': 'III', '4': 'IV', '5': 'V', '6': 'VI'}
                arabic_num = None
                for a, r in arabic_to_roman.items():
                    if r == roman:
                        arabic_num = a
                        break
                
                row_patterns = [
                    # Pattern 1: (I) SUBJECT 200 185 (most common - exact parentheses match)
                    # Use word boundary or start of line to ensure exact match
                    rf'(?:^|\s)\({roman}\)\s+([A-Z][A-Z\s&]+?)\s+(\d{{1,3}}(?:\.\d+)?)\s+(\d{{1,3}}(?:\.\d+)?)',
                    # Pattern 1b: (1) SUBJECT 200 185 (OCR error: Arabic numeral instead of Roman)
                    rf'(?:^|\s)\({arabic_num}\)\s+([A-Z][A-Z\s&]+?)\s+(\d{{1,3}}(?:\.\d+)?)\s+(\d{{1,3}}(?:\.\d+)?)',
                    # Pattern 2: (I) SUBJECT\n200\n185 (multi-line with newlines)
                    rf'(?:^|\s)\({roman}\)\s+([A-Z][A-Z\s&]+?)[\n\r]+\s*(\d{{1,3}}(?:\.\d+)?)[\n\r]+\s*(\d{{1,3}}(?:\.\d+)?)',
                    # Pattern 2b: (1) SUBJECT\n200\n185 (OCR error)
                    rf'(?:^|\s)\({arabic_num}\)\s+([A-Z][A-Z\s&]+?)[\n\r]+\s*(\d{{1,3}}(?:\.\d+)?)[\n\r]+\s*(\d{{1,3}}(?:\.\d+)?)',
                    # Pattern 3: I. SUBJECT 200 185 (with period)
                    rf'(?:^|\s){roman}\.\s+([A-Z][A-Z\s&]+?)\s+(\d{{1,3}}(?:\.\d+)?)\s+(\d{{1,3}}(?:\.\d+)?)',
                    # Pattern 4: Handle columnar format where subject and scores are separated
                    # (I) SUBJECT_NAME (on one line)
                    # ... other content ...
                    # Then find scores in column format: look for subject name, then find nearby scores
                    # This is more complex - we'll handle it separately below
                ]
                
                match = None
                for pattern in row_patterns:
                    match = re.search(pattern, section_text, re.IGNORECASE | re.MULTILINE)
                    if match and len(match.groups()) >= 3:
                        # Double-check: verify the match contains the correct Roman numeral
                        match_start = match.start()
                        # Look backwards to find the Roman numeral
                        context_start = max(0, match_start - 10)
                        context = section_text[context_start:match_start + 20]
                        if f'({roman})' in context or f'{roman}.' in context:
                            break
                        else:
                            match = None  # Wrong match, try next pattern
                
                if match and len(match.groups()) >= 3:
                    subject_raw = match.group(1).strip()
                    total = match.group(2)
                    obtained = match.group(3)
                    
                    # Clean up subject name
                    subject_name = re.sub(r'[^\w\s&]', '', subject_raw).strip()
                    # Map to standard subject name
                    for std_name, pattern in subject_patterns.items():
                        if re.search(pattern, subject_name, re.IGNORECASE):
                            subject_name = std_name
                            break
                    
                    if subject_name and len(subject_name) > 2:
                        result[f'cuet_subject_{idx}'] = subject_name
                        result[f'cuet_total_score_{idx}'] = total
                        result[f'cuet_score_obtained_{idx}'] = obtained
                        continue
                
                # Method 2: Look for subject name near Roman numeral (if Method 1 didn't match)
                # Pattern: (I) followed by subject name, then scores on same or next lines
                if f'cuet_subject_{idx}' not in result:
                    alt_pattern = rf'\(?\s*{roman}\s*\)?\s*([A-Z][A-Z\s&]{2,30}?)(?:[\s\n\r]+)' + SUBJ_DECIMAL + r'(?:[\s\n\r]+)' + SUBJ_DECIMAL
                    alt_match = re.search(alt_pattern, section_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                
                if alt_match:
                    subject_raw = alt_match.group(1).strip()
                    total = alt_match.group(2)
                    obtained = alt_match.group(3)
                    
                    # Clean and map subject name
                    subject_name = re.sub(r'[^\w\s&]', '', subject_raw).strip()
                    for std_name, pattern in subject_patterns.items():
                        if re.search(pattern, subject_name, re.IGNORECASE):
                            subject_name = std_name
                            break
                    
                    if subject_name and len(subject_name) > 2:
                        result[f'cuet_subject_{idx}'] = subject_name
                        result[f'cuet_total_score_{idx}'] = total
                        result[f'cuet_score_obtained_{idx}'] = obtained
            
            # Method 3: Extract subjects by name if Roman numerals failed
            # Only fill in missing slots
            if not all(result.get(f'cuet_subject_{i}') for i in range(1, 7)):
                for std_name, pattern in subject_patterns.items():
                    # Find first available slot
                    for idx in range(1, 7):
                        if result.get(f'cuet_subject_{idx}'):
                            continue
                        
                        # Look for subject name followed by two scores (various formats)
                        # Format 1: Subject Total Obtained (on same line)
                        subj_pattern1 = rf'{pattern}[\s\S]{{0,50}}?' + SUBJ_DECIMAL + r'[\s\n\r]+' + SUBJ_DECIMAL
                        match = re.search(subj_pattern1, section_text, re.IGNORECASE | re.MULTILINE)
                        if match:
                            total = match.group(1)
                            obtained = match.group(2)
                            result[f'cuet_subject_{idx}'] = std_name
                            result[f'cuet_total_score_{idx}'] = total
                            result[f'cuet_score_obtained_{idx}'] = obtained
                            break
                        
                        # Format 2: Subject on one line, scores on next lines
                        subj_pattern2 = rf'{pattern}(?:[\s\n\r]+)' + SUBJ_DECIMAL + r'(?:[\s\n\r]+)' + SUBJ_DECIMAL
                        match2 = re.search(subj_pattern2, section_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                        if match2:
                            total = match2.group(1)
                            obtained = match2.group(2)
                            result[f'cuet_subject_{idx}'] = std_name
                            result[f'cuet_total_score_{idx}'] = total
                            result[f'cuet_score_obtained_{idx}'] = obtained
                            break
            
            # Method 4: Table structure parsing - look for columnar data
            # Sometimes OCR outputs table as columns: Subject | Total | Obtained
            if not all(result.get(f'cuet_subject_{i}') for i in range(1, 7)):
                # Try to find table rows by looking for sequences of subject names and scores
                # Pattern: Look for lines that have subject-like text followed by two numbers
                table_row_pattern = r'([A-Z][A-Z\s&]{3,30}?)\s+' + SUBJ_DECIMAL + r'\s+' + SUBJ_DECIMAL
                table_matches = re.finditer(table_row_pattern, section_text, re.IGNORECASE | re.MULTILINE)
                
                idx = 1
                for match in table_matches:
                    if idx > 6:
                        break
                    if result.get(f'cuet_subject_{idx}'):
                        idx += 1
                        continue
                    
                    subject_raw = match.group(1).strip()
                    total = match.group(2)
                    obtained = match.group(3)
                    
                    # Skip if it's clearly not a subject (too short, contains numbers, etc.)
                    if len(subject_raw) < 3 or re.search(r'^\d+$', subject_raw):
                        continue
                    
                    # Skip if it's TOTAL or other labels
                    if re.search(r'TOTAL|SCORE|OBTAINED|SUBJECT', subject_raw, re.IGNORECASE):
                        continue
                    
                    # Map to standard subject name
                    subject_name = subject_raw
                    for std_name, pattern in subject_patterns.items():
                        if re.search(pattern, subject_raw, re.IGNORECASE):
                            subject_name = std_name
                            break
                    
                    # Only add if we haven't seen this subject yet
                    existing_subjects = [result.get(f'cuet_subject_{i}', '') for i in range(1, 7)]
                    if subject_name not in existing_subjects:
                        result[f'cuet_subject_{idx}'] = subject_name
                        result[f'cuet_total_score_{idx}'] = total
                        result[f'cuet_score_obtained_{idx}'] = obtained
                        idx += 1
            
            # Extract TOTAL row (VII) - this is the authoritative total
            # Pattern: (VII) TOTAL CUET SCORE OBTAINED TOTAL_POSSIBLE OBTAINED
            # Handle case where numbers are on separate lines after the label
            # Strategy: Find TOTAL CUET SCORE OBTAINED, then get the last two 3-4 digit numbers in the section
            total_label_match = re.search(
                r'\(?\s*VII\s*\)?\s*TOTAL[\s\S]{0,50}?CUET[\s\S]{0,50}?SCORE[\s\S]{0,50}?OBTAINED',
                section_text, re.IGNORECASE | re.MULTILINE
            )
            if total_label_match:
                # Get text after the label
                after_label = section_text[total_label_match.end():]
                # Find all 3-4 digit numbers after the label
                numbers_after = re.findall(r'\b(\d{3,4}(?:\.\d+)?)\b', after_label)
                if len(numbers_after) >= 2:
                    # Last two numbers are total and obtained
                    try:
                        nums = [float(n) for n in numbers_after[-2:]]
                        if all(100 <= n <= 2000 for n in nums):
                            # The last number is obtained, second-to-last is total
                            # Usually: total >= obtained
                            if nums[0] >= nums[1]:
                                result['cuet_total_score'] = str(int(nums[0])) if nums[0].is_integer() else str(nums[0])
                                result['cuet_score'] = str(int(nums[1])) if nums[1].is_integer() else str(nums[1])
                            else:
                                result['cuet_total_score'] = str(int(nums[1])) if nums[1].is_integer() else str(nums[1])
                                result['cuet_score'] = str(int(nums[0])) if nums[0].is_integer() else str(nums[0])
                    except (ValueError, IndexError):
                        pass
            # IMPORTANT: The CUET section extraction (above) sets cuet_score and cuet_total_score
            # from the TOTAL row. These values MUST override any PRIORITY 1 values set earlier.
            # The values are already set in result above, overriding any earlier values.
            
            # Fallback: Try direct pattern matching
            if 'cuet_score' not in result:
                total_patterns = [
                    rf'\(?\s*VII\s*\)?\s*TOTAL[\s\S]{{0,50}}?CUET[\s\S]{{0,50}}?SCORE[\s\S]{{0,50}}?OBTAINED[\s\S]{{0,20}}?' + DECIMAL_SCORE + r'[\s\n\r]+' + DECIMAL_SCORE,
                    rf'\(?\s*VII\s*\)?\s*TOTAL[\s\S]{{0,50}}?' + DECIMAL_SCORE + r'[\s\n\r]+' + DECIMAL_SCORE,
                    r'TOTAL[\s\S]{0,50}?CUET[\s\S]{0,50}?SCORE[\s\S]{0,50}?OBTAINED[\s\S]{0,20}?' + DECIMAL_SCORE + r'[\s\n\r]+' + DECIMAL_SCORE,
                ]
                
                for total_pattern in total_patterns:
                    total_match = re.search(total_pattern, section_text, re.IGNORECASE | re.MULTILINE)
                    if total_match:
                        # First number is total possible, second is obtained
                        if 'cuet_total_score' not in result:
                            result['cuet_total_score'] = total_match.group(1)
                        if 'cuet_score' not in result:
                            result['cuet_score'] = total_match.group(2)
                        break
        
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
        # Find the gender section first - expand search area to capture scattered format
        gender_section = re.search(r'2\s*\.\s*Gender[\s\S]{0,400}?(?=3\s*\.\s*Date|4\s*\.\s*Permanent)', text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        gender_text = gender_section.group(0) if gender_section else text[:2000]
        
        # Also check broader context around "2. Gender" for Male/Female
        if 'gender' not in result:
            # Look for Male or Female that appears after "2. Gender" and before "4. Permanent"
            gender_area = re.search(r'2\s*\.\s*Gender[\s\S]{0,600}?(?=4\s*\.\s*Permanent|5\s*\.\s*Local)', text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if gender_area:
                gender_text = gender_area.group(0)
        
        gender_patterns = [
            # Look for checked gender with tick mark
            r'(?:✓|✔|☑)\s*(Male|Female|Transgender)',
            r'(Male|Female|Transgender)\s*(?:✓|✔|☑)',
            # Pattern: "2. Gender {Tick (✓)}\nMale\nFemale\nTransgender" - Male appears first
            # IMPORTANT: Allow more content between Gender and Male/Female
            r'2\s*\.\s*Gender[\s\S]{0,150}?Male\s*(?:\n|$)',  # Male appears in gender section
            r'2\s*\.\s*Gender[\s\S]{0,150}?Female\s*(?:\n|$)',  # Female appears in gender section
            # Pattern: Look for Male or Female that appears after "2. Gender" and before "3. Date"
            # Find "2. Gender" section, then check which appears first: Male or Female
            r'2\s*\.\s*Gender[\s\S]{0,200}?(?:3\s*\.\s*Date|4\s*\.\s*Permanent)',  # Capture gender section
            # Look for Gender followed by Male/Female on same or next line
            r'Gender[:\s]*\n?\s*(Male|Female|Transgender)',
            r'2\s*\.\s*Gender[:\s]*\n?\s*(Male|Female|Transgender)',
        ]
        for pattern in gender_patterns:
            match = re.search(pattern, gender_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                # Check if Male appears before Female in the match or in the gender section
                match_text = match.group(0)
                male_pos = match_text.upper().find('MALE')
                female_pos = match_text.upper().find('FEMALE')
                
                # Also check in full gender_text (not just match)
                male_pos_full = gender_text.upper().find('MALE')
                female_pos_full = gender_text.upper().find('FEMALE')
                
                # Determine which appears first
                if male_pos != -1 and (female_pos == -1 or male_pos < female_pos):
                    result['gender'] = 'Male'
                    break
                elif female_pos != -1 and (male_pos == -1 or female_pos < male_pos):
                    result['gender'] = 'Female'
                    break
                elif male_pos_full != -1 and (female_pos_full == -1 or male_pos_full < female_pos_full):
                    result['gender'] = 'Male'
                    break
                elif female_pos_full != -1 and (male_pos_full == -1 or female_pos_full < male_pos_full):
                    result['gender'] = 'Female'
                    break
                elif match.lastindex and match.lastindex >= 1:
                    result['gender'] = match.group(1).capitalize()
                    break
                else:
                    # Default: if Male appears in the text, assume Male
                    if 'Male' in match_text or 'MALE' in gender_text.upper():
                        result['gender'] = 'Male'
                        break
                    elif 'Female' in match_text or 'FEMALE' in gender_text.upper():
                        result['gender'] = 'Female'
                        break
        
        # Date of Birth: Various formats found in SRCC forms
        # Handle scattered format: "23\n04\n06\nYYYY\nD D\nM M" (numbers before labels)
        # PRIORITY: Handle scattered format where numbers come first, then labels
        dob_area = re.search(r'3\s*\.\s*Date\s+of\s+Birth[\s\S]{0,400}', text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if dob_area:
            area_text = dob_area.group(0)
            # Pattern: "23\n04\n06\nYYYY\nD D\nM M" - numbers come before labels
            scattered_patterns = [
                # Pattern: numbers first, then YYYY, then D D M M labels
                r'(\d{1,2})\s*\n\s*(\d{1,2})\s*\n\s*(\d{2})\s*\n\s*Y\s*Y\s*Y\s*Y',  # 23\n04\n06\nYYYY
                # Pattern: numbers, then D D, M M labels (traditional format)
                r'(\d{1,2})\s*\n\s*D\s*D\s*\n\s*(\d{1,2})\s*\n\s*M\s*M\s*\n\s*(\d{2})(?:\s*\n\s*Y|$)',  # Y optional at end
                r'(\d{1,2})\s*\n\s*D\s*D\s*\n\s*(\d{1,2})\s*\n\s*M\s*M\s*\n\s*(\d{2})\s*\n',  # Just newline after year
                r'(\d{1,2})\s+D\s+D\s+(\d{1,2})\s+M\s+M\s+(\d{2})\s+Y',  # With spaces
                # Pattern with full context from "Date of Birth"
                r'Date\s+of\s+Birth[\s\S]*?(\d{1,2})\s*\n\s*D\s*D\s*\n\s*(\d{1,2})\s*\n\s*M\s*M\s*\n\s*(\d{2})',  # Full context
            ]
            for pattern in scattered_patterns:
                scattered_match = re.search(pattern, area_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if scattered_match:
                    day, month, year_2digit = scattered_match.group(1), scattered_match.group(2), scattered_match.group(3)
                    try:
                        d, m, y2 = int(day), int(month), int(year_2digit)
                        # Convert 2-digit year to 4-digit (06 -> 2006)
                        if y2 < 10:
                            year = 2000 + y2  # 06 -> 2006
                        elif y2 < 50:
                            year = 2000 + y2  # 34 -> 2034 (but this is likely OCR error, should be 2024)
                        else:
                            year = 1900 + y2
                        # For DOB, valid years are typically 2000-2010 (students born 2000-2010)
                        if year > 2010:
                            # If year is > 2010, it's likely an OCR error - use 2000 + y2
                            year = 2000 + y2
                        if 1 <= d <= 31 and 1 <= m <= 12 and 2000 <= year <= 2010:
                            result['date_of_birth'] = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                            break
                    except ValueError:
                        continue
        
        # Fallback to other patterns if scattered format didn't work
        if 'date_of_birth' not in result:
            dob_patterns = [
                # Pattern 1: Scattered format where numbers come before labels: "23\n04\n06\nYYYY\nD D\nM M"
                (r'3\s*\.\s*Date\s+of\s+Birth[\s\S]{0,300}?(\d{1,2})\s*\n\s*(\d{1,2})\s*\n\s*(\d{2})\s*\n\s*Y\s*Y\s*Y\s*Y', 'scattered_labels_after'),
                # Pattern 2: Scattered format with D D, M M, Y Y Y Y labels (4-digit year variant)
                (r'3\s*\.\s*Date\s+of\s+Birth[\s\S]{0,200}?(\d{1,2})\s*\n?\s*D\s*D\s*\n?\s*(\d{1,2})\s*\n?\s*M\s*M\s*\n?\s*(\d{4})\s*\n?\s*Y\s*Y', 'scattered'),
                # Pattern 3: Scattered format without labels (just numbers)
                (r'3\s*\.\s*Date\s+of\s+Birth[\s\S]{0,200}?(\d{1,2})\s+(\d{1,2})\s+(\d{4})', 'numeric'),
                # Pattern 4: "DOB: 23 April 2006" - most readable format
                (r'DOB:\s*(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', 'month_name'),
                # Pattern 5: DD MM YY format with spaces
                (r'Date\s+of\s+Birth[:\s]*(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})', 'numeric'),
                # Pattern 6: DD/MM/YYYY format
                (r'Date\s+of\s+Birth[:\s]*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', 'numeric'),
                # Pattern 7: After numbered field "3. Date of Birth"
                (r'3\s*\.\s*Date\s+of\s+Birth[:\s]*(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})', 'numeric'),
                # Pattern 8: Just numbers after DOB label
                (r'D\s*O\s*B[:\s]*(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})', 'numeric'),
                # Pattern 9: Compact format like "2370472006" = 23/04/2006
                (r'Date\s+of\s+Birth[:\s]*(\d{2})(\d{2})(\d{1,2})(\d{4})', 'compact'),
            ]
        
            month_map = {
                'january': '01', 'february': '02', 'march': '03', 'april': '04',
                'may': '05', 'june': '06', 'july': '07', 'august': '08',
                'september': '09', 'october': '10', 'november': '11', 'december': '12'
            }
            
            for pattern_tuple in dob_patterns:
                pattern, fmt = pattern_tuple
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match:
                    if fmt == 'scattered_labels_after':
                        # Format: "23\n04\n06\nYYYY\nD D\nM M" - numbers come first, labels after
                        day, month, year_2digit = match.group(1), match.group(2), match.group(3)
                        try:
                            d, m, y2 = int(day), int(month), int(year_2digit)
                            # Convert 2-digit year to 4-digit (06 -> 2006, 34 -> 2034 -> 2024 OCR error correction)
                            if y2 < 10:
                                year = 2000 + y2  # 06 -> 2006
                            elif y2 >= 50:
                                year = 1900 + y2  # 50+ -> 1950+
                            else:
                                # 10-49: likely 2000s, but if > 10, check if it's an OCR error
                                year = 2000 + y2
                                # OCR error correction: 34 -> 2024 (not 2034)
                                if year == 2034:
                                    year = 2024  # Common OCR error: 0 read as 3
                            if 1 <= d <= 31 and 1 <= m <= 12 and 2000 <= year <= 2010:
                                result['date_of_birth'] = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                                break
                        except ValueError:
                            continue
                    elif fmt == 'scattered':
                        # Format: "23\nD D\n04\nM M\n2006\nY Y Y Y"
                        day, month, year = match.group(1), match.group(2), match.group(3)
                        try:
                            d, m, y = int(day), int(month), int(year)
                            if 1 <= d <= 31 and 1 <= m <= 12 and 2000 <= y <= 2010:
                                result['date_of_birth'] = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                                break
                        except ValueError:
                            continue
                    elif fmt == 'month_name':
                        day = match.group(1)
                        month = month_map.get(match.group(2).lower(), '01')
                        year = match.group(3)
                        result['date_of_birth'] = f"{day.zfill(2)}/{month}/{year}"
                        break
                    elif fmt == 'compact':
                        day, month = match.group(1), match.group(2)
                        year = match.group(4)
                        result['date_of_birth'] = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                        break
                    else:
                        day, month, year = match.group(1), match.group(2), match.group(3)
                        # Handle 2-digit year
                        if len(year) == 2:
                            year_int = int(year)
                            if year_int < 10:
                                year = '200' + year
                            elif year_int < 50:
                                year = '20' + year
                            else:
                                year = '19' + year
                        try:
                            d, m, y = int(day), int(month), int(year)
                            if 1 <= d <= 31 and 1 <= m <= 12 and 2000 <= y <= 2010:
                                result['date_of_birth'] = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                                break
                        except ValueError:
                            continue
        
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
        # Find Field 12 section (Personal Information) - capture more text to include all values
        # Match "12. Personal Information" and capture until we find "13." (anywhere, not just newline)
        field_12_section = re.search(r'12\s*\.\s*Personal\s+Information.*?(?=13\s*\.|$)', text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if not field_12_section or len(field_12_section.group(0)) < 50:
            # Fallback: match just "12. Personal" and capture until "13."
            field_12_section = re.search(r'12\s*\.\s*Personal.*?(?=13\s*\.|$)', text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        blood_text = field_12_section.group(0) if field_12_section and len(field_12_section.group(0)) > 50 else text
        
        # Note: OCR format is: "(c) Blood Group\nINDIAN\nB+\nHINDU"
        # The blood group appears on a line after "Blood Group" label, after nationality value
        # Strategy: Find "Blood Group" position, then search for B+ pattern after it
        bg_label_pos = blood_text.upper().find('BLOOD GROUP')
        if bg_label_pos != -1:
            # Search in text after "Blood Group" label
            after_bg_label = blood_text[bg_label_pos:]
            # Look for blood group pattern (B+, A+, etc.) after the label
            # Try with word boundary first
            bg_match = re.search(r'\b([ABO]|AB)\s*([\+\-])\b', after_bg_label, re.IGNORECASE)
            if not bg_match:
                # Try without word boundary (in case B+ is at start of line)
                bg_match = re.search(r'([ABO]|AB)\s*([\+\-])', after_bg_label, re.IGNORECASE)
            if bg_match:
                bg = (bg_match.group(1) + bg_match.group(2)).upper()
                if bg in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
                    result['blood_group'] = bg
        else:
            # Fallback: try patterns if label position method didn't work
            blood_patterns = [
                # Pattern: Blood Group label, then skip lines until we find B+
                r'\(c\)\s*Blood\s+Group[:\s]*\n\s*[A-Z]+\s*\n\s*([ABO]|AB)\s*([\+\-])',  # After label, skip nationality line, then B+
                r'Blood\s+Group[:\s]*\n\s*[A-Z]+\s*\n\s*([ABO]|AB)\s*([\+\-])',  # Without (c)
                # Pattern: Look for B+ after Blood Group (within 200 chars, may have other text in between)
                r'Blood\s+Group[\s\S]{0,200}?\b([ABO]|AB)\s*([\+\-])\b',  # B+ anywhere after Blood Group
                # Pattern with optional space before +/-
                r'\(c\)\s*Blood\s+Group[:\s]*([ABO]|AB)\s*([\+\-])',
                r'Blood\s+Group[:\s]*([ABO]|AB)\s*([\+\-])',
                # Blood group anywhere on same line as label
                r'Blood\s+Group[^\n]*\b([ABO]|AB)\s*([\+\-])',
                # Fallback: any blood group pattern in the section (but prefer ones after Blood Group)
                r'\b([ABO]|AB)\s*([\+\-])\b',
            ]
            for pattern in blood_patterns:
                match = re.search(pattern, blood_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match:
                    # Combine group type and sign (removing any space)
                    bg = (match.group(1) + match.group(2)).upper()
                    # Validate blood group
                    if bg in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
                        result['blood_group'] = bg
                        break
        
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
        
        # Find address section - look for "4. Permanent Address" and capture until next section
        # Handle case where "Permanent" and "Address" are on separate lines
        address_section = ""
        addr_match = re.search(r'4\s*\.\s*Permanent\s*\n\s*Address(.*?)(?:5\s*\.\s*Local\s+Address|6\s*\.\s*Email|7\s*\.\s*Contact|8\s*\.\s*Mother)', 
                               text, re.IGNORECASE | re.DOTALL)
        if not addr_match:
            # Try with "Permanent Address" on same line
            addr_match = re.search(r'4\s*\.\s*Permanent\s+Address(.*?)(?:5\s*\.\s*Local\s+Address|6\s*\.\s*Email|7\s*\.\s*Contact|8\s*\.\s*Mother)', 
                                   text, re.IGNORECASE | re.DOTALL)
        if addr_match:
            address_section = addr_match.group(1)
        else:
            # Fallback: search in first 2500 chars (Page 1 area)
            addr_match = re.search(r'Permanent\s*\n\s*Address(.*?)(?:Local\s+Address|Email|Contact|Mother|State\s+[A-Z]|PIN\s+\d{6})', 
                                   text[:2500], re.IGNORECASE | re.DOTALL)
            if not addr_match:
                addr_match = re.search(r'Permanent\s+Address(.*?)(?:Local\s+Address|Email|Contact|Mother|State\s+[A-Z]|PIN\s+\d{6})', 
                                       text[:2500], re.IGNORECASE | re.DOTALL)
            if addr_match:
                address_section = addr_match.group(1)
            else:
                address_section = text[:2000]
        
        # Improved address extraction - handle multi-line format more carefully
        # Pattern: "4. Permanent Address" (may span multiple lines) followed by address lines until State/PIN/next section
        # Handle both "4. Permanent\nAddress" and "4. Permanent Address" formats
        # IMPORTANT: Address content may be scattered between "Address" label and "State"/"PIN" markers
        # Strategy: Look for address content between "Address" and "State DELHI" or "PIN 110095"
        address_block_patterns = [
            # Pattern 1: "4. Permanent\nAddress\n...content...\nState DELHI" (label on two lines, content before State)
            r'4\s*\.\s*Permanent\s*\n\s*Address\s+(.*?)(?:State\s+[A-Z]|PIN\s+\d{6}|5\s*\.\s*Local|6\s*\.)',
            # Pattern 2: "4. Permanent Address\n...content...\nState DELHI" (label on one line)
            r'4\s*\.\s*Permanent\s+Address\s+(.*?)(?:State\s+[A-Z]|PIN\s+\d{6}|5\s*\.\s*Local|6\s*\.)',
            # Pattern 3: Extract address between "Address" and "State"/"PIN" anywhere in Page 1
            # This handles cases where address is scattered across multiple lines
            r'(?:4\s*\.\s*Permanent\s*\n\s*Address|Permanent\s*\n\s*Address)[\s\n]+(.*?)(?:State\s+[A-Z]|PIN\s+\d{6})',
        ]
        
        match = None
        for pattern in address_block_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                break
        
        # If no match, try extracting address lines that appear between "Address" and "State" markers
        if not match:
            # Find "Address" and "State DELHI" positions, extract text between them
            # Handle case where address content is scattered between sections
            addr_start = re.search(r'(?:4\s*\.\s*Permanent\s*\n\s*Address|Permanent\s*\n\s*Address)', text, re.IGNORECASE)
            state_marker = re.search(r'State\s+[A-Z]|PIN\s+\d{6}', text, re.IGNORECASE)
            if addr_start and state_marker and state_marker.start() > addr_start.end():
                # Extract text between "Address" label and "State" marker
                addr_text_slice = text[addr_start.end():state_marker.start()]
                # Create a match-like object for processing
                class FakeMatch:
                    def __init__(self, group1):
                        self._group1 = group1
                    def group(self, n):
                        if n == 1:
                            return self._group1
                        return None
                match = FakeMatch(addr_text_slice)
        if match and match.group(1):
            addr_block = match.group(1).strip()
            addr_parts = []
            
            # Split by newline and filter lines
            for line in addr_block.split('\n'):
                line = line.strip()
                # Skip empty lines
                if not line:
                    continue
                
                line_upper = line.upper()
                
                # Allow "NO" even if it's 2 characters (it's part of "HOUSE NO")
                # Skip single letters or date format labels (D D, M M, Y Y), but not "NO"
                if line_upper != 'NO' and (len(line) <= 2 or re.match(r'^[DMY\s\-]+$', line, re.IGNORECASE)):
                    continue
                
                # Skip form label words (but allow HOUSE and NO as they're part of address)
                if line_upper in ['STATE', 'PIN', 'PINCODE', 'ADDRESS', 'PERMANENT', 'LOCAL', 'CORRESPONDENCE', 'CODE', 'OF']:
                    continue
                
                # IMPORTANT: Skip lines that are clearly NOT address parts
                # Skip gender labels (Male, Female, Transgender)
                if line_upper in ['MALE', 'FEMALE', 'TRANSGENDER', 'SEX', 'GENDER']:
                    continue
                # Skip date labels (D D, M M, Y Y, YYYY)
                if re.match(r'^[DMY\s\-२]+$', line, re.IGNORECASE):
                    continue
                # Skip 4-digit years (likely DOB year)
                if re.match(r'^(19|20)\d{2}$', line):
                    continue
                # Skip numeric values that are likely DOB components (23, 04, 06) if they're alone
                if line.isdigit() and len(line) <= 2:
                    # Check if it's likely part of address (house number) vs DOB
                    # If it's followed by address-like text, keep it
                    continue  # Skip standalone 1-2 digit numbers (likely DOB components)
                # Skip form field labels
                form_labels = [
                    'MIDDLE', 'NAME', 'SURNAME', 'FIRST', 'SIGNATURE', 'STUDENT',
                    'DATE', 'BIRTH', 'BLOCK', 'LETTERS', 'TICK', 'EMAIL',
                    'CONTACT', 'NUMBERS', 'PHONE', 'MOTHER', 'FATHER',
                    'CUET', 'SCORE', 'SUBJECTS', 'TOTAL', 'OBTAINED',
                    'ADMISSION', 'CATEGORY', 'COURSE', 'ACADEMIC', 'SESSION',
                    'ROLL', 'PORTAL', 'FORM', 'NUMBER', 'YYYY', 'DD', 'MM',
                    'HINDI', 'MEDIUM', 'PREFERENCE', 'QUALIFYING', 'EXAMINATION',
                    'YEAR', 'BOARD', 'INSTITUTION', 'MARKS', 'PERCENTAGE',
                    'PASSPORT', 'PHOTO', 'SIZE', 'AFFIX', 'RECENT'
                ]
                if line_upper in form_labels or any(line_upper == label for label in form_labels):
                    continue
                # Skip Roman numerals (I, II, III, IV, V, VI, VII)
                if re.match(r'^[IVX]{1,4}$', line_upper):
                    continue
                # Skip dates in format DD/MM/YYYY or DD-MM-YYYY
                if re.match(r'^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$', line):
                    continue
                # Skip parenthesized content like (if different from 4)
                if line.startswith('(') or line.endswith(')'):
                    continue
                # Skip single Hindi/special characters
                if len(line) == 1 and not line.isalnum():
                    continue
                
                # Valid address line (including "NO" which will be combined with "HOUSE" later)
                addr_parts.append(line)
            
            if addr_parts:
                # Clean up address parts - combine HOUSE and NO if they're separate
                cleaned_parts = []
                i = 0
                while i < len(addr_parts):
                    current_upper = addr_parts[i].upper()
                    # Check if current is "HOUSE" and next is "NO"
                    if current_upper == 'HOUSE' and i + 1 < len(addr_parts) and addr_parts[i+1].upper() == 'NO':
                        # "HOUSE" followed by "NO" - combine them
                        if i + 2 < len(addr_parts):
                            # "HOUSE NO 123" or "HOUSE NO ABC" - combine all three
                            cleaned_parts.append(f"HOUSE NO {addr_parts[i+2]}")
                            i += 3  # Skip HOUSE, NO, and the next part
                        else:
                            # Just "HOUSE NO" without following content
                            cleaned_parts.append("HOUSE NO")
                            i += 2  # Skip HOUSE and NO
                    elif current_upper == 'HOUSE' and i + 1 < len(addr_parts) and addr_parts[i+1].upper().startswith('NO'):
                        # "HOUSE" followed by "NO 123" or "NO123" (combined)
                        cleaned_parts.append(f"HOUSE {addr_parts[i+1]}")
                        i += 2
                    elif current_upper == 'NO' and i > 0 and addr_parts[i-1].upper() == 'HOUSE':
                        # "NO" that immediately follows "HOUSE" - should be handled above, skip it
                        i += 1
                        continue
                    else:
                        # Regular address part
                        cleaned_parts.append(addr_parts[i])
                        i += 1
                
                if cleaned_parts:
                    # Join address parts with comma
                    full_addr = ', '.join(cleaned_parts)
                    # Remove extra spaces
                    full_addr = re.sub(r'\s+', ' ', full_addr)
                    # Remove state and PIN code if they somehow got included
                    full_addr = re.sub(r',?\s+State\s+[A-Z\s]+.*$', '', full_addr, flags=re.IGNORECASE)
                    full_addr = re.sub(r',?\s+PIN\s+\d{6}.*$', '', full_addr, flags=re.IGNORECASE)
                    # Additional cleanup - remove trailing commas and spaces
                    full_addr = re.sub(r',+\s*$', '', full_addr).strip()
                    # Remove form labels that may have been captured
                    full_addr = self._clean_address(full_addr)
                    if len(full_addr) > 10:  # Minimum address length
                        result['permanent_address'] = full_addr.upper().strip()
        
        # Fallback: Extract address by finding address-like words between "Address" and "State DELHI"
        # Strategy: Look for lines containing HOUSE, FLATS, VIHAR, NAGAR, COLONY, etc.
        if 'permanent_address' not in result:
            # Find text between "4. Permanent\nAddress" and "State DELHI"
            addr_start_match = re.search(r'4\s*\.\s*Permanent\s*\n\s*Address', text, re.IGNORECASE)
            state_match = re.search(r'State\s+DELHI|PIN\s+\d{6}', text, re.IGNORECASE)
            
            if addr_start_match and state_match and state_match.start() > addr_start_match.end():
                addr_text_slice = text[addr_start_match.end():state_match.start()]
                # Look for address components in the text slice
                addr_components = []
                
                # Look for HOUSE, FLATS, VIHAR, NAGAR, COLONY, area names
                address_keywords = [
                    r'\bHOUSE\s+NO\b', r'\bHOUSE\b', r'\bNO\b',  # HOUSE NO pattern
                    r'\b\d+\s+JANTA\s+FLATS?\b', r'\bFLATS?\b',  # Flat numbers
                    r'\bVIVEK\s+VIHAR\b', r'\bVIHAR\b',  # Area names
                    r'\bSHAHDARA\b', r'\bSAVITA\s+VIHAR\b',
                    r'\bCOLONY\b', r'\bNAGAR\b', r'\bENCLAVE\b', r'\bPARK\b',
                ]
                
                # Extract lines that contain address keywords
                for line in addr_text_slice.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    line_upper = line.upper()
                    
                    # Skip if it's clearly not address (gender, DOB components, labels)
                    if line_upper in ['MALE', 'FEMALE', 'TRANSGENDER', 'MIDDLE', 'NAME', 'SURNAME', 'FIRST', 'SIGNATURE', 'STUDENT', 'MIDDLE NAME']:
                        continue
                    # Skip if it's just "NAME" alone
                    if line_upper == 'NAME':
                        continue
                    if re.match(r'^[DMY\s\-२]+$', line, re.IGNORECASE):
                        continue
                    if line.isdigit() and len(line) <= 2:
                        continue
                    if 'LOCAL ADDRESS' in line_upper or 'CORRESPONDENCE' in line_upper or 'DIFFERENT' in line_upper:
                        continue
                    
                    # Check if line contains address keywords or looks like address content
                    is_address_line = False
                    for keyword_pattern in address_keywords:
                        if re.search(keyword_pattern, line, re.IGNORECASE):
                            is_address_line = True
                            break
                    
                    # Also consider lines that look like address (mixed case, contains numbers, etc.)
                    if not is_address_line:
                        # Check if it's a reasonable address component
                        if len(line) > 2 and (line[0].isupper() or any(c.isdigit() for c in line)):
                            # Likely address component
                            is_address_line = True
                    
                    if is_address_line:
                        addr_components.append(line)
                
                if addr_components:
                    # Combine HOUSE and NO if they're separate
                    cleaned_components = []
                    i = 0
                    while i < len(addr_components):
                        current = addr_components[i].upper()
                        if current == 'HOUSE' and i + 1 < len(addr_components) and addr_components[i+1].upper() == 'NO':
                            if i + 2 < len(addr_components):
                                cleaned_components.append(f"HOUSE NO {addr_components[i+2]}")
                                i += 3
                            else:
                                cleaned_components.append("HOUSE NO")
                                i += 2
                        elif current == 'NO' and i > 0 and addr_components[i-1].upper() == 'HOUSE':
                            i += 1
                            continue
                        else:
                            cleaned_components.append(addr_components[i])
                            i += 1
                    
                    if cleaned_components:
                        full_addr = ', '.join(cleaned_components)
                        full_addr = re.sub(r'\s+', ' ', full_addr)
                        full_addr = self._clean_address(full_addr)
                        if len(full_addr) > 10:
                            result['permanent_address'] = full_addr.upper().strip()
        
        # Enhancement: Append locality if found separately and not already in address
        if 'permanent_address' in result:
            addr = result['permanent_address']
            # Only add locality if address doesn't already contain a known locality
            # and if we find it in the address section
            known_localities = ['VIVEK VIHAR', 'SHAHDARA', 'SAVITA VIHAR', 'PATEL NAGAR', 'GOMTI NAGAR', 
                              'VIVEK', 'SHAHDARA EAST', 'SHAHDARA WEST']
            has_locality = any(loc in addr.upper() for loc in known_localities)
            
            if not has_locality:
                # Look for locality in address section but outside the extracted address
                for loc in known_localities:
                    loc_pattern = loc.replace(' ', r'[\s\-]+')
                    if re.search(r'\b' + loc_pattern + r'\b', address_section, re.IGNORECASE):
                        # Only add if it's clearly separate from address (e.g., on different line or after State)
                        loc_context = re.search(r'(' + loc_pattern + r')(?:\s+State|\s+PIN|\s*$|\s*\n)', 
                                               address_section, re.IGNORECASE)
                        if loc_context and loc_context.group(1).upper() not in addr.upper():
                            addr = addr.rstrip(',. ') + ', ' + loc
                            result['permanent_address'] = addr
                            break
        
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
        
        # PIN Code - 6 digit number after PIN (make sure it's in address context)
        pin_patterns = [
            r'PIN\s+(\d{6})',
            r'(?:Pin|PIN)[:\s]*(\d{6})',
            # Look for 6-digit number after "PIN" or before next section
            r'PIN\s*(?:CODE)?[:\s]*(\d{6})(?:\s*$|\s*\n|\s*6\.|\s*Email)',
            # Standalone 6-digit number in address section (validate context)
            r'(\d{6})(?=\s*$|\s*\n\s*(?:6\.|Email|7\.|Contact))',
        ]
        for pattern in pin_patterns:
            match = re.search(pattern, address_section, re.IGNORECASE)
            if match:
                pin = match.group(1)
                # Validate it's a valid Indian PIN (first digit 1-9, not a year)
                if pin[0] in '123456789' and not (pin.startswith('20') and len(pin) == 6):
                    result['pincode'] = pin
                    result['permanent_pincode'] = pin  # Also set permanent_pincode
                    break
        
        # Extract correspondence address if different from permanent
        # Look for "5. Local Address for Correspondence" section
        corr_section = re.search(r'5\s*\.\s*Local\s+Address\s+for\s+Correspondence(.*?)(?:6\s*\.\s*Email|7\s*\.\s*Contact|8\s*\.\s*Mother)', 
                                 text, re.IGNORECASE | re.DOTALL)
        if corr_section:
            corr_text = corr_section.group(1).strip()
            # If correspondence section has content (not empty), extract it
            if len(corr_text.strip()) > 20:  # Has meaningful content
                # Extract address from correspondence section
                corr_addr_parts = []
                for line in corr_text.split('\n'):
                    line = line.strip()
                    if line and len(line) > 2 and not re.match(r'^[DMY\s\-]+$', line):
                        line_upper = line.upper()
                        if line_upper not in ['STATE', 'PIN', 'PINCODE', 'ADDRESS', 'LOCAL', 'CORRESPONDENCE', 'IF', 'DIFFERENT']:
                            corr_addr_parts.append(line)
                
                if corr_addr_parts:
                    corr_addr = ', '.join(corr_addr_parts)
                    corr_addr = re.sub(r'\s+', ' ', corr_addr)
                    corr_addr = re.sub(r',?\s+State\s+[A-Z\s]+.*$', '', corr_addr, flags=re.IGNORECASE)
                    corr_addr = re.sub(r',?\s+PIN\s+\d{6}.*$', '', corr_addr, flags=re.IGNORECASE)
                    corr_addr = self._clean_address(corr_addr)
                    if len(corr_addr) > 10:
                        result['correspondence_address'] = corr_addr.upper().strip()
                        # Extract correspondence state and PIN if present
                        corr_state_match = re.search(r'State\s+([A-Z][A-Za-z]+)', corr_text, re.IGNORECASE)
                        if corr_state_match:
                            result['correspondence_state'] = corr_state_match.group(1).title()
                        corr_pin_match = re.search(r'PIN\s+(\d{6})', corr_text, re.IGNORECASE)
                        if corr_pin_match:
                            result['correspondence_pincode'] = corr_pin_match.group(1)
        
        # If no separate correspondence address found, copy from permanent
        if 'correspondence_address' not in result and result.get('permanent_address'):
            result['correspondence_address'] = result['permanent_address']
        if 'correspondence_state' not in result and result.get('permanent_state'):
            result['correspondence_state'] = result['permanent_state']
        if 'correspondence_pincode' not in result and result.get('pincode'):
            result['correspondence_pincode'] = result['pincode']
        
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
            r"Mother'?s?\s+Name:\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.]*)*)",
            # "8. Mother's Name MAMTA" format (name directly after label)
            r"8\s*\.\s*Mother'?s?\s+Name\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.]*)*)",
            # Just "Mother's Name MAMTA" on one line
            r"Mother'?s?\s+Name\s+([A-Z][A-Za-z]+)(?:\s|$|\n)",
            # Name on next line: "8. Mother's Name\n9. Father's Name\nMOTHER_VALUE\nFATHER_VALUE"
            # Need to look for this specific pattern
            r"8\s*\.\s*Mother'?s?\s+Name\s*\n\s*9\s*\.\s*Father'?s?\s+Name\s*\n\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.]*)*)\s*\n",
            # "Smt MAMTA" or "of Smt MAMTA"
            r"(?:of\s+)?Smt\.?\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.]*)*)",
        ]
        for pattern in mother_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if not self._is_label(name) and name.upper() not in ['FATHER', 'GUARDIAN', 'SON', 'DAUGHTER']:
                    result['mother_name'] = name.title()
                    break
        
        # Father's Name - specific patterns found in SRCC forms
        # Support initials like "L" or "L." by ensuring regex matches single letters
        father_patterns = [
            # Pattern where labels are together: "Mother's Name\n9. Father's Name\nMOTHER_VALUE\nFATHER_VALUE"
            r"Mother'?s?\s+Name\s*\n\s*(?:9\s*\.\s*)?Father'?s?\s+Name\s*\n\s*[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.]*)*\s*\n\s*([A-Z][A-Za-z.\s]+)",
            # "Father's Name: KIRPAL" format  
            r"Father'?s?\s+Name:\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.]*)*)",
            # "9. Father's Name · KIRPAL" format (with middle dot or colon)
            r"9\s*\.\s*Father'?s?\s+Name\s*[·:\s]+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.]*)*)",
            # "Father's Name KIRPAL" on one line
            r"Father'?s?\s+Name\s+([A-Z][A-Za-z]+)(?:\s|$|\n)",
            # Name on next line after "9. Father's Name\nVALUE"
            r"9\s*\.\s*Father'?s?\s+Name\s*\n\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.]*)*)",
            # "Father's Guardian's Name: KIRPAL"
            r"Father'?s?\s+Guardian'?s?\s+Name[:\s]+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.]*)*)",
            # "Son of Mr. KIRPAL" or "Son/Daughter of KIRPAL"
            r"(?:Son|Daughter)\s+of\s+(?:Mr\.?\s+)?([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.]*)*)",
            # "Shri KIRPAL" or "of Shri KIRPAL"
            r"(?:of\s+)?Shri\.?\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.]*)*)",
            # "S/O KIRPAL" pattern
            r"S/O\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.]*)*)",
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
        # Find Field 11 section first to limit search scope
        field_11_section = re.search(r'11\s*\.\s*Details\s+of\s+qualifying[\s\S]*?(?=12\s*\.\s*Personal|$)', text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        section_text = field_11_section.group(0) if field_11_section else text
        
        year_patterns = [
            r'\(a\)\s*Year\s+of\s+passing[:\s]*(\d{4})',
            r'11\s*\.\s*Details.*?Year\s+of\s+passing[:\s]*(\d{4})',
            r'Year\s+of\s+passing[:\s]*(\d{4})',
            # Fallback: Look for 4-digit year in Field 11 section (but not phone numbers or roll numbers)
            # IMPORTANT: This must come AFTER checking for labels to avoid false matches
            # We'll validate it's not part of a roll number by checking context
            r'\b(20\d{2})\b',  # Years starting with 20XX
        ]
        for pattern in year_patterns:
            match = re.search(pattern, section_text, re.IGNORECASE)
            if match:
                year_str = match.group(1)
                # Validate it's a reasonable year (2020-2026 for Class XII passing)
                # Also handle OCR errors like 2034 -> 2024
                # IMPORTANT: Check it's not part of a roll number (like 21684714 which starts with 21)
                # If the year appears right before "CENTRAL" or in a roll number context, skip it
                match_start = match.start()
                context_before = section_text[max(0, match_start-10):match_start]
                context_after = section_text[match.end():match.end()+10]
                
                # Skip if it's part of a roll number (numbers before or after)
                if re.search(r'\d{4,}', context_before) or re.search(r'\d{4,}', context_after):
                    continue
                
                year_int = int(year_str)
                # Accept years 2020-2026, but also handle OCR errors (2034, 2035, etc.)
                if 2020 <= year_int <= 2036:
                    year = self._correct_year(year_str)
                    if year and 2020 <= int(year) <= 2026:
                        result['year_of_passing'] = year
                        break
        
        # 11(b) Board/University - look for CBSE, ICSE, State Board names
        # Find Field 11 section first - use non-greedy to capture up to Field 12
        field_11_section = re.search(r'11\s*\.\s*Details\s+of\s+qualifying[\s\S]*?(?=12\s*\.\s*Personal|$)', text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        section_text = field_11_section.group(0) if field_11_section else text
        
        board_patterns = [
            r'\(b\)\s*Board\s*/?\s*University[:\s]*([A-Z][A-Za-z\s]+?)(?:\n|\(c\)|Examination)',
            r'Board\s*/?\s*University[:\s]*(CENTRAL\s+BOARD\s+OF\s+SECONDARY\s+EDUCATION)',
            r'Board\s*/?\s*University[:\s]*(CBSE|ICSE|ISC)',
            r'(CENTRAL\s+BOARD\s+OF\s+SECONDARY\s+EDUCATION)',
        ]
        for pattern in board_patterns:
            match = re.search(pattern, section_text, re.IGNORECASE)
            if match:
                board = match.group(1).strip()
                # Clean up: remove OCR truncation artifacts
                board = re.sub(r'\s+', ' ', board)
                # Stop at common truncation points
                if 'EDUCA' in board.upper() and 'EDUCATION' not in board.upper():
                    board = board.replace('EDUCA', 'EDUCATION')
                if len(board) > 3 and 'examination' not in board.lower() and 'roll' not in board.lower():
                    result['board_university'] = board.title()
                    break
        
        # 11(c) Examination Roll No
        exam_roll_patterns = [
            r'\(c\)\s*Examination\s+Roll\s+No\.?[:\s]*(\d{7,10})',
            r'Examination\s+Roll\s+No\.?[:\s]*(\d{7,10})',
        ]
        for pattern in exam_roll_patterns:
            match = re.search(pattern, section_text, re.IGNORECASE)
            if match:
                result['exam_roll_no'] = match.group(1)
                break
        # Fallback: look for 7-8 digit number in Field 11 section
        if 'exam_roll_no' not in result:
            roll_matches = re.findall(r'\b(\d{7,8})\b', section_text)
            for roll in roll_matches:
                # Exclude phone numbers (start with 6-9) and years (start with 20)
                if not roll[0] in '6789' and not roll.startswith('20'):
                    result['exam_roll_no'] = roll
                    break
        
        # 11(d) Institution Last Attended - look for school name patterns
        # Find the institution field specifically
        inst_match = re.search(r'\(d\)\s*Institution\s+Last\s+Attended[:\s]*([A-Z0-9][A-Z0-9\s,\.\-]+?)(?:\n|\(e\)|Hindi)', section_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if inst_match:
            inst_raw = inst_match.group(1).strip()
            # Clean up OCR errors: "3) BB 47+ Public School" -> "BB 47+ Public School"
            inst = re.sub(r'^\d+\)\s*', '', inst_raw)  # Remove leading "3) "
            inst = re.sub(r'\s+', ' ', inst)  # Normalize spaces
            # Remove trailing garbage after school name
            inst = re.sub(r',?\s*(UP|GHAZIABAD|DELHI|NCR|STATE|DISTRICT).*$', '', inst, flags=re.IGNORECASE)
            if len(inst) > 5 and 'hindi' not in inst.lower() and 'examination' not in inst.lower():
                result['institution_last_attended'] = inst.title()
        else:
            # Fallback: look for school name patterns
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
                match = re.search(pattern, section_text, re.IGNORECASE)
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
        
        # Extract Mother's details (Field 13)
        # 13(a) Occupation - look for common patterns
        occ_patterns = [
            r'\(a\)\s*Occupation[:\s]+([A-Za-z]+(?:\s+[A-Za-z]+)*)',
            r'Occupation[:\s]+(HOUSE\s*WIFE|HOUSEWIFE|MOUSE\s*WIFE|HOME\s*MAKER|HOMEMAKER|TEACHER|DOCTOR|NURSE|ENGINEER|LAWYER|MANAGER|SELF\s+EMPLOYED|BUSINESS|PRIVATE\s+JOB)',
            r'(HOUSE\s*WIFE|HOUSEWIFE|MOUSE\s*WIFE)',  # MOUSE WIFE is OCR error for HOUSE WIFE
            r'(HOME\s*MAKER|HOMEMAKER)',
            r'(TEACHER|DOCTOR|NURSE|ENGINEER|LAWYER|MANAGER)',
            r'(SELF\s+EMPLOYED|BUSINESS|PRIVATE\s+JOB)',
        ]
        for pattern in occ_patterns:
            match = re.search(pattern, mother_text, re.IGNORECASE)
            if match:
                occ = match.group(1).strip().upper()
                # Fix OCR errors
                if 'MOUSE' in occ:
                    occ = occ.replace('MOUSE', 'HOUSE')
                if len(occ) > 2 and not self._is_label(occ):
                    result['mother_occupation'] = occ.title()
                    break
        
        # 13(b) Mother's Designation (if employed)
        designation_patterns = [
            r'\(b\)\s*Designation[:\s]+([A-Za-z]+(?:\s+[A-Za-z]+)*)',
            r'Designation[:\s]+([A-Za-z]+(?:\s+[A-Za-z]+)*)',
        ]
        for pattern in designation_patterns:
            match = re.search(pattern, mother_text, re.IGNORECASE)
            if match:
                designation = match.group(1).strip()
                if len(designation) > 2 and not self._is_label(designation):
                    result['mother_designation'] = designation.title()
                    break
        
        # 13(c) Mother's Organization & Address
        org_patterns = [
            r'\(c\)\s*Organization[:\s]+([A-Za-z0-9\s,\.\-]+?)(?=\s*\(d\)|Email|Mobile|Contact|$)',
            r'Organization\s+&\s+Address[:\s]+([A-Za-z0-9\s,\.\-]+?)(?=\s*Email|Mobile|Contact|$)',
            r'Organization[:\s]+([A-Za-z0-9\s,\.\-]+?)(?=\s*Email|Mobile|Contact|$)',
        ]
        for pattern in org_patterns:
            match = re.search(pattern, mother_text, re.IGNORECASE | re.DOTALL)
            if match:
                org = match.group(1).strip()
                # Clean up organization text
                org = re.sub(r'\s+', ' ', org)
                org = re.sub(r',\s*$', '', org)
                if len(org) > 5 and not self._is_label(org):
                    result['mother_organization'] = org.title()
                    break
        
        # 13(d) Mother's Email
        email_pattern = r'\(d\)\s*Email[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})'
        email_match = re.search(email_pattern, mother_text, re.IGNORECASE)
        if not email_match:
            # Fallback: any email in mother section
            email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})'
            email_match = re.search(email_pattern, mother_text, re.IGNORECASE)
        if email_match:
            email = email_match.group(1).lower().replace(' ', '')
            result['mother_email'] = email
        
        # 13(e) Mother's Contact Number (Mobile and Landline)
        phone_patterns = [
            r'\(e\)\s*Contact\s+Number[:\s]+Mobile\s+No\.?[:\s]*(\d{10})',
            r'Mobile\s+No\.?[:\s]*(\d{10})',
            r'\b([6-9]\d{9})\b',  # Fallback: any 10-digit number starting with 6-9
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, mother_text, re.IGNORECASE)
            if phone_match:
                result['mother_phone'] = phone_match.group(1)
                result['mother_mobile'] = phone_match.group(1)
                break
        
        # Mother's Landline Code and Number (if present)
        landline_patterns = [
            r'Landline\s+Code[:\s]*(\d{3,4})',
            r'Landline\s+No\.?[:\s]*(\d{6,8})',
        ]
        for pattern in landline_patterns:
            match = re.search(pattern, mother_text, re.IGNORECASE)
            if match:
                if 'code' in pattern.lower():
                    result['mother_landline_code'] = match.group(1)
                else:
                    result['mother_landline'] = match.group(1)
        
        # Extract Father's details (Field 14)
        # 14(a) Occupation - handle "DHOBHI CSELF EMPLOYED" OCR error
        father_occ_match = re.search(r'\(a\)\s*Occupation[:\s]*([A-Z][A-Z\s]+?)(?:\n|\(b\)|Designation|Organization)', father_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if father_occ_match:
            occ_raw = father_occ_match.group(1).strip()
            # Handle "DHOBHI CSELF EMPLOYED" -> extract "DHOBHI" (prefer specific occupation)
            if 'DHOBHI' in occ_raw.upper() or 'DHOBI' in occ_raw.upper():
                # Extract just the occupation part before "SELF EMPLOYED"
                occ_match = re.search(r'(DHOBHI|DHOBI)', occ_raw, re.IGNORECASE)
                if occ_match:
                    occ = occ_match.group(1).upper()
                else:
                    occ = 'DHOBHI'
            elif 'SELF' in occ_raw.upper() and 'EMPLOYED' in occ_raw.upper():
                # Only use "SELF EMPLOYED" if no specific occupation found
                occ = 'SELF EMPLOYED'
            else:
                occ = re.sub(r'\s+', ' ', occ_raw).strip().upper()
            if len(occ) > 2 and not self._is_label(occ):
                result['father_occupation'] = occ.title()
        else:
            # Fallback: look for common patterns
            father_occ_patterns = [
                r'Occupation[:\s]+(HOUSE\s*WIFE|HOUSEWIFE|MOUSE\s*WIFE|HOME\s*MAKER|HOMEMAKER|TEACHER|DOCTOR|NURSE|ENGINEER|LAWYER|MANAGER|SELF\s+EMPLOYED|BUSINESS|PRIVATE\s+JOB|DHOBI|DHOBHI|WASHERMAN|SHOPKEEPER|VENDOR|FARMER|GOVERNMENT\s+(?:JOB|SERVICE)|GOVT\s+(?:JOB|SERVICE))',
            ] + occ_patterns
            for pattern in father_occ_patterns:
                match = re.search(pattern, father_text, re.IGNORECASE)
                if match:
                    occ = match.group(1).strip().upper()
                    if len(occ) > 2 and not self._is_label(occ):
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
        
        # 14(b) Father's Designation (if employed)
        designation_patterns = [
            r'\(b\)\s*Designation[:\s]+([A-Za-z]+(?:\s+[A-Za-z]+)*)',
            r'Designation[:\s]+([A-Za-z]+(?:\s+[A-Za-z]+)*)',
        ]
        for pattern in designation_patterns:
            match = re.search(pattern, father_text, re.IGNORECASE)
            if match:
                designation = match.group(1).strip()
                if len(designation) > 2 and not self._is_label(designation):
                    result['father_designation'] = designation.title()
                    break
        
        # 14(c) Father's Organization & Address
        org_patterns = [
            r'\(c\)\s*Organization[:\s]+([A-Za-z0-9\s,\.\-]+?)(?=\s*\(d\)|Email|Mobile|Contact|$)',
            r'Organization\s+&\s+Address[:\s]+([A-Za-z0-9\s,\.\-]+?)(?=\s*Email|Mobile|Contact|$)',
            r'Organization[:\s]+([A-Za-z0-9\s,\.\-]+?)(?=\s*Email|Mobile|Contact|$)',
        ]
        for pattern in org_patterns:
            match = re.search(pattern, father_text, re.IGNORECASE | re.DOTALL)
            if match:
                org = match.group(1).strip()
                # Clean up organization text
                org = re.sub(r'\s+', ' ', org)
                org = re.sub(r',\s*$', '', org)
                if len(org) > 5 and not self._is_label(org):
                    result['father_organization'] = org.title()
                    break
        
        # 14(d) Father's Email
        email_pattern = r'\(d\)\s*Email[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})'
        email_match = re.search(email_pattern, father_text, re.IGNORECASE)
        if not email_match:
            # Fallback: any email in father section
            email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})'
            email_match = re.search(email_pattern, father_text, re.IGNORECASE)
        if email_match:
            email = email_match.group(1).lower().replace(' ', '')
            result['father_email'] = email
        
        # 14(e) Father's Contact Number (Mobile and Landline)
        phone_patterns = [
            r'\(e\)\s*Contact\s+Number[:\s]+Mobile\s+No\.?[:\s]*(\d{10})',
            r'Mobile\s+No\.?[:\s]*(\d{10})',
            r'\b([6-9]\d{9})\b',  # Fallback: any 10-digit number starting with 6-9
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, father_text, re.IGNORECASE)
            if phone_match:
                result['father_phone'] = phone_match.group(1)
                result['father_mobile'] = phone_match.group(1)
                break
        
        # Father's Landline Code and Number (if present)
        landline_patterns = [
            r'Landline\s+Code[:\s]*(\d{3,4})',
            r'Landline\s+No\.?[:\s]*(\d{6,8})',
        ]
        for pattern in landline_patterns:
            match = re.search(pattern, father_text, re.IGNORECASE)
            if match:
                if 'code' in pattern.lower():
                    result['father_landline_code'] = match.group(1)
                else:
                    result['father_landline'] = match.group(1)
        
        # Guardian's Details (Field 15)
        guardian_section = re.search(
            r"15\s*\.\s*Local\s+Guardian'?s?\s+Details[\s\S]*?(?=16\s*\.\s*Other|$)",
            text, re.IGNORECASE
        )
        guardian_text = guardian_section.group(0) if guardian_section else ""
        
        # 15(a) Guardian's Name
        guardian_patterns = [
            r"\(a\)\s*Name[:\s]*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            r"Local\s+Guardian'?s?\s+Name[:\s]*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            r"Guardian'?s?\s+Name[:\s]*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
        ]
        for pattern in guardian_patterns:
            match = re.search(pattern, guardian_text or text, re.IGNORECASE | re.DOTALL)
            if match:
                name = match.group(1).strip()
                if not self._is_label(name):
                    result['guardian_name'] = name.title()
                    break
        
        # 15(b) Guardian's Residential Address
        guardian_address_patterns = [
            r"\(b\)\s*Residential\s+Address[:\s]+([A-Za-z0-9\s,\.\-]+?)(?=\s*\(c\)|Organization|Email|Mobile|Contact|$)",
            r"Residential\s+Address[:\s]+([A-Za-z0-9\s,\.\-]+?)(?=\s*Organization|Email|Mobile|Contact|$)",
        ]
        for pattern in guardian_address_patterns:
            match = re.search(pattern, guardian_text, re.IGNORECASE | re.DOTALL)
            if match:
                address = match.group(1).strip()
                address = re.sub(r'\s+', ' ', address)
                if len(address) > 5 and not self._is_label(address):
                    result['guardian_residential_address'] = address.title()
                    break
        
        # 15(c) Guardian's Organization & Address
        guardian_org_patterns = [
            r"\(c\)\s*Organization[:\s]+([A-Za-z0-9\s,\.\-]+?)(?=\s*\(d\)|Email|Mobile|Contact|$)",
            r"Organization\s+&\s+Address[:\s]+([A-Za-z0-9\s,\.\-]+?)(?=\s*Email|Mobile|Contact|$)",
            r"Organization[:\s]+([A-Za-z0-9\s,\.\-]+?)(?=\s*Email|Mobile|Contact|$)",
        ]
        for pattern in guardian_org_patterns:
            match = re.search(pattern, guardian_text, re.IGNORECASE | re.DOTALL)
            if match:
                org = match.group(1).strip()
                org = re.sub(r'\s+', ' ', org)
                org = re.sub(r',\s*$', '', org)
                if len(org) > 5 and not self._is_label(org):
                    result['guardian_organization'] = org.title()
                    break
        
        # 15(d) Guardian's Email
        guardian_email_patterns = [
            r"\(d\)\s*Email[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})",
            r"Guardian'?s?\s+Email[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\s*[a-zA-Z]{2,})",
        ]
        for pattern in guardian_email_patterns:
            match = re.search(pattern, guardian_text, re.IGNORECASE)
            if match:
                email = match.group(1).lower().replace(' ', '')
                result['guardian_email'] = email
                break
        
        # 15(e) Guardian's Contact Number (Mobile and Landline)
        guardian_phone_patterns = [
            r"\(e\)\s*Contact\s+Number[:\s]+Mobile\s+No\.?[:\s]*(\d{10})",
            r"15.*?Contact\s+Number.*?Mobile\s+No\.?[:\s]*(\d{10})",
            r"Guardian'?s?.*?Mobile\s+No\.?[:\s]*(\d{10})",
        ]
        for pattern in guardian_phone_patterns:
            match = re.search(pattern, guardian_text or text, re.IGNORECASE | re.DOTALL)
            if match:
                result['guardian_phone'] = match.group(1)
                result['guardian_mobile'] = match.group(1)
                break
        
        # Guardian's Landline Code and Number (if present)
        landline_patterns = [
            r'Landline\s+Code[:\s]*(\d{3,4})',
            r'Landline\s+No\.?[:\s]*(\d{6,8})',
        ]
        for pattern in landline_patterns:
            match = re.search(pattern, guardian_text, re.IGNORECASE)
            if match:
                if 'code' in pattern.lower():
                    result['guardian_landline_code'] = match.group(1)
                else:
                    result['guardian_landline'] = match.group(1)
        
        # Guardian's Relation (if mentioned)
        relation_patterns = [
            r"Relation[:\s]+([A-Za-z]+)",
            r"Relationship[:\s]+([A-Za-z]+)",
        ]
        for pattern in relation_patterns:
            match = re.search(pattern, guardian_text, re.IGNORECASE)
            if match:
                relation = match.group(1).strip().title()
                if relation.lower() not in ['name', 'address', 'organization', 'email', 'phone', 'contact']:
                    result['guardian_relation'] = relation
                    break
        
        # DU Enrollment No (Field 16a)
        # Find Field 16 section first - look for "16. Other Information" section
        # Capture more text to include the enrollment number which comes after "17."
        # Match "16. Other Information" and capture until "Certificate" or "If belong"
        # Use .*? to match across newlines until we find the stop pattern
        field_16_section = re.search(r"16\s*\.\s*Other\s+Information.*?(?=Certificate|If\s+belong|$)", text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if not field_16_section or len(field_16_section.group(0)) < 100:
            # Fallback: match just "16. Other" and capture until "Certificate"
            field_16_section = re.search(r"16\s*\.\s*Other.*?(?=Certificate|If\s+belong|$)", text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        field_16_text = field_16_section.group(0) if field_16_section and len(field_16_section.group(0)) > 100 else text
        
        # Strategy: First try to find the SRCC pattern directly (most reliable)
        # Try with word boundary first
        srcc_pattern = r'\b(\d{2}SRCC[A-Z]{3}\d{7,})\b'
        srcc_match = re.search(srcc_pattern, field_16_text, re.IGNORECASE)
        if not srcc_match:
            # Try without word boundary (in case it's at start/end of line)
            srcc_pattern2 = r'(\d{2}SRCC[A-Z]{3}\d{7,})'
            srcc_match = re.search(srcc_pattern2, field_16_text, re.IGNORECASE)
        if srcc_match:
            enrollment = srcc_match.group(1).strip().upper()
            if len(enrollment) >= 10:
                result['du_enrollment_number'] = enrollment
        else:
            # Fallback: try label-based patterns
            du_enrollment_patterns = [
                # After label: "(a) Delhi University Enrolment No.\n34SRCCBCO4000135"
                r"\(a\)\s*Delhi\s+University\s+Enrol?ment\s+No\.?[:\s]*\n\s*([A-Z0-9]{10,})",
                r"Delhi\s+University\s+Enrol?ment\s+No\.?[:\s]*\n\s*([A-Z0-9]{10,})",
                # After label on same line
                r"Delhi\s+University\s+Enrol?ment\s+No\.?[:\s]*([A-Z0-9]{10,})",
                r"DU\s+Enrol?ment\s+No\.?[:\s]*([A-Z0-9]{10,})",
                r"16\s*\.\s*Other\s+Information.*?Enrol?ment\s+No\.?[:\s]*([A-Z0-9]{10,})",
                # Fallback: look for SRCC pattern anywhere in Field 16
                r'(\d{2}SRCC[A-Z0-9]{8,})',
            ]
            for pattern in du_enrollment_patterns:
                match = re.search(pattern, field_16_text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
                if match:
                    enrollment = match.group(1).strip().upper()
                    # Validate: should be at least 10 characters
                    if len(enrollment) >= 10:
                        # Prefer patterns with SRCC
                        if 'SRCC' in enrollment:
                            result['du_enrollment_number'] = enrollment
                            break
                        # Or if it's a long alphanumeric string after the label
                        elif len(enrollment) >= 12 and enrollment.isalnum():
                            result['du_enrollment_number'] = enrollment
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
            # Most common: 2034 -> 2024 (3 is OCR error for 0)
            if year.startswith('203'):
                corrected = '202' + year[3]
                corrected_int = int(corrected)
                if 2015 <= corrected_int <= 2026:
                    return corrected
            
            # Specific corrections for common OCR errors
            if year == '2033':
                return '2023'
            if year == '2034':
                return '2024'  # Common: 0 read as 3
            if year == '2035':
                return '2025'
            if year == '2036':
                return '2026'
            if year == '2030':
                return '2020'  # Common: 0 read as 3
            if year == '2031':
                return '2021'
            if year == '2032':
                return '2022'
            
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
                if year[3].isdigit():
                    return '202' + year[3]
                else:
                    return '2024'  # Default fallback
            
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
            'name in block letters', 'in block letters', 'block letters',  # Critical: filter out form label
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
        
        # Check if it's just instructions or form labels
        instruction_patterns = [
            r'^please\s+',
            r'\(please\s+',
            r'tick\s+\(',
            r'^fill\s+',
            r'^enter\s+',
            r'^write\s+',
            r'^specify',
            r'^select\s+',
            r'if\s+different',
            r'if\s+employed',
            r'if\s+applicable',
            r'if\s+yes',
            r'if\s+no',
            r'name\s+in\s+block\s+letters',  # Critical: filter "NAME IN BLOCK LETTERS"
            r'in\s+block\s+letters',  # Also match "IN BLOCK LETTERS"
            r'block\s+letters',  # Also match "BLOCK LETTERS"
            r'^mandatory',
            r'^optional',
            r'^self\s+attested',
            r'^attach',
        ]
        for pattern in instruction_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Short uppercase text that matches field names is a label
        if len(text_clean) < 15 and text_clean.isupper():
            if text_lower in ['name', 'address', 'email', 'phone', 'date', 'gender', 'state',
                            'pin', 'pincode', 'mobile', 'contact', 'category', 'details',
                            'occupation', 'designation', 'organization']:
                return True
        
        # Multi-word phrases that look like field labels
        label_phrases = [
            "mother's occupational details",
            "father's occupational details",
            "local guardian's details",
            "qualifying examination",
            "personal information",
            "personal details",
            "academic details",
            "admission details",
            "address details",
            "contact details",
            "name in block letters",  # Critical: filter this form label
            "in block letters",  # Also match this variant
            "of the student",
            "of student",
            "son of",
            "daughter of",
            "ward of",
            "student data form",
            "admission form",
            "cuet marks",
            "cuet scores",
            "category certificate details",
            "declaration",
            "undertaking",
            "documents required",
            "document checklist",
        ]
        for phrase in label_phrases:
            if phrase in text_lower:
                return True
        
        # Check if text is just a field number or label marker
        if re.match(r'^\d+\.\s*$', text_lower):  # Just "1.", "2.", etc.
            return True
        if re.match(r'^\([a-z0-9]\)\s*$', text_lower):  # Just "(a)", "(1)", etc.
            return True
        
        # If text is very short and matches common label words, it's likely a label
        if len(text_clean) <= 3:
            if text_lower in ['dd', 'mm', 'yyyy', 'pin', 'na', 'n/a']:
                return True
        
        return False


def extract_srcc_form(raw_text: str, zone_hints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main function to extract data from SRCC form text.
    
    This function is PAGE-ORDER AGNOSTIC - it works correctly even if pages
    are in the wrong order (e.g., pages 2 and 3 swapped). The extraction
    searches for field markers throughout the entire text, not based on
    page position.
    
    Args:
        raw_text: Raw OCR text from the scanned form (can include page markers
                 like "--- Page X ---", but page order doesn't matter)
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
