import { StudentProfileDetail } from '../services/api';
import './StudentProfileDetailsTable.css';

interface StudentProfileDetailsTableProps {
  profile: StudentProfileDetail;
}

export default function StudentProfileDetailsTable({ profile }: StudentProfileDetailsTableProps) {
  // Get the most recent verified form for displaying details
  const verifiedForm = profile.forms
    .filter(form => form.status === 'verified')
    .sort((a, b) => new Date(b.upload_date).getTime() - new Date(a.upload_date).getTime())[0];

  // If no verified form, use the most recent form
  const displayForm = verifiedForm || profile.forms[0];

  if (!displayForm) {
    return (
      <div className="empty-state">
        <p>No form data available to display.</p>
      </div>
    );
  }

  // Helper to format field value
  const formatValue = (value: any): string => {
    if (value === null || value === undefined || value === '') return '-';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    return String(value);
  };

  // Helper to format address
  const formatAddress = (line1?: string, line2?: string, line3?: string, state?: string, pincode?: string): string => {
    const parts = [line1, line2, line3, state, pincode].filter(p => p && p.trim() !== '');
    return parts.length > 0 ? parts.join(', ') : '-';
  };

  // Build data rows for the table - ORDER MATTERS: Personal Details, then Academic & Admission Details, then rest
  const dataRows = [
    // ============================================
    // PERSONAL DETAILS (Basic Information)
    // ============================================
    { section: 'Personal Details', label: 'Student Name', value: displayForm.student_name },
    { section: 'Personal Details', label: 'First Name', value: displayForm.first_name },
    { section: 'Personal Details', label: 'Middle Name', value: displayForm.middle_name },
    { section: 'Personal Details', label: 'Surname', value: displayForm.surname },
    { section: 'Personal Details', label: 'Date of Birth', value: displayForm.date_of_birth },
    { section: 'Personal Details', label: 'Gender', value: displayForm.gender },
    { section: 'Personal Details', label: 'Aadhar Number', value: displayForm.aadhar_number },
    { section: 'Personal Details', label: 'Roll Number', value: profile.roll_number || displayForm.college_roll_no },
    { section: 'Personal Details', label: 'Blood Group', value: displayForm.blood_group },
    { section: 'Personal Details', label: 'Nationality', value: displayForm.nationality },
    { section: 'Personal Details', label: 'Religion', value: displayForm.religion },
    { section: 'Personal Details', label: 'Category', value: displayForm.category },
    { section: 'Personal Details', label: 'Below Poverty Line', value: displayForm.below_poverty_line },
    { section: 'Personal Details', label: 'Minority Category', value: displayForm.minority_category },
    { section: 'Personal Details', label: 'Annual Income', value: displayForm.annual_income },
    
    // ============================================
    // ACADEMIC & ADMISSION DETAILS (Right after Personal Details)
    // ============================================
    { section: 'Academic & Admission Details', label: 'Academic Session', value: displayForm.academic_session },
    { section: 'Academic & Admission Details', label: 'Course', value: displayForm.course },
    { section: 'Academic & Admission Details', label: 'Admission Category', value: displayForm.admission_category },
    { section: 'Academic & Admission Details', label: 'Admission Category (Other)', value: displayForm.admission_category_other },
    { section: 'Academic & Admission Details', label: 'DU Portal Form Number', value: displayForm.du_portal_form_number },
    { section: 'Academic & Admission Details', label: 'CUET Score', value: displayForm.cuet_score },
    { section: 'Academic & Admission Details', label: 'Total CUET Score', value: displayForm.cuet_total_score },
    { section: 'Academic & Admission Details', label: 'College Roll No.', value: displayForm.college_roll_no },
    { section: 'Academic & Admission Details', label: 'Date of Admission', value: displayForm.date_of_admission },
    { section: 'Academic & Admission Details', label: 'Course Applied', value: displayForm.course_applied },
    { section: 'Academic & Admission Details', label: 'Application Number', value: displayForm.application_number },
    { section: 'Academic & Admission Details', label: 'Enrollment Number', value: displayForm.enrollment_number },
    
    // CUET Marks Details
    { section: 'Academic & Admission Details', label: 'CUET Subject 1', value: displayForm.cuet_subject_1 },
    { section: 'Academic & Admission Details', label: 'CUET Total Score 1', value: displayForm.cuet_total_score_1 },
    { section: 'Academic & Admission Details', label: 'CUET Score Obtained 1', value: displayForm.cuet_score_obtained_1 },
    { section: 'Academic & Admission Details', label: 'CUET Subject 2', value: displayForm.cuet_subject_2 },
    { section: 'Academic & Admission Details', label: 'CUET Total Score 2', value: displayForm.cuet_total_score_2 },
    { section: 'Academic & Admission Details', label: 'CUET Score Obtained 2', value: displayForm.cuet_score_obtained_2 },
    { section: 'Academic & Admission Details', label: 'CUET Subject 3', value: displayForm.cuet_subject_3 },
    { section: 'Academic & Admission Details', label: 'CUET Total Score 3', value: displayForm.cuet_total_score_3 },
    { section: 'Academic & Admission Details', label: 'CUET Score Obtained 3', value: displayForm.cuet_score_obtained_3 },
    { section: 'Academic & Admission Details', label: 'CUET Subject 4', value: displayForm.cuet_subject_4 },
    { section: 'Academic & Admission Details', label: 'CUET Total Score 4', value: displayForm.cuet_total_score_4 },
    { section: 'Academic & Admission Details', label: 'CUET Score Obtained 4', value: displayForm.cuet_score_obtained_4 },
    { section: 'Academic & Admission Details', label: 'CUET Subject 5', value: displayForm.cuet_subject_5 },
    { section: 'Academic & Admission Details', label: 'CUET Total Score 5', value: displayForm.cuet_total_score_5 },
    { section: 'Academic & Admission Details', label: 'CUET Score Obtained 5', value: displayForm.cuet_score_obtained_5 },
    { section: 'Academic & Admission Details', label: 'CUET Subject 6', value: displayForm.cuet_subject_6 },
    { section: 'Academic & Admission Details', label: 'CUET Total Score 6', value: displayForm.cuet_total_score_6 },
    { section: 'Academic & Admission Details', label: 'CUET Score Obtained 6', value: displayForm.cuet_score_obtained_6 },
    
    // ============================================
    // ADDRESS DETAILS
    // ============================================
    { section: 'Address Details', label: 'Permanent Address', value: formatAddress(
      displayForm.permanent_address_line1,
      displayForm.permanent_address_line2,
      displayForm.permanent_address_line3,
      displayForm.permanent_state,
      displayForm.permanent_pincode
    ) || displayForm.permanent_address },
    { section: 'Address Details', label: 'Permanent Address Line 1', value: displayForm.permanent_address_line1 },
    { section: 'Address Details', label: 'Permanent Address Line 2', value: displayForm.permanent_address_line2 },
    { section: 'Address Details', label: 'Permanent Address Line 3', value: displayForm.permanent_address_line3 },
    { section: 'Address Details', label: 'Permanent State', value: displayForm.permanent_state },
    { section: 'Address Details', label: 'Permanent Pincode', value: displayForm.permanent_pincode },
    { section: 'Address Details', label: 'Correspondence Address', value: formatAddress(
      displayForm.correspondence_address_line1,
      displayForm.correspondence_address_line2,
      displayForm.correspondence_address_line3,
      displayForm.correspondence_state,
      displayForm.correspondence_pincode
    ) || displayForm.correspondence_address },
    { section: 'Address Details', label: 'Correspondence Address Line 1', value: displayForm.correspondence_address_line1 },
    { section: 'Address Details', label: 'Correspondence Address Line 2', value: displayForm.correspondence_address_line2 },
    { section: 'Address Details', label: 'Correspondence Address Line 3', value: displayForm.correspondence_address_line3 },
    { section: 'Address Details', label: 'Correspondence State', value: displayForm.correspondence_state },
    { section: 'Address Details', label: 'Correspondence Pincode', value: displayForm.correspondence_pincode },
    { section: 'Address Details', label: 'City', value: displayForm.city },
    { section: 'Address Details', label: 'State', value: displayForm.state },
    { section: 'Address Details', label: 'Pincode', value: displayForm.pincode },
    
    // ============================================
    // CONTACT DETAILS
    // ============================================
    { section: 'Contact Details', label: 'Email', value: displayForm.email },
    { section: 'Contact Details', label: 'Phone Number', value: displayForm.phone_number },
    { section: 'Contact Details', label: 'Alternate Phone', value: displayForm.alternate_phone },
    { section: 'Contact Details', label: 'Emergency Contact Name', value: displayForm.emergency_contact_name },
    { section: 'Contact Details', label: 'Emergency Contact Phone', value: displayForm.emergency_contact_phone },
    
    // ============================================
    // PARENT/GUARDIAN DETAILS
    // ============================================
    { section: 'Mother\'s Details', label: 'Mother\'s Name', value: displayForm.mother_name },
    { section: 'Mother\'s Details', label: 'Occupation', value: displayForm.mother_occupation },
    { section: 'Mother\'s Details', label: 'Designation', value: displayForm.mother_designation },
    { section: 'Mother\'s Details', label: 'Organization & Address', value: displayForm.mother_organization },
    { section: 'Mother\'s Details', label: 'Email', value: displayForm.mother_email },
    { section: 'Mother\'s Details', label: 'Mobile', value: displayForm.mother_mobile },
    { section: 'Mother\'s Details', label: 'Landline Code', value: displayForm.mother_landline_code },
    { section: 'Mother\'s Details', label: 'Landline', value: displayForm.mother_landline },
    { section: 'Mother\'s Details', label: 'Phone', value: displayForm.mother_phone },
    
    { section: 'Father\'s Details', label: 'Father\'s Name', value: displayForm.father_name },
    { section: 'Father\'s Details', label: 'Occupation', value: displayForm.father_occupation },
    { section: 'Father\'s Details', label: 'Designation', value: displayForm.father_designation },
    { section: 'Father\'s Details', label: 'Organization & Address', value: displayForm.father_organization },
    { section: 'Father\'s Details', label: 'Email', value: displayForm.father_email },
    { section: 'Father\'s Details', label: 'Mobile', value: displayForm.father_mobile },
    { section: 'Father\'s Details', label: 'Landline Code', value: displayForm.father_landline_code },
    { section: 'Father\'s Details', label: 'Landline', value: displayForm.father_landline },
    { section: 'Father\'s Details', label: 'Phone', value: displayForm.father_phone },
    
    { section: 'Local Guardian\'s Details', label: 'Guardian Name', value: displayForm.guardian_name },
    { section: 'Local Guardian\'s Details', label: 'Relation', value: displayForm.guardian_relation },
    { section: 'Local Guardian\'s Details', label: 'Residential Address', value: displayForm.guardian_residential_address },
    { section: 'Local Guardian\'s Details', label: 'Organization & Address', value: displayForm.guardian_organization },
    { section: 'Local Guardian\'s Details', label: 'Email', value: displayForm.guardian_email },
    { section: 'Local Guardian\'s Details', label: 'Mobile', value: displayForm.guardian_mobile },
    { section: 'Local Guardian\'s Details', label: 'Landline Code', value: displayForm.guardian_landline_code },
    { section: 'Local Guardian\'s Details', label: 'Landline', value: displayForm.guardian_landline },
    { section: 'Local Guardian\'s Details', label: 'Phone', value: displayForm.guardian_phone },
    
    // ============================================
    // QUALIFYING EXAMINATION DETAILS
    // ============================================
    { section: 'Qualifying Examination', label: '12th Year of Passing', value: displayForm.twelfth_year },
    { section: 'Qualifying Examination', label: '12th Board/University', value: displayForm.twelfth_board },
    { section: 'Qualifying Examination', label: '12th Examination Roll No.', value: displayForm.twelfth_roll_number },
    { section: 'Qualifying Examination', label: '12th Institution Last Attended', value: displayForm.twelfth_institution },
    { section: 'Qualifying Examination', label: '12th Percentage', value: displayForm.twelfth_percentage },
    { section: 'Qualifying Examination', label: '12th School', value: displayForm.twelfth_school },
    { section: 'Qualifying Examination', label: 'Hindi Studied Upto', value: displayForm.hindi_studied_upto },
    { section: 'Qualifying Examination', label: '10th Board', value: displayForm.tenth_board },
    { section: 'Qualifying Examination', label: '10th Year', value: displayForm.tenth_year },
    { section: 'Qualifying Examination', label: '10th Percentage', value: displayForm.tenth_percentage },
    { section: 'Qualifying Examination', label: '10th School', value: displayForm.tenth_school },
    { section: 'Qualifying Examination', label: 'Previous Qualification', value: displayForm.previous_qualification },
    { section: 'Qualifying Examination', label: 'Graduation Details', value: displayForm.graduation_details },
    
    // ============================================
    // OTHER INFORMATION
    // ============================================
    { section: 'Other Information', label: 'DU Enrollment Number', value: displayForm.du_enrollment_number },
    { section: 'Other Information', label: 'Hindi Medium Preference', value: displayForm.hindi_medium_preference },
    
    // ============================================
    // CATEGORY CERTIFICATE DETAILS
    // ============================================
    { section: 'Category Certificate Details', label: 'Certificate Issuing Authority', value: displayForm.category_certificate_authority },
    { section: 'Category Certificate Details', label: 'Certificate Number', value: displayForm.category_certificate_number },
    { section: 'Category Certificate Details', label: 'Certificate Date of Issue', value: displayForm.category_certificate_date },
    { section: 'Category Certificate Details', label: 'Disability Percentage', value: displayForm.disability_percentage },
    { section: 'Category Certificate Details', label: 'Type of Disability', value: displayForm.disability_type },
    { section: 'Category Certificate Details', label: 'UDID Number', value: displayForm.udid_number },
    
    // ============================================
    // DOCUMENT CHECKLIST
    // ============================================
    { section: 'Document Checklist', label: 'Admission/Registration Form', value: displayForm.doc_admission_form },
    { section: 'Document Checklist', label: 'Anti-Ragging Undertaking', value: displayForm.doc_undertaking_ragging },
    { section: 'Document Checklist', label: 'Photographs', value: displayForm.doc_photographs },
    { section: 'Document Checklist', label: 'CUET Score Card', value: displayForm.doc_cuet_scorecard },
    { section: 'Document Checklist', label: 'Class XII Mark Sheet', value: displayForm.doc_class_xii_marksheet },
    { section: 'Document Checklist', label: 'Class X Certificate', value: displayForm.doc_class_x_certificate },
    { section: 'Document Checklist', label: 'Class XII Certificate', value: displayForm.doc_class_xii_certificate },
    { section: 'Document Checklist', label: 'Character Certificate', value: displayForm.doc_character_certificate },
    { section: 'Document Checklist', label: 'Transfer/Migration Certificate', value: displayForm.doc_transfer_certificate },
    { section: 'Document Checklist', label: 'Hindi Certificate', value: displayForm.doc_hindi_certificate },
    { section: 'Document Checklist', label: 'Caste/Category Certificate', value: displayForm.doc_caste_certificate },
    { section: 'Document Checklist', label: 'Sports/ECA Certificates', value: displayForm.doc_sports_eca },
    { section: 'Document Checklist', label: 'Original Documents', value: displayForm.doc_originals },
    { section: 'Document Checklist', label: 'Photo ID Proof', value: displayForm.doc_photo_id },
    
    // ============================================
    // SYSTEM INFORMATION
    // ============================================
    { section: 'System Information', label: 'Form Status', value: displayForm.status },
    { section: 'System Information', label: 'OCR Provider', value: displayForm.ocr_provider },
    { section: 'System Information', label: 'Form Upload Date', value: new Date(displayForm.upload_date).toLocaleDateString() },
    { section: 'System Information', label: 'Profile Created', value: new Date(profile.created_date).toLocaleDateString() },
    { section: 'System Information', label: 'Profile Last Updated', value: new Date(profile.updated_date).toLocaleDateString() },
  ].filter(row => {
    // Filter out rows with no value, but keep rows with value '-'
    const val = row.value;
    return val !== undefined && val !== null && val !== '';
  });

  // Define sections in the correct order
  const sections = [
    'Personal Details',
    'Academic & Admission Details',
    'Address Details',
    'Contact Details',
    'Mother\'s Details',
    'Father\'s Details',
    'Local Guardian\'s Details',
    'Qualifying Examination',
    'Other Information',
    'Category Certificate Details',
    'Document Checklist',
    'System Information'
  ];

  return (
    <div className="profile-details-table-container">
      <table className="profile-details-table">
        <thead>
          <tr>
            <th className="col-section">Section</th>
            <th className="col-label">Field</th>
            <th className="col-value">Value</th>
          </tr>
        </thead>
        <tbody>
          {sections.map(section => {
            const sectionRows = dataRows.filter(row => row.section === section);
            if (sectionRows.length === 0) return null;
            
            return sectionRows.map((row, index) => (
              <tr key={`${section}-${index}`} className={index === 0 ? 'section-start' : ''}>
                {index === 0 && (
                  <td rowSpan={sectionRows.length} className="col-section">
                    {section}
                  </td>
                )}
                <td className="col-label">{row.label}</td>
                <td className="col-value">{formatValue(row.value)}</td>
              </tr>
            ));
          })}
        </tbody>
      </table>
    </div>
  );
}