"""
Field Mapper for Student Admission Forms

Maps OCR extracted text to structured form fields using pattern matching
and field labels. This helps train models to recognize field-value pairs.
"""
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class FieldMapping:
    """Represents a field mapping with label and value"""
    field_key: str
    label_patterns: List[str]  # Patterns that identify this field
    value_pattern: Optional[str] = None  # Pattern to extract value
    field_type: str = "text"  # text, date, number, email, phone


class StudentFormFieldMapper:
    """
    Maps OCR text to structured student form fields.
    Handles various label formats and extracts values.
    """
    
    def __init__(self):
        self.field_mappings = self._initialize_field_mappings()
    
    def _initialize_field_mappings(self) -> Dict[str, FieldMapping]:
        """Initialize all field mappings with label patterns"""
        mappings = {}
        
        # Academic & Admission Details
        mappings['academic_session'] = FieldMapping(
            'academic_session',
            ['academic session', 'session', 'academic year', 'session year'],
            field_type='text'
        )
        mappings['course'] = FieldMapping(
            'course',
            ['course', 'course applied', 'program', 'programme', 'b.com.(h)', 'b.a.(h) eco'],
            field_type='text'
        )
        mappings['admission_category'] = FieldMapping(
            'admission_category',
            ['admission category', 'category', 'admission cat', 'gen', 'obc', 'sc', 'st', 'sports', 'pwd', 'ews'],
            r'(gen|obc|sc|st|sports|pwd|ews|foreign|cw|km|others|eca)',
            'text'
        )
        mappings['admission_category_other'] = FieldMapping(
            'admission_category_other',
            ['other (specify)', 'other specify', 'admission category other'],
            field_type='text'
        )
        mappings['du_portal_form_number'] = FieldMapping(
            'du_portal_form_number',
            ['du portal form number', 'portal form number', 'du form number', 'form number'],
            field_type='text'
        )
        mappings['cuet_score'] = FieldMapping(
            'cuet_score',
            ['cuet score', 'cuet', 'common university entrance test score'],
            r'\d+',
            'number'
        )
        mappings['college_roll_no'] = FieldMapping(
            'college_roll_no',
            ['college roll no', 'college roll number', 'roll no', 'roll number'],
            field_type='text'
        )
        mappings['date_of_admission'] = FieldMapping(
            'date_of_admission',
            ['date of admission', 'admission date'],
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            'date'
        )
        
        # Name Fields (Separate)
        mappings['first_name'] = FieldMapping(
            'first_name',
            ['first name', 'name in block letters', 'given name'],
            field_type='text'
        )
        mappings['middle_name'] = FieldMapping(
            'middle_name',
            ['middle name', 'middle'],
            field_type='text'
        )
        mappings['surname'] = FieldMapping(
            'surname',
            ['surname', 'last name', 'family name'],
            field_type='text'
        )
        
        # Basic Details
        mappings['student_name'] = FieldMapping(
            'student_name',
            ['student name', 'name', 'applicant name', 'candidate name', 'full name', 'name of student', 'name in block letters'],
            field_type='text'
        )
        mappings['date_of_birth'] = FieldMapping(
            'date_of_birth',
            ['date of birth', 'dob', 'birth date', 'date of birth (dd/mm/yyyy)', 'birthday'],
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            'date'
        )
        mappings['gender'] = FieldMapping(
            'gender',
            ['gender', 'sex', 'male/female', 'gender {tick}', 'male', 'female', 'transgender'],
            r'(male|female|transgender|m|f|other)',
            'text'
        )
        mappings['category'] = FieldMapping(
            'category',
            ['category', 'caste category', 'reservation category', 'general/obc/sc/st'],
            r'(general|obc|sc|st|other)',
            'text'
        )
        mappings['nationality'] = FieldMapping(
            'nationality',
            ['nationality', 'citizenship'],
            field_type='text'
        )
        mappings['religion'] = FieldMapping(
            'religion',
            ['religion'],
            field_type='text'
        )
        mappings['aadhar_number'] = FieldMapping(
            'aadhar_number',
            ['aadhar', 'aadhaar', 'aadhar number', 'aadhaar number', 'uid'],
            r'\d{4}\s?\d{4}\s?\d{4}',
            'number'
        )
        mappings['blood_group'] = FieldMapping(
            'blood_group',
            ['blood group', 'blood type', 'blood'],
            r'(a|b|ab|o)[+-]',
            'text'
        )
        
        # Address Details
        mappings['permanent_address'] = FieldMapping(
            'permanent_address',
            ['permanent address', 'permanent addr', 'address', 'residential address'],
            field_type='text'
        )
        mappings['permanent_address_line1'] = FieldMapping(
            'permanent_address_line1',
            ['permanent address line 1', 'permanent address'],
            field_type='text'
        )
        mappings['permanent_address_line2'] = FieldMapping(
            'permanent_address_line2',
            ['permanent address line 2'],
            field_type='text'
        )
        mappings['permanent_address_line3'] = FieldMapping(
            'permanent_address_line3',
            ['permanent address line 3'],
            field_type='text'
        )
        mappings['permanent_state'] = FieldMapping(
            'permanent_state',
            ['permanent state', 'state (permanent)'],
            field_type='text'
        )
        mappings['permanent_pincode'] = FieldMapping(
            'permanent_pincode',
            ['permanent pin', 'permanent pincode', 'pin (permanent)'],
            r'\d{6}',
            'number'
        )
        mappings['correspondence_address'] = FieldMapping(
            'correspondence_address',
            ['correspondence address', 'correspondence addr', 'mailing address', 'current address', 'local address for correspondence'],
            field_type='text'
        )
        mappings['correspondence_address_line1'] = FieldMapping(
            'correspondence_address_line1',
            ['correspondence address line 1', 'local address line 1'],
            field_type='text'
        )
        mappings['correspondence_address_line2'] = FieldMapping(
            'correspondence_address_line2',
            ['correspondence address line 2', 'local address line 2'],
            field_type='text'
        )
        mappings['correspondence_address_line3'] = FieldMapping(
            'correspondence_address_line3',
            ['correspondence address line 3', 'local address line 3'],
            field_type='text'
        )
        mappings['correspondence_state'] = FieldMapping(
            'correspondence_state',
            ['correspondence state', 'state (correspondence)', 'local state'],
            field_type='text'
        )
        mappings['correspondence_pincode'] = FieldMapping(
            'correspondence_pincode',
            ['correspondence pin', 'correspondence pincode', 'pin (correspondence)', 'local pin'],
            r'\d{6}',
            'number'
        )
        mappings['city'] = FieldMapping(
            'city',
            ['city', 'town'],
            field_type='text'
        )
        mappings['state'] = FieldMapping(
            'state',
            ['state', 'province'],
            field_type='text'
        )
        mappings['pincode'] = FieldMapping(
            'pincode',
            ['pincode', 'pin code', 'pin', 'postal code', 'zip code'],
            r'\d{6}',
            'number'
        )
        
        # Contact Details
        mappings['phone_number'] = FieldMapping(
            'phone_number',
            ['phone', 'phone number', 'mobile', 'mobile number', 'contact number', 'tel'],
            r'[\d\s-]{10,}',
            'phone'
        )
        mappings['alternate_phone'] = FieldMapping(
            'alternate_phone',
            ['alternate phone', 'alternate mobile', 'secondary phone', 'other phone'],
            r'[\d\s-]{10,}',
            'phone'
        )
        mappings['email'] = FieldMapping(
            'email',
            ['email', 'e-mail', 'email address', 'email id'],
            r'[\w\.-]+@[\w\.-]+\.\w+',
            'email'
        )
        mappings['emergency_contact_name'] = FieldMapping(
            'emergency_contact_name',
            ['emergency contact', 'emergency contact name', 'contact person'],
            field_type='text'
        )
        mappings['emergency_contact_phone'] = FieldMapping(
            'emergency_contact_phone',
            ['emergency phone', 'emergency contact phone', 'emergency mobile'],
            r'[\d\s-]{10,}',
            'phone'
        )
        
        # Parent/Guardian Details
        mappings['father_name'] = FieldMapping(
            'father_name',
            ['father name', 'father\'s name', 'fathers name', 'father', 'name of father'],
            field_type='text'
        )
        mappings['father_occupation'] = FieldMapping(
            'father_occupation',
            ['father occupation', 'father\'s occupation', 'fathers occupation', 'father profession', 'father\'s occupational details'],
            field_type='text'
        )
        mappings['father_designation'] = FieldMapping(
            'father_designation',
            ['father designation', 'father\'s designation', 'designation (if employed)', 'father\'s designation if employed'],
            field_type='text'
        )
        mappings['father_organization'] = FieldMapping(
            'father_organization',
            ['father organization', 'father\'s organization', 'organization & address', 'father organization & address'],
            field_type='text'
        )
        mappings['father_email'] = FieldMapping(
            'father_email',
            ['father email', 'father\'s email', 'father e-mail'],
            r'[\w\.-]+@[\w\.-]+\.\w+',
            'email'
        )
        mappings['father_mobile'] = FieldMapping(
            'father_mobile',
            ['father mobile', 'father\'s mobile', 'father mobile no', 'mobile no (father)'],
            r'\d{10}',
            'phone'
        )
        mappings['father_landline_code'] = FieldMapping(
            'father_landline_code',
            ['father landline code', 'father\'s landline code', 'code (father)'],
            r'\d{3}',
            'number'
        )
        mappings['father_landline'] = FieldMapping(
            'father_landline',
            ['father landline', 'father\'s landline', 'father landline no', 'landline no (father)'],
            r'\d{8}',
            'phone'
        )
        mappings['father_phone'] = FieldMapping(
            'father_phone',
            ['father phone', 'father\'s phone', 'fathers phone', 'father mobile', 'father contact', 'father contact number'],
            r'[\d\s-]{10,}',
            'phone'
        )
        mappings['mother_name'] = FieldMapping(
            'mother_name',
            ['mother name', 'mother\'s name', 'mothers name', 'mother', 'name of mother'],
            field_type='text'
        )
        mappings['mother_occupation'] = FieldMapping(
            'mother_occupation',
            ['mother occupation', 'mother\'s occupation', 'mothers occupation', 'mother profession', 'mother\'s occupational details'],
            field_type='text'
        )
        mappings['mother_designation'] = FieldMapping(
            'mother_designation',
            ['mother designation', 'mother\'s designation', 'designation (if employed)', 'mother\'s designation if employed'],
            field_type='text'
        )
        mappings['mother_organization'] = FieldMapping(
            'mother_organization',
            ['mother organization', 'mother\'s organization', 'organization & address', 'mother organization & address'],
            field_type='text'
        )
        mappings['mother_email'] = FieldMapping(
            'mother_email',
            ['mother email', 'mother\'s email', 'mother e-mail'],
            r'[\w\.-]+@[\w\.-]+\.\w+',
            'email'
        )
        mappings['mother_mobile'] = FieldMapping(
            'mother_mobile',
            ['mother mobile', 'mother\'s mobile', 'mother mobile no', 'mobile no (mother)'],
            r'\d{10}',
            'phone'
        )
        mappings['mother_landline_code'] = FieldMapping(
            'mother_landline_code',
            ['mother landline code', 'mother\'s landline code', 'code (mother)'],
            r'\d{3}',
            'number'
        )
        mappings['mother_landline'] = FieldMapping(
            'mother_landline',
            ['mother landline', 'mother\'s landline', 'mother landline no', 'landline no (mother)'],
            r'\d{8}',
            'phone'
        )
        mappings['mother_phone'] = FieldMapping(
            'mother_phone',
            ['mother phone', 'mother\'s phone', 'mothers phone', 'mother mobile', 'mother contact', 'mother contact number'],
            r'[\d\s-]{10,}',
            'phone'
        )
        mappings['guardian_name'] = FieldMapping(
            'guardian_name',
            ['guardian name', 'guardian\'s name', 'guardians name', 'guardian', 'local guardian', 'local guardian\'s name', 'local guardian name'],
            field_type='text'
        )
        mappings['guardian_relation'] = FieldMapping(
            'guardian_relation',
            ['guardian relation', 'guardian\'s relation', 'relation with guardian', 'relationship'],
            field_type='text'
        )
        mappings['guardian_residential_address'] = FieldMapping(
            'guardian_residential_address',
            ['guardian residential address', 'local guardian residential address', 'guardian address'],
            field_type='text'
        )
        mappings['guardian_organization'] = FieldMapping(
            'guardian_organization',
            ['guardian organization', 'local guardian organization', 'organization & address (guardian)'],
            field_type='text'
        )
        mappings['guardian_email'] = FieldMapping(
            'guardian_email',
            ['guardian email', 'local guardian email', 'guardian e-mail'],
            r'[\w\.-]+@[\w\.-]+\.\w+',
            'email'
        )
        mappings['guardian_mobile'] = FieldMapping(
            'guardian_mobile',
            ['guardian mobile', 'local guardian mobile', 'guardian mobile no', 'mobile no (guardian)'],
            r'\d{10}',
            'phone'
        )
        mappings['guardian_landline_code'] = FieldMapping(
            'guardian_landline_code',
            ['guardian landline code', 'local guardian landline code', 'code (guardian)'],
            r'\d{3}',
            'number'
        )
        mappings['guardian_landline'] = FieldMapping(
            'guardian_landline',
            ['guardian landline', 'local guardian landline', 'guardian landline no', 'landline no (guardian)'],
            r'\d{8}',
            'phone'
        )
        mappings['guardian_phone'] = FieldMapping(
            'guardian_phone',
            ['guardian phone', 'guardian\'s phone', 'guardians phone', 'guardian mobile', 'local guardian contact number'],
            r'[\d\s-]{10,}',
            'phone'
        )
        mappings['annual_income'] = FieldMapping(
            'annual_income',
            ['annual income', 'family income', 'parent income', 'household income'],
            r'[\d,]+',
            'number'
        )
        
        # Educational Qualifications
        mappings['tenth_board'] = FieldMapping(
            'tenth_board',
            ['10th board', 'tenth board', '10 board', 'class 10 board', 'ssc board'],
            field_type='text'
        )
        mappings['tenth_year'] = FieldMapping(
            'tenth_year',
            ['10th year', 'tenth year', '10 year', 'class 10 year', 'ssc year'],
            r'\d{4}',
            'number'
        )
        mappings['tenth_percentage'] = FieldMapping(
            'tenth_percentage',
            ['10th percentage', 'tenth percentage', '10 percentage', 'class 10 percentage', 'ssc percentage', '10th %'],
            r'\d+\.?\d*%?',
            'number'
        )
        mappings['tenth_school'] = FieldMapping(
            'tenth_school',
            ['10th school', 'tenth school', '10 school', 'class 10 school', 'ssc school', '10th school name'],
            field_type='text'
        )
        mappings['twelfth_board'] = FieldMapping(
            'twelfth_board',
            ['12th board', 'twelfth board', '12 board', 'class 12 board', 'hsc board', 'board / university', 'qualifying examination board'],
            field_type='text'
        )
        mappings['twelfth_year'] = FieldMapping(
            'twelfth_year',
            ['12th year', 'twelfth year', '12 year', 'class 12 year', 'hsc year', 'year of passing', 'qualifying examination year'],
            r'\d{4}',
            'number'
        )
        mappings['twelfth_roll_number'] = FieldMapping(
            'twelfth_roll_number',
            ['12th roll number', 'twelfth roll number', 'examination roll no', 'roll number', 'qualifying examination roll no'],
            field_type='text'
        )
        mappings['twelfth_institution'] = FieldMapping(
            'twelfth_institution',
            ['12th institution', 'twelfth institution', 'institution last attended', 'last institution', 'qualifying examination institution'],
            field_type='text'
        )
        mappings['hindi_studied_upto'] = FieldMapping(
            'hindi_studied_upto',
            ['hindi studied upto', 'hindi studied up to', 'hindi studied', 'hindi upto viii/x/xii/never'],
            r'(viii|x|xi|xii|never|class viii|class x|class xii)',
            'text'
        )
        mappings['twelfth_percentage'] = FieldMapping(
            'twelfth_percentage',
            ['12th percentage', 'twelfth percentage', '12 percentage', 'class 12 percentage', 'hsc percentage', '12th %'],
            r'\d+\.?\d*%?',
            'number'
        )
        mappings['twelfth_school'] = FieldMapping(
            'twelfth_school',
            ['12th school', 'twelfth school', '12 school', 'class 12 school', 'hsc school', '12th school name'],
            field_type='text'
        )
        mappings['previous_qualification'] = FieldMapping(
            'previous_qualification',
            ['previous qualification', 'qualification', 'educational qualification', 'degree'],
            field_type='text'
        )
        mappings['graduation_details'] = FieldMapping(
            'graduation_details',
            ['graduation', 'graduation details', 'degree details', 'college', 'university'],
            field_type='text'
        )
        
        # Course Application Details
        mappings['course_applied'] = FieldMapping(
            'course_applied',
            ['course applied', 'course', 'applied course', 'program', 'programme'],
            field_type='text'
        )
        mappings['application_number'] = FieldMapping(
            'application_number',
            ['application number', 'application no', 'app no', 'application id'],
            field_type='text'
        )
        mappings['enrollment_number'] = FieldMapping(
            'enrollment_number',
            ['enrollment number', 'enrollment no', 'enrolment number', 'enroll no', 'enrollment id'],
            field_type='text'
        )
        mappings['admission_date'] = FieldMapping(
            'admission_date',
            ['admission date', 'date of admission', 'admission'],
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            'date'
        )
        
        # CUET Marks Table
        for i in range(1, 7):
            mappings[f'cuet_subject_{i}'] = FieldMapping(
                f'cuet_subject_{i}',
                [f'cuet subject {i}', f'subject {i}', 'subjects'],
                field_type='text'
            )
            mappings[f'cuet_total_score_{i}'] = FieldMapping(
                f'cuet_total_score_{i}',
                [f'cuet total score {i}', f'total score {i}', 'total score'],
                r'\d+',
                'number'
            )
            mappings[f'cuet_score_obtained_{i}'] = FieldMapping(
                f'cuet_score_obtained_{i}',
                [f'cuet score obtained {i}', f'score obtained {i}', 'score obtained'],
                r'\d+',
                'number'
            )
        mappings['cuet_total_score'] = FieldMapping(
            'cuet_total_score',
            ['total cuet score obtained', 'total cuet score', 'total score obtained'],
            r'\d+',
            'number'
        )
        
        # Additional Personal Information
        mappings['below_poverty_line'] = FieldMapping(
            'below_poverty_line',
            ['whether below poverty line', 'below poverty line', 'bpl'],
            r'(yes|no|y|n)',
            'text'
        )
        mappings['minority_category'] = FieldMapping(
            'minority_category',
            ['whether belongs to minority', 'minority', 'minority category', 'muslim', 'jain', 'sikh', 'persian', 'christian', 'buddhists'],
            r'(muslim|jain|sikh|persian|christian|buddhists|others)',
            'text'
        )
        
        # Other Information
        mappings['du_enrollment_number'] = FieldMapping(
            'du_enrollment_number',
            ['delhi university enrolment no', 'du enrolment no', 'du enrollment number', 'enrolment no'],
            field_type='text'
        )
        mappings['hindi_medium_preference'] = FieldMapping(
            'hindi_medium_preference',
            ['would you like to be taught in hindi medium', 'hindi medium', 'hindi medium preference'],
            r'(yes|no|y|n)',
            'text'
        )
        
        # Category Certificate Details
        mappings['category_certificate_authority'] = FieldMapping(
            'category_certificate_authority',
            ['name & address of certificate issuing authority', 'certificate issuing authority', 'certificate authority'],
            field_type='text'
        )
        mappings['category_certificate_number'] = FieldMapping(
            'category_certificate_number',
            ['certificate no', 'certificate number', 'category certificate no'],
            field_type='text'
        )
        mappings['category_certificate_date'] = FieldMapping(
            'category_certificate_date',
            ['date of issue', 'certificate date of issue', 'certificate date'],
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            'date'
        )
        mappings['disability_percentage'] = FieldMapping(
            'disability_percentage',
            ['if pwbd, extent of disability', 'disability percentage', 'extent of disability', 'disability %'],
            r'\d+%?',
            'number'
        )
        mappings['disability_type'] = FieldMapping(
            'disability_type',
            ['type of disability', 'disability type', 'vh/hh/oh'],
            r'(vh|hh|oh|visual|hearing|orthopedic)',
            'text'
        )
        mappings['udid_number'] = FieldMapping(
            'udid_number',
            ['udid no', 'udid number', 'unique disability id'],
            field_type='text'
        )
        
        # Declaration Fields
        mappings['student_declaration_name'] = FieldMapping(
            'student_declaration_name',
            ['declaration by the student', 'student declaration name', 'i,', 'student full name declaration'],
            field_type='text'
        )
        mappings['student_declaration_date'] = FieldMapping(
            'student_declaration_date',
            ['date (student)', 'student declaration date'],
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            'date'
        )
        mappings['student_declaration_place'] = FieldMapping(
            'student_declaration_place',
            ['place (student)', 'student declaration place'],
            field_type='text'
        )
        mappings['parent_guardian_name'] = FieldMapping(
            'parent_guardian_name',
            ['declaration by parent', 'parent guardian name', 'father / mother / guardian of'],
            field_type='text'
        )
        mappings['parent_guardian_relationship'] = FieldMapping(
            'parent_guardian_relationship',
            ['relationship', 'father / mother / guardian', 'parent guardian relationship'],
            r'(father|mother|guardian)',
            'text'
        )
        mappings['parent_guardian_candidate_name'] = FieldMapping(
            'parent_guardian_candidate_name',
            ['name of candidate', 'candidate name (by parent)', 'parent guardian candidate name'],
            field_type='text'
        )
        mappings['parent_guardian_course'] = FieldMapping(
            'parent_guardian_course',
            ['bachelor with honours in', 'bachelor program', 'parent guardian course'],
            field_type='text'
        )
        mappings['parent_guardian_date'] = FieldMapping(
            'parent_guardian_date',
            ['date (parent/guardian)', 'parent guardian date'],
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            'date'
        )
        mappings['parent_guardian_place'] = FieldMapping(
            'parent_guardian_place',
            ['place (parent/guardian)', 'parent guardian place'],
            field_type='text'
        )
        
        # Document Checklist (Boolean fields)
        document_fields = [
            'printed_admission_form', 'anti_ragging_undertaking', 'photographs_pasted',
            'cuet_score_card', 'twelfth_mark_sheet', 'tenth_certificate', 'twelfth_certificate',
            'character_certificate', 'transfer_certificate', 'migration_certificate',
            'hindi_exemption_certificate', 'caste_category_certificate', 'sports_eca_certificates',
            'original_certificates', 'photo_id_proofs'
        ]
        
        document_labels = [
            'printed admission/registration form', 'undertakings for curbing ragging', 'photographs pasted',
            'cuet score card', 'detailed mark sheet of class xii', 'certificate and mark sheet of class x',
            'provisional / original certificate of class xii', 'recent character certificate',
            'transfer certificate', 'migration certificate', 'certificate from head of school',
            'caste/category certificate', 'all relevant certificates', 'all certificates in original',
            'photo id proof'
        ]
        
        for field, label in zip(document_fields, document_labels):
            mappings[field] = FieldMapping(
                field,
                [label, label.replace('/', ' '), label.replace('&', 'and')],
                r'(yes|no|tick|checked|attached)',
                'boolean'
            )
        
        return mappings
    
    def extract_field_value(self, text: str, field_key: str) -> Optional[str]:
        """
        Extract value for a specific field from text.
        
        Args:
            text: OCR extracted text
            field_key: Field key to extract
            
        Returns:
            Extracted value or None
        """
        if field_key not in self.field_mappings:
            return None
        
        mapping = self.field_mappings[field_key]
        text_lower = text.lower()
        
        # Search for label patterns
        for label_pattern in mapping.label_patterns:
            # Create regex pattern to find label and value
            pattern = rf'{re.escape(label_pattern)}[:\s]+([^\n]+)'
            match = re.search(pattern, text_lower, re.IGNORECASE)
            
            if match:
                value = match.group(1).strip()
                
                # Apply value pattern if specified
                if mapping.value_pattern:
                    value_match = re.search(mapping.value_pattern, value, re.IGNORECASE)
                    if value_match:
                        value = value_match.group(0)
                
                # Clean up value
                value = re.sub(r'^[:\-\s]+', '', value)  # Remove leading separators
                value = re.sub(r'[:\-\s]+$', '', value)  # Remove trailing separators
                
                if value:
                    return value
        
        return None
    
    def extract_all_fields(self, text: str) -> Dict[str, Any]:
        """
        Extract all fields from OCR text.
        
        Args:
            text: OCR extracted text
            
        Returns:
            Dictionary with field keys and extracted values
        """
        extracted = {}
        
        for field_key in self.field_mappings.keys():
            value = self.extract_field_value(text, field_key)
            if value:
                extracted[field_key] = value
        
        return extracted
    
    def create_training_example(self, text: str, verified_fields: Dict[str, str]) -> Dict[str, Any]:
        """
        Create a training example with field mappings.
        
        Args:
            text: OCR extracted text
            verified_fields: Verified field values from database
            
        Returns:
            Training example with text and field mappings
        """
        # Extract fields from text
        extracted_fields = self.extract_all_fields(text)
        
        # Create field mappings (label -> value pairs)
        field_mappings = []
        for field_key, verified_value in verified_fields.items():
            if field_key in self.field_mappings:
                mapping = self.field_mappings[field_key]
                # Find which label pattern matched
                matched_label = None
                for label_pattern in mapping.label_patterns:
                    pattern = rf'{re.escape(label_pattern)}[:\s]+'
                    if re.search(pattern, text.lower(), re.IGNORECASE):
                        matched_label = label_pattern
                        break
                
                field_mappings.append({
                    'field_key': field_key,
                    'label': matched_label or mapping.label_patterns[0],
                    'value': verified_value,
                    'extracted_value': extracted_fields.get(field_key),
                    'field_type': mapping.field_type
                })
        
        return {
            'text': text,
            'verified_fields': verified_fields,
            'extracted_fields': extracted_fields,
            'field_mappings': field_mappings
        }


# Global instance
field_mapper = StudentFormFieldMapper()
