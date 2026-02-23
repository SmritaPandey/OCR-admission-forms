"""
Comprehensive Form Labels - Garbage Collector for OCR Extraction

This module contains all static text from the SRCC Student Data Form that should
be filtered out during OCR extraction. Any text matching these patterns should
NOT be extracted as field values.

Based on analysis of the empty form template PDF.
"""

# ==============================================================================
# HEADER SECTION - College and Form Title
# ==============================================================================
HEADER_LABELS = {
    # College name
    'shri ram college of commerce',
    'shri ram college',
    'srcc',
    'university of delhi',
    'delhi university',
    
    # Form title
    "students' data form",
    "student's data form",
    'students data form',
    'student data form',
    'data form',
    
    # Photo area
    'photo',
    'paste',
    'paste here',
    'paste photograph',
    'affix photo',
    'affix photograph',
    'passport size photo',
    'passport size photograph',
    'recent passport',
    
    # Session and course headers
    'academic session',
    'session',
    'course (please tick)',
    'course please tick',
    'category (please tick)',
    'category please tick',
    'please tick',
    'tick',
    '(please tick)',
}

# ==============================================================================
# COURSE AND CATEGORY OPTIONS (as labels, not values when standalone)
# ==============================================================================
COURSE_CATEGORY_LABELS = {
    # Courses (these are valid values when extracted correctly, but not as standalone labels)
    'b.com.(h)',
    'b.com(h)',
    'bcom h',
    'b.a.(h) eco',
    'b.a.(h)eco',
    'ba h eco',
    'economics',
    
    # Categories (valid values when ticked, labels when not)
    'gen',
    'general',
    'obc',
    'sc',
    'st',
    'pwd',
    'pwbd',
    'sports',
    'ews',
    'foreign',
    'cw',
    'km',
    'others',
    'eca',
    'person with disability',
    'persons with disability',
    'economically weaker section',
    'other backward class',
    'scheduled caste',
    'scheduled tribe',
}

# ==============================================================================
# FORM NUMBER SECTION
# ==============================================================================
FORM_NUMBER_LABELS = {
    'du portal form number',
    'du form number',
    'portal form number',
    'form number',
    'application number',
    'cuet score',
    'total cuet score',
    'college roll no',
    'college roll no.',
    'roll no',
    'roll no.',
    'roll number',
    'date of admission',
    'admission date',
    'doa',
}

# ==============================================================================
# STUDENT DETAILS SECTION (Page 1 - Fields 1-10)
# ==============================================================================
STUDENT_DETAILS_LABELS = {
    # Name field
    '1. name in block letters',
    'name in block letters',
    'in block letters',
    'block letters',
    'first name',
    'middle name',
    'surname',
    'last name',
    'name of the student',
    'name of student',
    'student name',
    'applicant name',
    'candidate name',
    'full name',
    'name',
    
    # Date of Birth
    '2. date of birth',
    'date of birth',
    'dob',
    'd.o.b',
    'd.o.b.',
    'birth date',
    'date of birth (dd/mm/yyyy)',
    
    # Gender/Sex
    '3. sex (tick)',
    'sex (tick)',
    'sex',
    'gender',
    'male',
    'female',
    'transgender',
    'm/f/t',
    'male/female/transgender',
    
    # Permanent Address
    '4. permanent address',
    'permanent address',
    'permanent addr',
    'perm address',
    'home address',
    'residential address',
    
    # State and PIN
    'state',
    'pin',
    'pincode',
    'pin code',
    'postal code',
    
    # Correspondence Address
    '5. local address for correspondence',
    'local address for correspondence',
    'correspondence address',
    'local address',
    'mailing address',
    'current address',
    'if different from permanent address',
    'if different from',
    'different from permanent',
    
    # Email
    '6. email',
    'email',
    'e-mail',
    'email id',
    'email address',
    'e mail',
    
    # Contact Numbers
    '7. contact numbers',
    'contact numbers',
    'contact number',
    'phone number',
    'mobile number',
    'phone',
    'mobile',
    'contact',
    'contact no',
    'phone no',
    'mobile no',
    'tel',
    'telephone',
    'emergency contact name',
    'emergency contact phone',
    
    # Parent Names
    "8. mother's name",
    "mother's name",
    'mother name',
    'name of mother',
    'mother',
    "9. father's name",
    "father's name",
    'father name',
    'name of father',
    'father',
    
    # CUET Details Table
    '10. details of marks obtained in qualifying examination: [cuet]',
    'details of marks obtained in qualifying examination',
    'details of marks obtained',
    'qualifying examination',
    'cuet',
    'subject',
    'subjects',
    'total marks',
    'score obtained',
    'marks obtained',
    'total score',
    'obtained',
    'maximum',
    'max',
}

# ==============================================================================
# CUET TABLE HEADERS AND LABELS
# ==============================================================================
CUET_TABLE_LABELS = {
    # Row labels
    '(i)',
    '(ii)',
    '(iii)',
    '(iv)',
    '(v)',
    '(vi)',
    'vii-total',
    'vii total',
    'total',
    'grand total',
    
    # Roman numerals
    'i',
    'ii',
    'iii',
    'iv',
    'v',
    'vi',
    'vii',
    'viii',
    'ix',
    'x',
    
    # Column headers
    'subject name',
    'subject code',
    'total marks',
    'marks obtained',
    'score obtained',
    'percentile',
}

# ==============================================================================
# CLASS XII DETAILS SECTION (Page 2 - Field 11)
# ==============================================================================
CLASS_XII_LABELS = {
    '11. details of qualifying examination passed (class xii)',
    'details of qualifying examination passed',
    'qualifying examination passed',
    'class xii',
    'class 12',
    'twelfth',
    '12th',
    
    '(a) year of passing',
    'year of passing',
    'passing year',
    
    '(b) board / university',
    'board / university',
    'board/university',
    'board',
    'university',
    
    '(c) examination roll no.',
    '(c) examination roll no',
    'examination roll no',
    'exam roll no',
    'board roll no',
    
    '(d) name of institution last attended',
    'name of institution last attended',
    'institution last attended',
    'institution',
    'school',
    'last school',
    'school name',
    
    '(e) hindi studied upto (tick)',
    'hindi studied upto (tick)',
    'hindi studied upto',
    'hindi studied',
    'hindi upto',
    'viii/x/xii/never',
    'never',
}

# ==============================================================================
# PERSONAL INFORMATION SECTION (Page 2 - Field 12)
# ==============================================================================
PERSONAL_INFO_LABELS = {
    '12. personal information',
    'personal information',
    'personal details',
    
    '(a) nationality',
    'nationality',
    'nation',
    'citizenship',
    
    '(b) religion',
    'religion',
    'faith',
    
    '(c) blood group',
    'blood group',
    'blood type',
    'bg',
    
    '(d) whether belongs to below poverty line',
    'whether belongs to below poverty line',
    'below poverty line',
    'bpl',
    
    '(e) parent\'s / family annual income',
    "parent's / family annual income",
    "parents' / family annual income",
    'parent\'s/family annual income',
    'family annual income',
    'annual income',
    'income',
    
    '(f) whether under minority category',
    'whether under minority category',
    'minority category',
    'minority',
    
    # Yes/No options
    'yes',
    'no',
}

# ==============================================================================
# PARENT OCCUPATIONAL DETAILS (Page 2 - Fields 13-14)
# ==============================================================================
PARENT_OCCUPATION_LABELS = {
    "13. mother's occupational details",
    "mother's occupational details",
    "14. father's occupational details",
    "father's occupational details",
    'occupational details',
    
    '(a) occupation',
    'occupation',
    
    '(b) designation',
    'designation',
    
    '(c) organization & address',
    'organization & address',
    'organization and address',
    'organization',
    'org address',
    
    '(d) email',
    '(e) mobile no.',
    'mobile no.',
    'mobile no',
    
    '(f) landline',
    'landline',
    'std code',
    'landline code',
}

# ==============================================================================
# GUARDIAN DETAILS (Page 2 - Field 15)
# ==============================================================================
GUARDIAN_LABELS = {
    "15. local guardian's details",
    "local guardian's details",
    'local guardian details',
    'guardian details',
    'guardian',
    'local guardian',
    
    "(a) name",
    "(b) residential address",
    'residential address',
    "(c) organization & address",
    "(d) email",
    "(e) mobile no.",
    "(f) landline",
    "(g) relation with student",
    'relation with student',
    'relation',
}

# ==============================================================================
# OTHER INFORMATION (Page 2 - Fields 16-17)
# ==============================================================================
OTHER_INFO_LABELS = {
    '16. other information',
    'other information',
    
    '(a) delhi university enrollment no.',
    'delhi university enrollment no.',
    'delhi university enrollment no',
    'du enrollment no',
    'du enrollment number',
    'enrollment no',
    'enrollment number',
    'enrolment no',
    'enrolment number',
    
    '(b) preference for hindi medium (tick)',
    'preference for hindi medium',
    'hindi medium preference',
    'hindi medium',
    
    '17. if you belong to ews/sc/st/obc/pwbd category',
    'if you belong to ews/sc/st/obc/pwbd category',
    'ews/sc/st/obc/pwbd',
    'certificate issuing authority',
    'issuing authority',
    'certificate no.',
    'certificate no',
    'certificate number',
    'date of issue',
    
    'if pwbd',
    'disability %',
    'disability percentage',
    'disability',
    'vh',
    'hh',
    'oh',
    'visually handicapped',
    'hearing handicapped',
    'orthopedically handicapped',
    'udid no.',
    'udid no',
    'udid number',
}

# ==============================================================================
# DOCUMENT CHECKLIST (Page 3)
# ==============================================================================
DOCUMENT_LABELS = {
    'list of documents required',
    'documents required',
    'document checklist',
    'checklist',
    
    '1. printed admission/registration form',
    'printed admission/registration form',
    'admission/registration form',
    'registration form',
    
    '2. undertakings for curbing ragging',
    'undertakings for curbing ragging',
    'undertaking for ragging',
    'anti-ragging',
    'anti ragging',
    
    '3. photographs',
    'photographs',
    'photograph',
    'photos',
    'pasted',
    
    'one set of self attested copies',
    'self attested copies',
    'self attested',
    
    '(i) cuet score card',
    'cuet score card',
    'cuet scorecard',
    
    '(ii) detailed mark sheet of class xii',
    'detailed mark sheet of class xii',
    'mark sheet of class xii',
    'marksheet class xii',
    'xii marksheet',
    
    '(iii) certificate and mark sheet of class x',
    'certificate and mark sheet of class x',
    'mark sheet of class x',
    'class x certificate',
    
    '(iv) provisional/original certificate of class xii',
    'provisional/original certificate of class xii',
    'provisional certificate',
    'original certificate',
    
    '(v) recent character certificate',
    'recent character certificate',
    'character certificate',
    
    '(vi) transfer/migration certificate',
    'transfer/migration certificate',
    'transfer certificate',
    'migration certificate',
    'tc',
    
    '(vii) certificate from the head of school',
    'certificate from the head of school',
    'head of school',
    
    '(viii) caste/category certificate',
    'caste/category certificate',
    'caste certificate',
    'category certificate',
    
    '(ix) all relevant certificates (only for sports/eca)',
    'all relevant certificates',
    'sports/eca',
    
    '5. all certificates in original',
    'all certificates in original',
    'certificates in original',
    'original documents',
    
    '6. any photo id proof',
    'any photo id proof',
    'photo id proof',
    'id proof',
}

# ==============================================================================
# DECLARATION SECTION (Page 4)
# ==============================================================================
DECLARATION_LABELS = {
    'declaration',
    'undertaking',
    
    'i hereby declare',
    'hereby declare',
    'i certify',
    'certify that',
    'certify',
    'particulars',
    'information given',
    'true and correct',
    'true',
    'correct',
    'to the best of my knowledge',
    'knowledge and belief',
    'knowledge',
    'belief',
    
    'signature of student',
    'signature of parent/guardian',
    'signature of parent',
    'signature of guardian',
    'signature',
    'sign',
    
    'date',
    'place',
    'dated',
}

# ==============================================================================
# COMMON OCR ARTIFACTS AND NOISE
# ==============================================================================
OCR_ARTIFACTS = {
    # Date placeholders
    'd d',
    'm m',
    'y y y y',
    'dd',
    'mm',
    'yyyy',
    'yy',
    'dd/mm/yyyy',
    'dd-mm-yyyy',
    
    # Number prefixes
    '1.',
    '2.',
    '3.',
    '4.',
    '5.',
    '6.',
    '7.',
    '8.',
    '9.',
    '10.',
    '11.',
    '12.',
    '13.',
    '14.',
    '15.',
    '16.',
    '17.',
    
    # Parenthetical markers
    '(a)',
    '(b)',
    '(c)',
    '(d)',
    '(e)',
    '(f)',
    '(g)',
    '(h)',
    
    # Tick marks and symbols
    '✓',
    '✔',
    '☑',
    '☒',
    '√',
    '✗',
    '×',
    '[x]',
    '[X]',
    '(v)',
    '(✓)',
    '(x)',
    
    # Common noise words
    'please',
    'fill',
    'enter',
    'write',
    'select',
    'specify',
    'applicable',
    'mandatory',
    'optional',
    'required',
    'attach',
    'attested',
    
    # Form instructions
    'if applicable',
    'if yes',
    'if no',
    'if different',
    'if employed',
    'self employed',
    'self-employed',
    
    # Section markers
    'sl no',
    'sl. no',
    's.no',
    's. no',
    'serial number',
    'serial no',
}

# ==============================================================================
# ADDRESS WORDS (to distinguish from names)
# ==============================================================================
ADDRESS_WORDS = {
    # Common address suffixes
    'vihar',
    'nagar',
    'colony',
    'enclave',
    'park',
    'garden',
    'gardens',
    'road',
    'street',
    'lane',
    'gali',
    'mohalla',
    'sector',
    'block',
    'phase',
    'extension',
    'extn',
    'apartment',
    'apartments',
    'flat',
    'flats',
    'floor',
    'house',
    'plot',
    'building',
    'tower',
    'complex',
    'society',
    'pocket',
    'area',
    'locality',
    'district',
    'tehsil',
    'taluka',
    'post',
    'p.o.',
    'p.o',
    
    # Common Delhi areas
    'vivek',  # part of Vivek Vihar
    'ashok',  # part of Ashok Vihar
    'pitampura',
    'rohini',
    'dwarka',
    'janakpuri',
    'paschim',
    'uttam',
    'saket',
    'vasant',
    'kunj',
    'karol',
    'bagh',
    'puri',
    
    # Other address words
    'near',
    'behind',
    'opposite',
    'opp',
    'beside',
    'adjacent',
    'main',
    'new',
    'old',
    'east',
    'west',
    'north',
    'south',
}

# ==============================================================================
# COMBINED SETS FOR CONVENIENCE
# ==============================================================================

# All form labels (for strict filtering)
ALL_FORM_LABELS = (
    HEADER_LABELS |
    FORM_NUMBER_LABELS |
    STUDENT_DETAILS_LABELS |
    CUET_TABLE_LABELS |
    CLASS_XII_LABELS |
    PERSONAL_INFO_LABELS |
    PARENT_OCCUPATION_LABELS |
    GUARDIAN_LABELS |
    OTHER_INFO_LABELS |
    DOCUMENT_LABELS |
    DECLARATION_LABELS |
    OCR_ARTIFACTS
)

# Labels that should never appear as name values
NAME_REJECT_LABELS = (
    HEADER_LABELS |
    FORM_NUMBER_LABELS |
    STUDENT_DETAILS_LABELS |
    OCR_ARTIFACTS |
    ADDRESS_WORDS |
    DECLARATION_LABELS |
    {'name', 'first', 'middle', 'surname', 'last', 'block', 'letters', 'in'}
)

# Labels that should never appear as date values
DATE_REJECT_LABELS = {
    'date', 'of', 'birth', 'admission', 'issue', 'dob', 'doa',
    'd', 'm', 'y', 'dd', 'mm', 'yy', 'yyyy',
    'd d', 'm m', 'y y y y',
}

# Function to check if a value is a label
def is_form_label(value: str, strict: bool = False) -> bool:
    """
    Check if a value is a form label that should be rejected.
    
    Args:
        value: The value to check
        strict: If True, use stricter matching (exact match only)
        
    Returns:
        True if the value is a form label, False otherwise
    """
    if not value:
        return True
        
    value_lower = value.lower().strip()
    
    # Empty or too short
    if len(value_lower) < 2:
        return True
    
    # Exact match
    if value_lower in ALL_FORM_LABELS:
        return True
    
    # If not strict, also check for partial matches
    if not strict:
        # Check if value contains any label phrase
        for label in ALL_FORM_LABELS:
            if len(label) > 3 and label in value_lower:
                return True
    
    return False


def is_reject_name_value(value: str) -> bool:
    """
    Check if a value should be rejected as a name field.
    
    Args:
        value: The value to check
        
    Returns:
        True if the value should be rejected, False otherwise
    """
    if not value:
        return True
        
    value_lower = value.lower().strip()
    value_words = value_lower.split()
    
    # Single word checks
    if len(value_words) == 1:
        if value_lower in NAME_REJECT_LABELS:
            return True
        # Single character or just initials
        if len(value_lower) <= 2:
            return True
    
    # Multi-word checks
    # Reject if contains "block letters" or similar
    if 'block letters' in value_lower or 'in block letters' in value_lower:
        return True
    
    # Reject if all words are labels/address words
    valid_words = [w for w in value_words if w.lower() not in NAME_REJECT_LABELS and len(w) > 1]
    if not valid_words:
        return True
    
    return False


def is_address_word(word: str) -> bool:
    """Check if a word is an address component."""
    return word.lower().strip() in ADDRESS_WORDS


def clean_name_value(value: str) -> str:
    """
    Clean a name value by removing label text and garbage.
    
    Args:
        value: The value to clean
        
    Returns:
        Cleaned name value, or empty string if invalid
    """
    if not value:
        return ''
    
    # Remove common label patterns
    import re
    
    value = re.sub(r'(?:name\s+)?in\s+block\s+letters', '', value, flags=re.IGNORECASE)
    value = re.sub(r'block\s+letters', '', value, flags=re.IGNORECASE)
    value = re.sub(r'^name\s+', '', value, flags=re.IGNORECASE)
    value = re.sub(r'\s+name\s+', ' ', value, flags=re.IGNORECASE)
    
    # Remove non-alpha characters (except spaces)
    value = re.sub(r'[^A-Za-z\s]', '', value).strip()
    
    # Filter out garbage words
    words = value.split()
    clean_words = [w for w in words if not is_form_label(w, strict=True) and len(w) > 1]
    
    if not clean_words:
        return ''
    
    return ' '.join(clean_words)
