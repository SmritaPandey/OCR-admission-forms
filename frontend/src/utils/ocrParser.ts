/**
 * Utility functions to parse OCR text and extract structured information
 */

export interface ParsedInfo {
  student_name?: string;
  date_of_birth?: string;
  address?: string;
  phone_number?: string;
  email?: string;
  guardian_name?: string;
  guardian_phone?: string;
  course_applied?: string;
  previous_qualification?: string;
}

/**
 * Extract information from OCR raw text using pattern matching
 */
export function parseOCRText(rawText: string): ParsedInfo {
  const parsed: ParsedInfo = {};
  const text = rawText.toLowerCase();
  const lines = rawText.split('\n').filter(line => line.trim().length > 0);

  // Student Name - Look for "name:" or "student name:" or "applicant name:"
  const namePatterns = [
    /(?:name|student\s+name|applicant\s+name|full\s+name)[:\s]+([a-z\s]+?)(?:\n|phone|dob|email|address|$)/i,
    /^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*$/m, // Full name on its own line
  ];
  
  for (const pattern of namePatterns) {
    const match = rawText.match(pattern);
    if (match && match[1]) {
      const name = match[1].trim();
      if (name.length > 2 && name.length < 50 && /^[a-z\s'-]+$/i.test(name)) {
        parsed.student_name = name.split(/\s+/).map(word => 
          word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
        ).join(' ');
        break;
      }
    }
  }

  // Email - Standard email regex
  const emailPattern = /([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/i;
  const emailMatch = rawText.match(emailPattern);
  if (emailMatch) {
    parsed.email = emailMatch[1].trim().toLowerCase();
  }

  // Phone Number - Various formats
  const phonePatterns = [
    /(?:phone|mobile|contact|tel)[:\s]+([+\d\s\-()]{10,15})/i,
    /(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/,
    /\d{10,15}/,
  ];
  
  for (const pattern of phonePatterns) {
    const match = rawText.match(pattern);
    if (match) {
      let phone = match[1] || match[0];
      // Clean up phone number
      phone = phone.replace(/\s+/g, '').replace(/[^\d+]/g, '');
      if (phone.length >= 10 && phone.length <= 15) {
        parsed.phone_number = phone;
        break;
      }
    }
  }

  // Date of Birth - Look for "dob", "birth", "date of birth"
  const dobPatterns = [
    /(?:dob|date\s+of\s+birth|birth\s+date|born)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})/i,
    /(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})/, // Generic date pattern
  ];
  
  for (const pattern of dobPatterns) {
    const match = rawText.match(pattern);
    if (match && match[1]) {
      const dob = match[1].trim();
      if (dob.length >= 8 && dob.length <= 12) {
        parsed.date_of_birth = dob;
        break;
      }
    }
  }

  // Address - Look for "address:" followed by multiple lines
  const addressPattern = /(?:address|residence|location)[:\s]+([^\n]+(?:\n[^\n]+){0,3})/i;
  const addressMatch = rawText.match(addressPattern);
  if (addressMatch && addressMatch[1]) {
    const address = addressMatch[1]
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0)
      .join(', ');
    if (address.length > 10) {
      parsed.address = address;
    }
  }

  // Guardian Name - Look for "guardian", "parent", "father", "mother"
  const guardianPatterns = [
    /(?:guardian|parent|father|mother)[:\s]+([a-z\s]+?)(?:\n|phone|email|$)/i,
  ];
  
  for (const pattern of guardianPatterns) {
    const match = rawText.match(pattern);
    if (match && match[1]) {
      const name = match[1].trim();
      if (name.length > 2 && name.length < 50) {
        parsed.guardian_name = name.split(/\s+/).map(word => 
          word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
        ).join(' ');
        break;
      }
    }
  }

  // Guardian Phone
  const guardianPhonePattern = /(?:guardian|parent)[\s\w]*phone[:\s]+([+\d\s\-()]{10,15})/i;
  const guardianPhoneMatch = rawText.match(guardianPhonePattern);
  if (guardianPhoneMatch && guardianPhoneMatch[1]) {
    let phone = guardianPhoneMatch[1].replace(/\s+/g, '').replace(/[^\d+]/g, '');
    if (phone.length >= 10) {
      parsed.guardian_phone = phone;
    }
  }

  // Course Applied - Look for "course", "program", "subject"
  const coursePatterns = [
    /(?:course|program|subject|stream)[:\s]+([^\n]+)/i,
  ];
  
  for (const pattern of coursePatterns) {
    const match = rawText.match(pattern);
    if (match && match[1]) {
      const course = match[1].trim();
      if (course.length > 3 && course.length < 100) {
        parsed.course_applied = course;
        break;
      }
    }
  }

  // Previous Qualification - Look for "qualification", "education", "degree"
  const qualPatterns = [
    /(?:qualification|education|degree|diploma)[:\s]+([^\n]+)/i,
  ];
  
  for (const pattern of qualPatterns) {
    const match = rawText.match(pattern);
    if (match && match[1]) {
      const qual = match[1].trim();
      if (qual.length > 3 && qual.length < 100) {
        parsed.previous_qualification = qual;
        break;
      }
    }
  }

  return parsed;
}

