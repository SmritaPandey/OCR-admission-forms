import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiService, StudentProfileDetail, AdmissionForm, FormVerification, Document } from '../services/api';
import { parseOCRText } from '../utils/ocrParser';
import { extractStructuredData, filterFormLabels, isFormLabel } from '../utils/structuredDataParser';
import DocumentUpload from './DocumentUpload';
import './VerificationView.css'; // Reusing the same styles

// Helper to get all documents from profile and forms
const getAllDocuments = (profile: StudentProfileDetail | null): (Document & { sourceLabel: string })[] => {
  if (!profile) return [];
  
  const directDocs = (profile.documents || []).map(doc => ({
    ...doc,
    sourceLabel: 'Profile'
  }));
  
  const formDocs = (profile.forms || []).flatMap(form => 
    (form.documents || []).map(doc => ({
      ...doc,
      sourceLabel: `Form: ${form.filename}`
    }))
  );
  
  return [...directDocs, ...formDocs];
};

const normalizeConfidence = (value?: number | null): number | undefined => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return undefined;
  }
  if (value <= 1) {
    return value * 100;
  }
  return value;
};

const formatConfidenceValue = (value?: number | null): string => {
  const normalized = normalizeConfidence(value);
  return normalized !== undefined ? `${normalized.toFixed(1)}%` : 'n/a';
};

// Helper to get the correct file URL
const getFileUrl = (filePath: string | undefined, formId?: number, page?: number): string => {
  const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  
  if (!filePath) {
    // Fallback to preview endpoint if no file path
    return formId ? `${apiUrl}/api/preview/${formId}${page ? `?page=${page}` : ''}` : '';
  }
  
  // Normalize the file path - remove any leading 'uploads/' to avoid duplication
  let normalizedPath = filePath;
  if (normalizedPath.startsWith('uploads/')) {
    normalizedPath = normalizedPath.substring(8);
  }
  if (normalizedPath.startsWith('/uploads/')) {
    normalizedPath = normalizedPath.substring(9);
  }
  if (normalizedPath.startsWith('/')) {
    normalizedPath = normalizedPath.substring(1);
  }
  
  // Return the direct PDF URL - browser will handle page navigation via #page= anchor
  return `${apiUrl}/uploads/${normalizedPath}`;
};

const mergeIntoVerification = (
  base: FormVerification,
  updates: Record<string, any> | undefined,
  options: { overwrite?: boolean } = {}
): FormVerification => {
  if (!updates) {
    return base;
  }
  const { overwrite = false } = options;
  const next: FormVerification = { ...base };
  Object.entries(updates).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    const fieldKey = key as keyof FormVerification;
    if (!(fieldKey in next)) {
      return;
    }
    if (fieldKey === 'additional_info') {
      const current = typeof next.additional_info === 'object' && next.additional_info !== null ? next.additional_info : {};
      next.additional_info = { ...current, ...(value as Record<string, any>) };
      return;
    }
    if (overwrite || !next[fieldKey]) {
      next[fieldKey] = value as string;
    }
  });
  return next;
};

function StudentEditView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<StudentProfileDetail | null>(null);
  const [form, setForm] = useState<AdmissionForm | null>(null);
  const [verification, setVerification] = useState<FormVerification>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

  // Initialize form state from existing data
  useEffect(() => {
    if (id) {
      loadStudentData(parseInt(id));
    }
  }, [id]);

  const loadStudentData = async (studentId: number) => {
    try {
      setLoading(true);
      const profileData = await apiService.getStudentProfile(studentId);
      setProfile(profileData);

      // Try to find an associated admission form
      // If profile has forms, use the first one to populate the edit view
      if (profileData.forms && profileData.forms.length > 0) {
        // Sort by upload date desc to get latest
        const forms = [...profileData.forms].sort((a, b) => 
          new Date(b.upload_date).getTime() - new Date(a.upload_date).getTime()
        );
        const latestForm = forms[0];
        
        // Fetch full form details including extracted data
        const formData = await apiService.getForm(latestForm.id);
        setForm(formData);
        
        // Get structured data from extracted_data as fallback
        const sd = formData.extracted_data?.structured_data || {};
        
        // Helper to get value from form or structured data
        const getValue = (field: string): string => {
          return (formData as any)[field] || sd[field] || '';
        };
        
        // Initialize verification state from form data AND structured_data
        const formState: FormVerification = {
          // Academic & Admission
          academic_session: getValue('academic_session'),
          course: getValue('course'),
          admission_category: getValue('admission_category'),
          admission_category_other: getValue('admission_category_other'),
          du_portal_form_number: getValue('du_portal_form_number'),
          cuet_score: getValue('cuet_score'),
          college_roll_no: getValue('college_roll_no'),
          date_of_admission: getValue('date_of_admission'),
          
          // Personal - Name parts
          first_name: getValue('first_name'),
          middle_name: getValue('middle_name'),
          surname: getValue('surname'),
          student_name: formData.student_name || profileData.student_name || sd.student_name || '',
          date_of_birth: getValue('date_of_birth'),
          gender: getValue('gender'),
          category: getValue('category'),
          nationality: getValue('nationality'),
          religion: getValue('religion'),
          aadhar_number: formData.aadhar_number || profileData.aadhar_number || sd.aadhar_number || '',
          blood_group: getValue('blood_group'),
          below_poverty_line: getValue('below_poverty_line'),
          annual_income: getValue('annual_income'),
          minority_category: getValue('minority_category'),
          
          // Address
          permanent_address: getValue('permanent_address'),
          permanent_state: getValue('permanent_state'),
          permanent_pincode: getValue('permanent_pincode'),
          correspondence_address: getValue('correspondence_address'),
          correspondence_state: getValue('correspondence_state'),
          correspondence_pincode: getValue('correspondence_pincode'),
          city: getValue('city'),
          state: getValue('state'),
          pincode: getValue('pincode'),
          
          // Contact
          phone_number: formData.phone_number || profileData.phone_number || sd.phone_number || '',
          alternate_phone: getValue('alternate_phone'),
          email: formData.email || profileData.email || sd.email || '',
          emergency_contact_name: getValue('emergency_contact_name'),
          emergency_contact_phone: getValue('emergency_contact_phone'),
          
          // Family
          father_name: getValue('father_name'),
          father_occupation: getValue('father_occupation'),
          father_designation: getValue('father_designation'),
          father_organization: getValue('father_organization'),
          father_email: getValue('father_email'),
          father_mobile: getValue('father_mobile'),
          father_phone: getValue('father_phone'),
          
          mother_name: getValue('mother_name'),
          mother_occupation: getValue('mother_occupation'),
          mother_designation: getValue('mother_designation'),
          mother_organization: getValue('mother_organization'),
          mother_email: getValue('mother_email'),
          mother_mobile: getValue('mother_mobile'),
          mother_phone: getValue('mother_phone'),
          
          guardian_name: getValue('guardian_name'),
          guardian_relation: getValue('guardian_relation'),
          guardian_residential_address: getValue('guardian_residential_address'),
          guardian_organization: getValue('guardian_organization'),
          guardian_email: getValue('guardian_email'),
          guardian_mobile: getValue('guardian_mobile'),
          guardian_phone: getValue('guardian_phone'),
          
          // Academic History
          tenth_board: getValue('tenth_board'),
          tenth_year: getValue('tenth_year'),
          tenth_percentage: getValue('tenth_percentage'),
          tenth_school: getValue('tenth_school'),
          twelfth_board: getValue('twelfth_board'),
          twelfth_year: getValue('twelfth_year'),
          twelfth_percentage: getValue('twelfth_percentage'),
          twelfth_school: getValue('twelfth_school'),
          twelfth_roll_number: getValue('twelfth_roll_number'),
          twelfth_institution: getValue('twelfth_institution'),
          hindi_studied_upto: getValue('hindi_studied_upto'),
          previous_qualification: getValue('previous_qualification'),
          graduation_details: getValue('graduation_details'),
          
          // Course & Admission
          course_applied: formData.course_applied || profileData.course_applied || sd.course_applied || '',
          application_number: formData.application_number || profileData.application_number || sd.application_number || '',
          enrollment_number: formData.enrollment_number || profileData.enrollment_number || sd.enrollment_number || '',
          du_enrollment_number: getValue('du_enrollment_number'),
          hindi_medium_preference: getValue('hindi_medium_preference'),
          admission_date: getValue('admission_date'),
          
          // Certificate
          category_certificate_authority: getValue('category_certificate_authority'),
          category_certificate_number: getValue('category_certificate_number'),
          category_certificate_date: getValue('category_certificate_date'),
          disability_percentage: getValue('disability_percentage'),
          disability_type: getValue('disability_type'),
          udid_number: getValue('udid_number'),
          
          // CUET Marks
          cuet_subject_1: getValue('cuet_subject_1'),
          cuet_total_score_1: getValue('cuet_total_score_1'),
          cuet_score_obtained_1: getValue('cuet_score_obtained_1'),
          cuet_subject_2: getValue('cuet_subject_2'),
          cuet_total_score_2: getValue('cuet_total_score_2'),
          cuet_score_obtained_2: getValue('cuet_score_obtained_2'),
          cuet_subject_3: getValue('cuet_subject_3'),
          cuet_total_score_3: getValue('cuet_total_score_3'),
          cuet_score_obtained_3: getValue('cuet_score_obtained_3'),
          cuet_subject_4: getValue('cuet_subject_4'),
          cuet_total_score_4: getValue('cuet_total_score_4'),
          cuet_score_obtained_4: getValue('cuet_score_obtained_4'),
          cuet_subject_5: getValue('cuet_subject_5'),
          cuet_total_score_5: getValue('cuet_total_score_5'),
          cuet_score_obtained_5: getValue('cuet_score_obtained_5'),
          cuet_subject_6: getValue('cuet_subject_6'),
          cuet_total_score_6: getValue('cuet_total_score_6'),
          cuet_score_obtained_6: getValue('cuet_score_obtained_6'),
          cuet_total_score: getValue('cuet_total_score'),
          
          // Document Checklist
          doc_admission_form: getValue('doc_admission_form'),
          doc_undertaking_ragging: getValue('doc_undertaking_ragging'),
          doc_photographs: getValue('doc_photographs'),
          doc_cuet_scorecard: getValue('doc_cuet_scorecard'),
          doc_class_xii_marksheet: getValue('doc_class_xii_marksheet'),
          doc_class_x_certificate: getValue('doc_class_x_certificate'),
          doc_class_xii_certificate: getValue('doc_class_xii_certificate'),
          doc_character_certificate: getValue('doc_character_certificate'),
          doc_transfer_certificate: getValue('doc_transfer_certificate'),
          doc_hindi_certificate: getValue('doc_hindi_certificate'),
          doc_caste_certificate: getValue('doc_caste_certificate'),
          doc_sports_eca: getValue('doc_sports_eca'),
          doc_originals: getValue('doc_originals'),
          doc_photo_id: getValue('doc_photo_id'),
        };
        
        setVerification(formState);
      } else {
        // No form found, initialize with basic profile data
        setVerification({
          student_name: profileData.student_name,
          roll_number: profileData.roll_number,
          aadhar_number: profileData.aadhar_number,
          phone_number: profileData.phone_number,
          email: profileData.email,
          course_applied: profileData.course_applied,
          application_number: profileData.application_number,
          enrollment_number: profileData.enrollment_number,
        } as any);
      }
    } catch (error) {
      console.error('Failed to load student data:', error);
      alert('Failed to load student data');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: keyof FormVerification, value: string) => {
    setVerification((prev) => ({ ...prev, [field]: value }));
  };

  const handleApplyParsedData = useCallback(() => {
    if (!form?.extracted_data) {
      alert('No OCR data available to autofill');
      return;
    }

    let parsedData: Record<string, any> = {};

    // Priority 1: Use structured_data if available (from Google Vision, Document AI, etc.)
    if (form.extracted_data.structured_data) {
      parsedData = extractStructuredData({ structured_data: form.extracted_data.structured_data });
    }

    // Priority 2: Parse raw_text if structured_data didn't provide enough data
    if (form.extracted_data.raw_text) {
      const parsedFromText = parseOCRText(form.extracted_data.raw_text);
      
      // Filter out form labels from parsed text
      const filteredParsed = filterFormLabels(parsedFromText);
      
      // Merge with structured data (structured_data takes precedence)
      parsedData = { ...filteredParsed, ...parsedData };
      
      // Handle address field mapping
      if (parsedFromText.address && !parsedData.permanent_address) {
        if (!isFormLabel(parsedFromText.address)) {
          parsedData.permanent_address = parsedFromText.address;
        }
      }
    }

    // Count how many fields were actually filled
    const fieldsToFill = Object.keys(parsedData).filter(key => {
      const value = parsedData[key];
      return value !== undefined && value !== null && value !== '' && 
             typeof value === 'string' && value.trim().length > 0;
    }).length;

    // Apply filtered data to verification state
    setVerification((prev) => mergeIntoVerification(prev, parsedData, { overwrite: false }));
    
    // Show success message
    if (fieldsToFill > 0) {
      alert(`✅ Autofill complete! ${fieldsToFill} field${fieldsToFill > 1 ? 's' : ''} filled successfully.`);
    } else {
      alert('⚠️ No fields could be extracted from the OCR text. Please verify the extracted text or try re-extracting.');
    }
  }, [form?.extracted_data]);

  const handleSave = async () => {
    if (!id) return;

    try {
      setSaving(true);

      // Build full name from parts if available
      const fullName = [verification.first_name, verification.middle_name, verification.surname]
        .filter(Boolean)
        .join(' ') || verification.student_name || '';

      // Update student profile (basic fields)
      await apiService.updateStudentProfile(parseInt(id), {
        student_name: fullName,
        roll_number: verification.college_roll_no || undefined,
        aadhar_number: verification.aadhar_number,
      });

      // If there's a form, update it with all the form fields
      if (form) {
        // Ensure student_name is set from parts
        const updatedVerification = {
          ...verification,
          student_name: fullName,
        };
        await apiService.updateForm(form.id, updatedVerification);
      }

      alert('Student profile and form updated successfully');
      navigate(`/students/${id}`);
    } catch (error: any) {
      alert(`Save failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading student data...</div>;
  }

  if (!profile) {
    return <div className="error">Student profile not found</div>;
  }

  return (
    <div className="verification-view">
      <div className="verification-header">
        <h2>Edit Student: {profile.student_name}</h2>
        <div className="header-actions">
          <button onClick={handleSave} className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button onClick={() => navigate(`/students/${id}`)} className="btn btn-secondary">
            Cancel
          </button>
        </div>
      </div>

      <div className="verification-content" style={{ display: 'grid', gridTemplateColumns: form ? '1fr 1fr' : '1fr', gap: '2rem' }}>
        {form && (
          <div className="form-preview">
            <div className="page-controls">
              <button 
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              >
                Previous
              </button>
              <span>Page {currentPage} of {form.extracted_data?.total_pages || form.extracted_data?.pages_processed || 1}</span>
              <button 
                disabled={currentPage >= (form.extracted_data?.total_pages || form.extracted_data?.pages_processed || 1)}
                onClick={() => {
                  const maxPages = form.extracted_data?.total_pages || form.extracted_data?.pages_processed || 1;
                  setCurrentPage(prev => Math.min(maxPages, prev + 1));
                }}
              >
                Next
              </button>
            </div>
            <div className="image-container">
              {form.file_path?.toLowerCase().endsWith('.pdf') ? (
                // PDF files - use iframe for native PDF viewing with page navigation
                <iframe
                  key={`pdf-${form.id}-${currentPage}`}
                  src={`${getFileUrl(form.file_path, form.id)}#page=${currentPage}`}
                  title={`Scanned form page ${currentPage}`}
                  width="100%"
                  height="800px"
                  style={{ border: 'none', display: 'block' }}
                  allow="fullscreen"
                />
              ) : (
                // Image files
                <img
                  src={getFileUrl(form.file_path, form.id)}
                  alt="Scanned form"
                  style={{ maxWidth: '100%', height: 'auto', display: 'block' }}
                  onError={(e) => {
                    // Fallback to preview endpoint
                    const img = e.target as HTMLImageElement;
                    if (form.id && !img.src.includes('/api/preview/')) {
                      img.src = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/preview/${form.id}`;
                    }
                  }}
                />
              )}
            </div>
            
            {form.extracted_data && (
              <div className="extracted-text" style={{ marginTop: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <h4>Extracted Text (Raw)</h4>
                  {form.extracted_data?.raw_text && (
                    <button
                      onClick={handleApplyParsedData}
                      className="btn btn-sm btn-secondary"
                      style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                    >
                      🔄 Auto-fill Fields
                    </button>
                  )}
                </div>
                <div className="raw-text-box">
                  {form.extracted_data.raw_text || 'No text extracted'}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="data-section" style={{ gridColumn: form ? 'auto' : '1 / -1' }}>
          <h3>Student Information</h3>
          <div className="form-editor" style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}>
            
            {/* Academic & Admission Details */}
            <div className="form-section">
              <h4 className="form-section-title">Academic & Admission Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label>Academic Session</label>
                  <input type="text" className="input" value={verification.academic_session || ''} onChange={(e) => handleChange('academic_session', e.target.value)} placeholder="2025-2026" />
                </div>
                <div className="form-row">
                  <label>Course</label>
                  <select className="input" value={verification.course || ''} onChange={(e) => handleChange('course', e.target.value)}>
                    <option value="">Select Course</option>
                    <option value="B.COM.(H)">B.COM.(H)</option>
                    <option value="B.A.(H) ECO">B.A.(H) ECO</option>
                  </select>
                </div>
                <div className="form-row">
                  <label>Admission Category</label>
                  <select className="input" value={verification.admission_category || ''} onChange={(e) => handleChange('admission_category', e.target.value)}>
                    <option value="">Select Category</option>
                    <option value="GEN">GEN</option>
                    <option value="OBC">OBC</option>
                    <option value="SC">SC</option>
                    <option value="ST">ST</option>
                    <option value="EWS">EWS</option>
                    <option value="PWD">PWD</option>
                    <option value="Sports">Sports</option>
                    <option value="Foreign">Foreign</option>
                    <option value="CW">CW</option>
                    <option value="KM">KM</option>
                    <option value="Others">Others</option>
                  </select>
                </div>
                <div className="form-row">
                  <label>Other Category (Specify)</label>
                  <input type="text" className="input" value={verification.admission_category_other || ''} onChange={(e) => handleChange('admission_category_other', e.target.value)} placeholder="If Others selected" />
                </div>
                <div className="form-row">
                  <label>DU Portal Form No.</label>
                  <input type="text" className="input" value={verification.du_portal_form_number || ''} onChange={(e) => handleChange('du_portal_form_number', e.target.value)} placeholder="Form Number" />
                </div>
                <div className="form-row">
                  <label>CUET Score</label>
                  <input type="text" className="input" value={verification.cuet_score || ''} onChange={(e) => handleChange('cuet_score', e.target.value)} placeholder="e.g. 851.147" />
                </div>
                <div className="form-row">
                  <label>College Roll No.</label>
                  <input type="text" className="input" value={verification.college_roll_no || ''} onChange={(e) => handleChange('college_roll_no', e.target.value)} placeholder="Roll No" />
                </div>
                <div className="form-row">
                  <label>Date of Admission</label>
                  <input type="text" className="input" value={verification.date_of_admission || ''} onChange={(e) => handleChange('date_of_admission', e.target.value)} placeholder="DD/MM/YYYY" />
                </div>
              </div>
            </div>

            {/* Basic Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Personal Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label>First Name *</label>
                  <input type="text" className="input" value={verification.first_name || ''} onChange={(e) => handleChange('first_name', e.target.value)} placeholder="First Name" />
                </div>
                <div className="form-row">
                  <label>Middle Name</label>
                  <input type="text" className="input" value={verification.middle_name || ''} onChange={(e) => handleChange('middle_name', e.target.value)} placeholder="Middle Name" />
                </div>
                <div className="form-row">
                  <label>Surname *</label>
                  <input type="text" className="input" value={verification.surname || ''} onChange={(e) => handleChange('surname', e.target.value)} placeholder="Surname" />
                </div>
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label>Full Name (Auto)</label>
                  <input 
                    type="text" 
                    value={[verification.first_name, verification.middle_name, verification.surname].filter(Boolean).join(' ') || verification.student_name || ''} 
                    readOnly
                    style={{ backgroundColor: '#f5f5f5' }}
                  />
                </div>
                <div className="form-row">
                  <label>Date of Birth</label>
                  <input type="text" className="input" value={verification.date_of_birth || ''} onChange={(e) => handleChange('date_of_birth', e.target.value)} placeholder="DD/MM/YYYY" />
                </div>
                <div className="form-row">
                  <label>Gender</label>
                  <select className="input" value={verification.gender || ''} onChange={(e) => handleChange('gender', e.target.value)}>
                    <option value="">Select</option>
                    <option value="MALE">Male</option>
                    <option value="FEMALE">Female</option>
                    <option value="TRANSGENDER">Transgender</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div className="form-row">
                  <label>Nationality</label>
                  <input type="text" className="input" value={verification.nationality || ''} onChange={(e) => handleChange('nationality', e.target.value)} placeholder="Nationality" />
                </div>
                <div className="form-row">
                  <label>Religion</label>
                  <input type="text" className="input" value={verification.religion || ''} onChange={(e) => handleChange('religion', e.target.value)} placeholder="Religion" />
                </div>
                <div className="form-row">
                  <label>Aadhar Number</label>
                  <input type="text" className="input" value={verification.aadhar_number || ''} onChange={(e) => handleChange('aadhar_number', e.target.value)} placeholder="Aadhar Number" />
                </div>
                <div className="form-row">
                  <label>Blood Group</label>
                  <select className="input" value={verification.blood_group || ''} onChange={(e) => handleChange('blood_group', e.target.value)}>
                    <option value="">Select</option>
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                  </select>
                </div>
                <div className="form-row">
                  <label>Below Poverty Line</label>
                  <select className="input" value={verification.below_poverty_line || ''} onChange={(e) => handleChange('below_poverty_line', e.target.value)}>
                    <option value="">Select</option>
                    <option value="YES">Yes</option>
                    <option value="NO">No</option>
                  </select>
                </div>
                <div className="form-row">
                  <label>Annual Family Income</label>
                  <input type="text" className="input" value={verification.annual_income || ''} onChange={(e) => handleChange('annual_income', e.target.value)} placeholder="Annual Income" />
                </div>
                <div className="form-row">
                  <label>Minority Category</label>
                  <input type="text" className="input" value={verification.minority_category || ''} onChange={(e) => handleChange('minority_category', e.target.value)} placeholder="e.g. Muslim, Jain, Sikh" />
                </div>
              </div>
            </div>

            {/* Address Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Address Details</h4>
              <div className="form-grid">
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label>Permanent Address</label>
                  <textarea className="input" value={verification.permanent_address || ''} onChange={(e) => handleChange('permanent_address', e.target.value)} placeholder="Permanent Address" rows={3} />
                </div>
                <div className="form-row">
                  <label>Permanent State</label>
                  <input type="text" className="input" value={verification.permanent_state || ''} onChange={(e) => handleChange('permanent_state', e.target.value)} placeholder="State" />
                </div>
                <div className="form-row">
                  <label>Permanent PIN</label>
                  <input type="text" className="input" value={verification.permanent_pincode || ''} onChange={(e) => handleChange('permanent_pincode', e.target.value)} placeholder="PIN Code" />
                </div>
                
                <div className="form-row" style={{ gridColumn: '1 / -1', marginTop: '1rem' }}>
                  <label>Correspondence Address</label>
                  <textarea className="input" value={verification.correspondence_address || ''} onChange={(e) => handleChange('correspondence_address', e.target.value)} placeholder="Correspondence Address" rows={3} />
                </div>
                <div className="form-row">
                  <label>Correspondence State</label>
                  <input type="text" className="input" value={verification.correspondence_state || ''} onChange={(e) => handleChange('correspondence_state', e.target.value)} placeholder="State" />
                </div>
                <div className="form-row">
                  <label>Correspondence PIN</label>
                  <input type="text" className="input" value={verification.correspondence_pincode || ''} onChange={(e) => handleChange('correspondence_pincode', e.target.value)} placeholder="PIN Code" />
                </div>
              </div>
            </div>

            {/* Contact Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Contact Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label>Email</label>
                  <input type="email" className="input" value={verification.email || ''} onChange={(e) => handleChange('email', e.target.value)} placeholder="Student Email" />
                </div>
                <div className="form-row">
                  <label>Phone Number</label>
                  <input type="text" className="input" value={verification.phone_number || ''} onChange={(e) => handleChange('phone_number', e.target.value)} placeholder="Phone Number" />
                </div>
                <div className="form-row">
                  <label>Alternate Phone</label>
                  <input type="text" className="input" value={verification.alternate_phone || ''} onChange={(e) => handleChange('alternate_phone', e.target.value)} placeholder="Alternate Phone" />
                </div>
              </div>
            </div>

            {/* Parent Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Mother's Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label>Mother's Name</label>
                  <input type="text" className="input" value={verification.mother_name || ''} onChange={(e) => handleChange('mother_name', e.target.value)} placeholder="Mother's Name" />
                </div>
                <div className="form-row">
                  <label>Occupation</label>
                  <input type="text" className="input" value={verification.mother_occupation || ''} onChange={(e) => handleChange('mother_occupation', e.target.value)} placeholder="Occupation" />
                </div>
                <div className="form-row">
                  <label>Designation</label>
                  <input type="text" className="input" value={verification.mother_designation || ''} onChange={(e) => handleChange('mother_designation', e.target.value)} placeholder="Designation" />
                </div>
                <div className="form-row">
                  <label>Organization</label>
                  <input type="text" className="input" value={verification.mother_organization || ''} onChange={(e) => handleChange('mother_organization', e.target.value)} placeholder="Organization" />
                </div>
                <div className="form-row">
                  <label>Mother's Email</label>
                  <input type="email" className="input" value={verification.mother_email || ''} onChange={(e) => handleChange('mother_email', e.target.value)} placeholder="Email" />
                </div>
                <div className="form-row">
                  <label>Mother's Mobile</label>
                  <input type="text" className="input" value={verification.mother_mobile || ''} onChange={(e) => handleChange('mother_mobile', e.target.value)} placeholder="Mobile No." />
                </div>
              </div>

              <h4 className="form-section-title" style={{ marginTop: '1.5rem' }}>Father's Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label>Father's Name</label>
                  <input type="text" className="input" value={verification.father_name || ''} onChange={(e) => handleChange('father_name', e.target.value)} placeholder="Father's Name" />
                </div>
                <div className="form-row">
                  <label>Occupation</label>
                  <input type="text" className="input" value={verification.father_occupation || ''} onChange={(e) => handleChange('father_occupation', e.target.value)} placeholder="Occupation" />
                </div>
                <div className="form-row">
                  <label>Designation</label>
                  <input type="text" className="input" value={verification.father_designation || ''} onChange={(e) => handleChange('father_designation', e.target.value)} placeholder="Designation" />
                </div>
                <div className="form-row">
                  <label>Organization</label>
                  <input type="text" className="input" value={verification.father_organization || ''} onChange={(e) => handleChange('father_organization', e.target.value)} placeholder="Organization" />
                </div>
                <div className="form-row">
                  <label>Father's Email</label>
                  <input type="email" className="input" value={verification.father_email || ''} onChange={(e) => handleChange('father_email', e.target.value)} placeholder="Email" />
                </div>
                <div className="form-row">
                  <label>Father's Mobile</label>
                  <input type="text" className="input" value={verification.father_mobile || ''} onChange={(e) => handleChange('father_mobile', e.target.value)} placeholder="Mobile No." />
                </div>
              </div>
            </div>
            
            {/* Local Guardian Details */}
            <div className="form-section">
              <h4 className="form-section-title">Local Guardian's Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label>Guardian Name</label>
                  <input type="text" className="input" value={verification.guardian_name || ''} onChange={(e) => handleChange('guardian_name', e.target.value)} placeholder="Name" />
                </div>
                <div className="form-row">
                  <label>Residential Address</label>
                  <input type="text" className="input" value={verification.guardian_residential_address || ''} onChange={(e) => handleChange('guardian_residential_address', e.target.value)} placeholder="Address" />
                </div>
                <div className="form-row">
                  <label>Organization</label>
                  <input type="text" className="input" value={verification.guardian_organization || ''} onChange={(e) => handleChange('guardian_organization', e.target.value)} placeholder="Organization" />
                </div>
                <div className="form-row">
                  <label>Email</label>
                  <input type="email" className="input" value={verification.guardian_email || ''} onChange={(e) => handleChange('guardian_email', e.target.value)} placeholder="Email" />
                </div>
                <div className="form-row">
                  <label>Mobile Number</label>
                  <input type="text" className="input" value={verification.guardian_mobile || ''} onChange={(e) => handleChange('guardian_mobile', e.target.value)} placeholder="Mobile No." />
                </div>
              </div>
            </div>

            {/* CUET Marks Section */}
            <div className="form-section">
              <h4 className="form-section-title">CUET Marks</h4>
              <div className="form-grid" style={{ gridTemplateColumns: '1fr 100px 100px' }}>
                <div className="form-row"><strong>Subject</strong></div>
                <div className="form-row"><strong>Total</strong></div>
                <div className="form-row"><strong>Obtained</strong></div>
                
                {[1, 2, 3, 4, 5, 6].map(i => (
                  <div key={i} style={{ display: 'contents' }}>
                    <input type="text" className="input" value={(verification as any)[`cuet_subject_${i}`] || ''} onChange={(e) => handleChange(`cuet_subject_${i}` as any, e.target.value)} placeholder={`Subject ${i}`} />
                    <input type="text" className="input" value={(verification as any)[`cuet_total_score_${i}`] || ''} onChange={(e) => handleChange(`cuet_total_score_${i}` as any, e.target.value)} placeholder="Total" />
                    <input type="text" className="input" value={(verification as any)[`cuet_score_obtained_${i}`] || ''} onChange={(e) => handleChange(`cuet_score_obtained_${i}` as any, e.target.value)} placeholder="Score" />
                  </div>
                ))}
                
                <div style={{ gridColumn: '1 / -1', marginTop: '10px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '10px' }}>
                  <strong>Total CUET Score:</strong>
                  <input
                    type="text"
                    value={(() => {
                      // Calculate sum of all obtained scores from subjects above (supports decimals)
                      let total = 0;
                      for (let i = 1; i <= 6; i++) {
                        const score = (verification as any)[`cuet_score_obtained_${i}`];
                        if (score) {
                          const num = parseFloat(score);
                          if (!isNaN(num)) total += num;
                        }
                      }
                      // Format: show decimals only if present
                      if (total > 0) {
                        return total % 1 === 0 ? String(total) : total.toFixed(3).replace(/\.?0+$/, '');
                      }
                      return verification.cuet_score || '';
                    })()}
                    onChange={(e) => handleChange('cuet_score', e.target.value)}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#e8f5e9',
                      borderRadius: '4px',
                      fontWeight: 'bold',
                      width: '80px',
                      textAlign: 'center',
                      border: '1px solid #c8e6c9'
                    }}
                  />
                  <span style={{ fontSize: '11px', color: '#666' }}>= sum of obtained</span>
                </div>
              </div>
            </div>

            {/* Qualifying Exam Section */}
            <div className="form-section">
              <h4 className="form-section-title">Qualifying Examination (Class XII)</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label>Year of Passing</label>
                  <input type="text" className="input" value={verification.twelfth_year || ''} onChange={(e) => handleChange('twelfth_year', e.target.value)} placeholder="Year" />
                </div>
                <div className="form-row">
                  <label>Board/University</label>
                  <input type="text" className="input" value={verification.twelfth_board || ''} onChange={(e) => handleChange('twelfth_board', e.target.value)} placeholder="Board" />
                </div>
                <div className="form-row">
                  <label>Exam Roll No.</label>
                  <input type="text" className="input" value={verification.twelfth_roll_number || ''} onChange={(e) => handleChange('twelfth_roll_number', e.target.value)} placeholder="Roll No" />
                </div>
                <div className="form-row">
                  <label>Institution Last Attended</label>
                  <input type="text" className="input" value={verification.twelfth_institution || ''} onChange={(e) => handleChange('twelfth_institution', e.target.value)} placeholder="School Name" />
                </div>
                <div className="form-row">
                  <label>Hindi Studied Upto</label>
                  <select className="input" value={verification.hindi_studied_upto || ''} onChange={(e) => handleChange('hindi_studied_upto', e.target.value)}>
                    <option value="">Select</option>
                    <option value="VIII">VIII</option>
                    <option value="X">X</option>
                    <option value="XII">XII</option>
                    <option value="NEVER">Never</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Other Information & Certificate */}
            <div className="form-section">
              <h4 className="form-section-title">Other Information & Certificates</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label>DU Enrollment No.</label>
                  <input type="text" className="input" value={verification.du_enrollment_number || ''} onChange={(e) => handleChange('du_enrollment_number', e.target.value)} placeholder="Enrollment No" />
                </div>
                <div className="form-row">
                  <label>Hindi Medium Pref.</label>
                  <select className="input" value={verification.hindi_medium_preference || ''} onChange={(e) => handleChange('hindi_medium_preference', e.target.value)}>
                    <option value="">Select</option>
                    <option value="YES">Yes</option>
                    <option value="NO">No</option>
                  </select>
                </div>
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label>Certificate Issuing Authority</label>
                  <input type="text" className="input" value={verification.category_certificate_authority || ''} onChange={(e) => handleChange('category_certificate_authority', e.target.value)} placeholder="Authority Name & Address" />
                </div>
                <div className="form-row">
                  <label>Certificate No.</label>
                  <input type="text" className="input" value={verification.category_certificate_number || ''} onChange={(e) => handleChange('category_certificate_number', e.target.value)} placeholder="Cert No" />
                </div>
                <div className="form-row">
                  <label>Date of Issue</label>
                  <input type="text" className="input" value={verification.category_certificate_date || ''} onChange={(e) => handleChange('category_certificate_date', e.target.value)} placeholder="DD/MM/YYYY" />
                </div>
              </div>
            </div>

            {/* Document Checklist */}
            <div className="form-section">
              <h4 className="form-section-title">📋 Document Checklist</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                {[
                  { key: 'doc_admission_form', label: 'Admission/Registration Form' },
                  { key: 'doc_undertaking_ragging', label: 'Anti-Ragging Undertaking' },
                  { key: 'doc_photographs', label: 'Photographs' },
                  { key: 'doc_cuet_scorecard', label: 'CUET Score Card' },
                  { key: 'doc_class_xii_marksheet', label: 'Class XII Mark Sheet' },
                  { key: 'doc_class_x_certificate', label: 'Class X Certificate' },
                  { key: 'doc_class_xii_certificate', label: 'Class XII Certificate' },
                  { key: 'doc_character_certificate', label: 'Character Certificate' },
                  { key: 'doc_transfer_certificate', label: 'Transfer/Migration Certificate' },
                  { key: 'doc_hindi_certificate', label: 'Hindi Certificate' },
                  { key: 'doc_caste_certificate', label: 'Caste/Category Certificate' },
                  { key: 'doc_sports_eca', label: 'Sports/ECA Certificates' },
                  { key: 'doc_originals', label: 'Original Documents' },
                  { key: 'doc_photo_id', label: 'Photo ID Proof' },
                ].map(({ key, label }) => {
                  const value = (verification as any)[key] || 'No';
                  const isChecked = value === 'Yes';
                  return (
                    <label 
                      key={key} 
                      style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '8px',
                        padding: '8px 12px',
                        backgroundColor: isChecked ? '#e8f5e9' : '#fff',
                        borderRadius: '4px',
                        border: `1px solid ${isChecked ? '#4caf50' : '#ddd'}`,
                        cursor: 'pointer'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(e) => handleChange(key as any, e.target.checked ? 'Yes' : 'No')}
                        style={{ width: '16px', height: '16px', accentColor: '#4caf50' }}
                      />
                      <span style={{ fontSize: '0.85rem', color: isChecked ? '#2e7d32' : '#666' }}>
                        {label}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Documents Section */}
            <div className="form-section">
              <h4 className="form-section-title">📎 Attached Documents</h4>
              {profile && (
                <>
                  <DocumentUpload
                    studentProfileId={profile.id}
                    onUploadComplete={() => loadStudentData(parseInt(id!))}
                  />
                  
                  {(() => {
                    const allDocs = getAllDocuments(profile);
                    if (allDocs.length === 0) {
                      return <p style={{ color: '#666', fontSize: '0.9rem', marginTop: '1rem' }}>No documents attached yet.</p>;
                    }
                    
                    const apiUrl = 'http://localhost:8000';
                    return (
                      <div style={{ marginTop: '1rem', display: 'grid', gap: '0.75rem' }}>
                        {allDocs.map((doc, index) => {
                          const displayName = verification.du_portal_form_number || verification.du_enrollment_number
                            ? `${verification.du_portal_form_number || verification.du_enrollment_number}_${(verification.student_name || 'document').replace(/\s+/g, '_')}_${index + 1}.pdf`
                            : doc.filename;
                          
                          return (
                            <div 
                              key={`${doc.id}-${index}`}
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                padding: '0.75rem 1rem',
                                backgroundColor: '#f8f9fa',
                                borderRadius: '8px',
                                border: '1px solid #e0e0e0'
                              }}
                            >
                              <div>
                                <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>{displayName}</div>
                                <div style={{ fontSize: '0.75rem', color: '#666' }}>
                                  {doc.sourceLabel} • {(doc.file_size / 1024).toFixed(1)} KB
                                </div>
                              </div>
                              <div style={{ display: 'flex', gap: '1rem' }}>
                                <a 
                                  href={`${apiUrl}/uploads/${doc.file_path}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{ color: '#1976d2', fontSize: '0.85rem', textDecoration: 'none' }}
                                >
                                  View
                                </a>
                                <a 
                                  href={`${apiUrl}/uploads/${doc.file_path}`}
                                  download={displayName}
                                  style={{ color: '#388e3c', fontSize: '0.85rem', textDecoration: 'none' }}
                                >
                                  Download
                                </a>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}
                </>
              )}
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}

export default StudentEditView;
