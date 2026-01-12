/**
 * Utility functions to extract and filter structured data from OCR results
 * Filters out form labels and only returns handwritten values
 */

export interface StructuredData {
  [key: string]: any;
  fields?: Record<string, any>;
}

// Common form labels to filter out
const FORM_LABEL_KEYWORDS = [
  // Headers and instructions
  'shri ram college', 'student\'s data form', 'students data form', 'admission form',
  'all informations need to be filled', 'all information need to be filled',
  'academic session', 'academic year',
  
  // Field labels (with and without colons)
  'name:', 'student name:', 'applicant name:', 'full name:', 'name in block letters',
  'first name:', 'middle name:', 'surname:', 'last name:',
  'dob:', 'date of birth:', 'birth date:',
  'gender:', 'sex:', 'gender {tick', 'tick ()',
  'category:', 'caste:', 'reservation category:', 'admission category',
  'nationality:', 'country:',
  'religion:',
  'aadhar:', 'aadhaar:', 'uid:', 'aadhar number:',
  'blood group:', 'blood type:',
  'permanent address:', 'address:', 'local address for correspondence',
  'correspondence address:', 'mailing address:',
  'pincode:', 'pin code:', 'pin:', 'pin',
  'city:', 'state:',
  'phone:', 'mobile:', 'contact:', 'phone number:', 'contact numbers',
  'alternate phone:', 'alt phone:',
  'email:', 'e-mail:', 'email address:',
  'emergency contact:', 'emergency contact name:',
  'father:', "father's name:", 'father name:', "fathers name:",
  "father's occupation:", 'father occupation:', 'father\'s occupational details',
  "father's phone:", 'father phone:',
  'mother:', "mother's name:", 'mother name:', "mothers name:",
  "mother's occupation:", 'mother occupation:', 'mother\'s occupational details',
  "mother's phone:", 'mother phone:',
  'guardian:', 'guardian name:', 'local guardian', 'parent:',
  'guardian relation:', 'relationship:',
  'guardian phone:', 'parent phone:',
  'annual income:', 'income:', 'parent\'s/ family annual income',
  'course:', 'course applied:', 'program:', 'subject:', 'course (please', 'course please',
  'application number:', 'application no:',
  'enrollment number:', 'enrollment no:', 'delhi university enrollment no',
  'admission date:', 'date of admission:',
  '10th board:', 'tenth board:', 'board/university',
  '12th board:', 'twelfth board:',
  'school:', 'institution:', 'institution last attended',
  'session:', 'academic session:', 'academic year:',
  'college roll no:', 'roll number:', 'roll no:', 'roll no',
  'du portal form number:', 'cuet score:', 'total cuet score obtained',
  'year of passing', 'examination roll no', 'hindi studied upto',
  'whether below poverty line', 'whether belongs to minority',
  'details of marks obtained', 'details of qualifying examination',
  'certificate no', 'date of issue', 'certificate issuing authority',
  
  // Checkbox labels
  'male', 'female', 'transgender', 'gen', 'obc', 'sc', 'st', 'sports', 'pwd', 'ews',
  'foreign', 'cw', 'km', 'others', 'eca', 'yes', 'no',
  'muslim', 'jain', 'sikh', 'persian', 'christian', 'buddhists',
  
  // Section headers and repeated text
  'documents required', 'particulars', 'tick', 'attached', 'for office use',
  'self attested copies', 'printed admission', 'photographs pasted',
];

// Form header patterns (college name, form title, etc.)
const FORM_HEADER_PATTERNS = [
  /^shri\s*ram\s*college/i,
  /^sri\s*ram\s*college/i,
  /^ram\s*college/i,
  /college\s*of\s*commerce/i,
  /student[\'s]*\s*data\s*form/i,
  /students?\s*data?\s*form/i,
  /admission\s*form/i,
  /application\s*form/i,
  /^---\s*page\s*\d+\s*---/i,  // Page markers like "--- Page 1 ---"
  /all\s+informations?\s+need\s+to\s+be\s+filled/i,
  /academic\s+session/i,
];

/**
 * Check if a value is likely a form label rather than handwritten data
 */
export function isFormLabel(value: string): boolean {
  if (!value || typeof value !== 'string') {
    return false;
  }

  const valueTrimmed = value.trim();
  const valueLower = valueTrimmed.toLowerCase();
  
  // Check if value is empty or too short
  if (valueLower.length < 2) {
    return true;
  }

  // Check page markers first
  if (/^---\s*page\s*\d+\s*---$/i.test(valueTrimmed)) {
    return true;
  }

  // Check if it exactly matches a label keyword
  for (const label of FORM_LABEL_KEYWORDS) {
    const labelLower = label.toLowerCase();
    if (valueLower === labelLower || valueLower === labelLower.replace(':', '')) {
      return true;
    }
    // Check if value starts with label
    if (valueLower.startsWith(labelLower) || valueLower.startsWith(labelLower.replace(':', ''))) {
      return true;
    }
    // Check if label appears as a whole word in the value (for longer labels)
    const labelWords = labelLower.split(/\s+/);
    if (labelWords.length > 1) {
      // Escape special regex characters and check if all words of the label appear in sequence
      const escapedWords = labelWords.map(word => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
      const labelPattern = escapedWords.join('\\s+');
      try {
        if (new RegExp(`^${labelPattern}`, 'i').test(valueLower)) {
          return true;
        }
      } catch (e) {
        // If regex fails, fall back to simple string matching
        if (valueLower.startsWith(labelLower)) {
          return true;
        }
      }
    }
  }

  // Check form header patterns
  for (const pattern of FORM_HEADER_PATTERNS) {
    if (pattern.test(valueLower)) {
      return true;
    }
  }

  // Check for label patterns like "Name:", "Session:", etc. at start (standalone labels)
  if (/^(name|dob|date|phone|email|address|gender|category|course|session|roll|aadhar|first\s+name|middle\s+name|surname|college\s+roll)[:\s]*$/i.test(valueLower)) {
    return true;
  }

  // Check for common label patterns with numbers (like "1. Name", "2. Gender")
  if (/^\d+\.\s*(name|dob|date|phone|email|address|gender|category|course|session|roll|father|mother|guardian)/i.test(valueLower)) {
    return true;
  }

  // Check for patterns like "First Name", "Middle Name", "Surname" as standalone labels
  if (/^(first\s+name|middle\s+name|surname|last\s+name)$/i.test(valueLower)) {
    return true;
  }

  // Check if value is all uppercase short text (likely form labels)
  if (value === value.toUpperCase() && value.length > 3 && value.length < 50 && value.split(' ').length <= 5) {
    // But allow valid category codes and actual data
    const validCodes = ['OBC', 'SC', 'ST', 'GEN', 'EWS', 'PWD', 'ECA', 'CW', 'KM', 'INDIAN', 'HINDU'];
    const validDataPatterns = [
      /^\d{10,15}$/,  // Phone numbers
      /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/,  // Email addresses
      /^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$/,  // Aadhar numbers
      /^[A-Z]\+$/,  // Blood groups like "O+"
      /^\d{6}$/,  // Pincodes
    ];
    
    // Check if it matches a valid data pattern
    const isValidData = validDataPatterns.some(pattern => pattern.test(valueTrimmed));
    if (isValidData) {
      return false;
    }
    
    // Check if it's a valid code
    if (validCodes.includes(valueTrimmed)) {
      return false;
    }
    
    // Check if it's a known label keyword (all uppercase)
    for (const label of FORM_LABEL_KEYWORDS) {
      if (valueLower === label.toLowerCase() || valueLower.startsWith(label.toLowerCase())) {
        return true;
      }
    }
    
    // If it's all uppercase and matches common label patterns, it's likely a label
    if (/^(NAME|DOB|DATE|PHONE|EMAIL|ADDRESS|GENDER|CATEGORY|COURSE|SESSION|ROLL|FATHER|MOTHER|GUARDIAN|COLLEGE|SHRI|STUDENT)/i.test(valueTrimmed)) {
      return true;
    }
  }

  // Check if value contains multiple label keywords (likely label phrase)
  const labelWordCount = FORM_LABEL_KEYWORDS.filter(label => {
    const labelBase = label.replace(':', '').trim();
    return valueLower.includes(labelBase);
  }).length;

  if (labelWordCount >= 2 && valueLower.split(' ').length <= 5) {
    return true;
  }

  // Check for instruction phrases
  const instructionPatterns = [
    /please\s*(tick|check|fill|enter)/i,
    /all\s*informations?\s*need/i,
    /fill\s*in\s*capital\s*letters/i,
    /if\s*different\s*from/i,
    /if\s*yes/i,
    /mandatory/i,
    /optional/i,
    /signature\s+of/i,
    /for\s+office\s+use/i,
    /self\s+attested/i,
    /please\s*[✓√]/i,
    /tick\s*\(\)/i,
  ];

  for (const pattern of instructionPatterns) {
    if (pattern.test(valueLower)) {
      return true;
    }
  }

  // Check for checkbox/option lists (like "Male ✓ Female" or "GEN QBC SC ST")
  // These are typically labels, not values
  const checkboxPattern = /^(male|female|transgender|gen|obc|sc|st|sports|pwd|ews|foreign|cw|km|others|eca|yes|no)(\s+[✓√]?\s*(male|female|transgender|gen|obc|sc|st|sports|pwd|ews|foreign|cw|km|others|eca|yes|no))*$/i;
  if (checkboxPattern.test(valueLower) && valueLower.split(/\s+/).length <= 8) {
    return true;
  }

  // Check for section numbers with labels (like "11. Details of...")
  if (/^\d+\.\s+(details|personal|information|occupational|local|guardian|other|document)/i.test(valueLower)) {
    return true;
  }

  // Check for table headers or column labels
  const tableHeaderPatterns = [
    /^(si\.?\s*no|subjects|total|score|obtained|particulars|documents|for\s+office|attached|tick)/i,
    /^\([ivx]+\)\s*[a-z\s]+$/i,  // Roman numerals like "(I)", "(II)" followed by text
  ];
  for (const pattern of tableHeaderPatterns) {
    if (pattern.test(valueLower)) {
      return true;
    }
  }

  return false;
}

/**
 * Filter form labels from a data object
 * Returns only values that appear to be handwritten data (not labels)
 */
export function filterFormLabels(data: Record<string, any>): Record<string, any> {
  const filtered: Record<string, any> = {};

  for (const [key, value] of Object.entries(data)) {
    if (value === null || value === undefined || value === '') {
      continue;
    }

    // Handle string values
    if (typeof value === 'string') {
      // Check if value is a label
      if (!isFormLabel(value)) {
        filtered[key] = value;
      }
    }
    // Handle nested objects
    else if (typeof value === 'object' && !Array.isArray(value)) {
      const filteredNested = filterFormLabels(value);
      if (Object.keys(filteredNested).length > 0) {
        filtered[key] = filteredNested;
      }
    }
    // Handle arrays
    else if (Array.isArray(value)) {
      const filteredArray = value.filter(item => {
        if (typeof item === 'string') {
          return !isFormLabel(item);
        }
        return true;
      });
      if (filteredArray.length > 0) {
        filtered[key] = filteredArray;
      }
    }
    // Keep other types (numbers, booleans, etc.)
    else {
      filtered[key] = value;
    }
  }

  return filtered;
}

/**
 * Extract structured data from OCR result
 * Directly uses structured_data from backend which already has proper field names
 */
export function extractStructuredData(
  extractedData: {
    structured_data?: StructuredData | Record<string, any>;
    raw_text?: string;
  } | null | undefined
): Record<string, any> {
  if (!extractedData) {
    return {};
  }

  let result: Record<string, any> = {};

  // Use structured_data directly from backend (already has proper field names)
  if (extractedData.structured_data) {
    const structured = extractedData.structured_data;
    
    // If structured has a 'fields' nested object, use that
    const fieldsSource = structured.fields && typeof structured.fields === 'object' 
      ? structured.fields 
      : structured;
    
    for (const [key, value] of Object.entries(fieldsSource)) {
      // Skip metadata fields
      if (['pages', 'blocks', 'paragraphs', 'text', 'raw_text', 'confidence', 'provider'].includes(key)) {
        continue;
      }
      
      // Skip numbered labels like "10. details of..."
      if (/^\d+\.\s+/.test(key)) {
        continue;
      }
      
      // Map the key to standard field name if needed
      const mappedKey = mapLabelToFieldName(key);
      
      if (typeof value === 'string') {
        const trimmedValue = value.trim();
        // Only include non-empty values that aren't form labels
        if (trimmedValue.length > 0 && !isFormLabel(trimmedValue)) {
          result[mappedKey] = trimmedValue;
        }
      } else if (typeof value === 'boolean') {
        result[mappedKey] = value;
      } else if (typeof value === 'number') {
        result[mappedKey] = String(value);
      }
    }
    
    console.log('[extractStructuredData] Extracted fields:', Object.keys(result).length, 'fields');
    console.log('[extractStructuredData] student_name:', result.student_name);
    console.log('[extractStructuredData] date_of_birth:', result.date_of_birth);
    console.log('[extractStructuredData] gender:', result.gender);
  }

  return result;
  return {};
}

/**
 * Map label key to standard field name
 */
function mapLabelToFieldName(label: string): string {
  const labelLower = label.toLowerCase().trim();
  
  // Handle underscore-separated field names (from backend structured_data)
  const labelNormalized = labelLower.replace(/_/g, ' ').trim();
  
  const mapping: Record<string, string> = {
    // Names - include both underscore and space versions
    'name': 'student_name',
    'student name': 'student_name',
    'student_name': 'student_name',  // Already correct key
    'applicant name': 'student_name',
    'full name': 'student_name',
    'name of student': 'student_name',
    'first name': 'first_name',
    'first_name': 'first_name',
    'middle name': 'middle_name',
    'middle_name': 'middle_name',
    'surname': 'surname',
    'last name': 'surname',
    'last_name': 'surname',
    
    // Dates
    'dob': 'date_of_birth',
    'date of birth': 'date_of_birth',
    'date_of_birth': 'date_of_birth',
    'birth date': 'date_of_birth',
    
    // Gender
    'gender': 'gender',
    'sex': 'gender',
    
    // Contact
    'phone': 'phone_number',
    'mobile': 'phone_number',
    'contact': 'phone_number',
    'phone number': 'phone_number',
    'phone_number': 'phone_number',
    'mobile number': 'phone_number',
    'contact numbers': 'phone_number',
    'alternate phone': 'alternate_phone',
    'alternate_phone': 'alternate_phone',
    'alt phone': 'alternate_phone',
    'email': 'email',
    'e-mail': 'email',
    
    // Identity
    'aadhar': 'aadhar_number',
    'aadhaar': 'aadhar_number',
    'aadhar_number': 'aadhar_number',
    'uid': 'aadhar_number',
    'aadhar number': 'aadhar_number',
    'roll number': 'college_roll_no',
    'roll no': 'college_roll_no',
    'roll no.': 'college_roll_no',
    'college roll no': 'college_roll_no',
    'college roll no.': 'college_roll_no',
    'college_roll_no': 'college_roll_no',
    
    // Address
    'address': 'permanent_address',
    'permanent address': 'permanent_address',
    'permanent_address': 'permanent_address',
    'correspondence address': 'correspondence_address',
    'correspondence_address': 'correspondence_address',
    'mailing address': 'correspondence_address',
    'local address for correspondence': 'correspondence_address',
    'pincode': 'pincode',
    'pin code': 'pincode',
    'permanent_pincode': 'permanent_pincode',
    'permanent pincode': 'permanent_pincode',
    'correspondence_pincode': 'correspondence_pincode',
    'pin': 'pincode',
    'city': 'city',
    'state': 'state',
    'permanent_state': 'permanent_state',
    'permanent state': 'permanent_state',
    'correspondence_state': 'correspondence_state',
    
    // Family
    'father': 'father_name',
    "father's name": 'father_name',
    'father name': 'father_name',
    'father_name': 'father_name',
    "fathers name": 'father_name',
    'mother': 'mother_name',
    "mother's name": 'mother_name',
    'mother_name': 'mother_name',
    'mother name': 'mother_name',
    "mothers name": 'mother_name',
    'guardian': 'guardian_name',
    'guardian name': 'guardian_name',
    'local guardian': 'guardian_name',
    
    // Academic
    'course': 'course_applied',
    'course applied': 'course_applied',
    'program': 'course_applied',
    'application number': 'application_number',
    'application no': 'application_number',
    'enrollment number': 'enrollment_number',
    'enrollment no': 'enrollment_number',
    'du portal form number': 'application_number',
    'cuet score': 'cuet_score',
  };
  
  return mapping[labelLower] || label;  // Return original if no mapping found
}

/**
 * Clean and normalize field values
 */
export function cleanFieldValue(value: string, fieldName?: string): string {
  if (!value || typeof value !== 'string') {
    return '';
  }

  // Remove leading/trailing colons and whitespace
  let cleaned = value.trim().replace(/^[:;\s]+|[:;\s]+$/g, '');

  // Remove common prefixes that might be labels
  const prefixes = [
    /^(name|dob|date|phone|email|address|gender|category|course|session|roll|aadhar)[:\s]+/i,
  ];

  for (const prefix of prefixes) {
    cleaned = cleaned.replace(prefix, '').trim();
  }

  return cleaned;
}

