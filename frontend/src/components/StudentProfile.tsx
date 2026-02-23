import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { apiService, StudentProfileDetail, FormDetail, Document } from '../services/api';
import DocumentUpload from './DocumentUpload';
import './StudentProfile.css';

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

// Helper to get the latest verified or extracted form
const getLatestForm = (forms: FormDetail[]): FormDetail | null => {
  if (forms.length === 0) return null;

  // Prefer verified forms, then extracted, then any
  const verified = forms.filter(f => f.status === 'verified');
  if (verified.length > 0) return verified[0];

  const extracted = forms.filter(f => f.status === 'extracted');
  if (extracted.length > 0) return extracted[0];

  return forms[0];
};

// Helper to get all documents from profile and forms
const getAllDocuments = (profile: StudentProfileDetail): Document[] => {
  const profileDocs = profile.documents || [];
  const formDocs = profile.forms.flatMap(form => form.documents || []);

  // Deduplicate by id
  const seen = new Set<number>();
  const allDocs: Document[] = [];
  [...profileDocs, ...formDocs].forEach(doc => {
    if (!seen.has(doc.id)) {
      seen.add(doc.id);
      allDocs.push(doc);
    }
  });

  return allDocs;
};

// Detail row component
const DetailRow = ({ label, value }: { label: string; value?: string | null }) => {
  if (!value) return null;
  return (
    <div className="detail-row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
};

function StudentProfile() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<StudentProfileDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'forms' | 'documents'>('overview');

  useEffect(() => {
    if (id) {
      loadProfile(parseInt(id));
    }
  }, [id]);

  const loadProfile = async (profileId: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getStudentProfile(profileId);
      setProfile(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load student profile');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    if (id) {
      loadProfile(parseInt(id));
    }
  };

  if (loading) {
    return (
      <div className="student-profile loading">
        <div className="spinner"></div>
        <p>Loading student profile...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="student-profile error">
        <p>{error}</p>
        <button onClick={() => navigate('/search')} className="btn btn-primary">
          Back to Search
        </button>
      </div>
    );
  }

  if (!profile) {
    return <div className="student-profile error">Student profile not found</div>;
  }

  const latestForm = getLatestForm(profile.forms);
  const allDocuments = getAllDocuments(profile);

  return (
    <div className="student-profile">
      {/* Hero Section */}
      <section className="profile-hero">
        <div className="hero-details">
          <div className="hero-nav">
            <button onClick={() => navigate(-1)} className="btn btn-outline back-btn">
              ← Back
            </button>
            <button onClick={() => navigate(`/students/${id}/edit`)} className="btn btn-primary edit-btn">
              ✏️ Edit Profile
            </button>
            <button
              onClick={async () => {
                if (window.confirm(`Are you sure you want to permanently delete profile for "${profile.student_name}"?`)) {
                  try {
                    await apiService.deleteStudentProfile(profile.id);
                    navigate('/students');
                  } catch (err) {
                    alert('Failed to delete student profile');
                  }
                }
              }}
              className="btn btn-danger delete-btn"
              style={{ marginLeft: '10px' }}
            >
              🗑️ Delete Profile
            </button>
          </div>
          <span className="page-eyebrow">Student Record</span>
          <h1>{profile.student_name}</h1>

          <div className="hero-meta">
            {latestForm?.course && (
              <div className="meta-item">
                <span className="meta-label">Course</span>
                <span className="meta-value">{latestForm.course}</span>
              </div>
            )}
            {latestForm?.college_roll_no && (
              <div className="meta-item">
                <span className="meta-label">Roll No</span>
                <span className="meta-value">{latestForm.college_roll_no}</span>
              </div>
            )}
            {profile.aadhar_number && (
              <div className="meta-item">
                <span className="meta-label">Aadhar</span>
                <span className="meta-value">{profile.aadhar_number}</span>
              </div>
            )}
            <div className="meta-item">
              <span className="meta-label">Profile Created</span>
              <span className="meta-value">
                {new Date(profile.created_date).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>
        <div className="hero-stats">
          <div className="stat-card">
            <span className="stat-chip">Admission Forms</span>
            <span className="stat-value">{profile.forms_count}</span>
            <span className="stat-description">Uploaded across all cycles</span>
          </div>
          <div className="stat-card">
            <span className="stat-chip">Supporting Docs</span>
            <span className="stat-value">{allDocuments.length}</span>
            <span className="stat-description">Archived for compliance</span>
          </div>
        </div>
      </section>

      {/* Tab Navigation */}
      <div className="profile-tabs">
        <button
          className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={`tab-btn ${activeTab === 'forms' ? 'active' : ''}`}
          onClick={() => setActiveTab('forms')}
        >
          Forms ({profile.forms.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveTab('documents')}
        >
          Documents ({allDocuments.length})
        </button>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && latestForm && (
        <div className="profile-overview">
          {/* Personal Details */}
          <section className="details-card">
            <h3>Personal Details</h3>
            <dl className="details-grid">
              <DetailRow label="Full Name" value={latestForm.student_name} />
              <DetailRow label="First Name" value={latestForm.first_name} />
              <DetailRow label="Middle Name" value={latestForm.middle_name} />
              <DetailRow label="Surname" value={latestForm.surname} />
              <DetailRow label="Date of Birth" value={latestForm.date_of_birth} />
              <DetailRow label="Gender" value={latestForm.gender} />
              <DetailRow label="Category" value={latestForm.category || latestForm.admission_category} />
              <DetailRow label="Nationality" value={latestForm.nationality} />
              <DetailRow label="Religion" value={latestForm.religion} />
              <DetailRow label="Aadhar Number" value={latestForm.aadhar_number} />
              <DetailRow label="Blood Group" value={latestForm.blood_group} />
            </dl>
          </section>

          {/* Contact Details */}
          <section className="details-card">
            <h3>Contact Details</h3>
            <dl className="details-grid">
              <DetailRow label="Phone Number" value={latestForm.phone_number} />
              <DetailRow label="Alternate Phone" value={latestForm.alternate_phone} />
              <DetailRow label="Email" value={latestForm.email} />
              <DetailRow label="Emergency Contact" value={latestForm.emergency_contact_name} />
              <DetailRow label="Emergency Phone" value={latestForm.emergency_contact_phone} />
            </dl>
          </section>

          {/* Address Details */}
          <section className="details-card">
            <h3>Address</h3>
            <dl className="details-grid two-cols">
              <div className="address-block">
                <h4>Permanent Address</h4>
                <DetailRow label="Line 1" value={latestForm.permanent_address_line1} />
                <DetailRow label="Line 2" value={latestForm.permanent_address_line2} />
                <DetailRow label="Line 3" value={latestForm.permanent_address_line3} />
                <DetailRow label="State" value={latestForm.permanent_state} />
                <DetailRow label="Pincode" value={latestForm.permanent_pincode} />
              </div>
              <div className="address-block">
                <h4>Correspondence Address</h4>
                <DetailRow label="Line 1" value={latestForm.correspondence_address_line1} />
                <DetailRow label="Line 2" value={latestForm.correspondence_address_line2} />
                <DetailRow label="Line 3" value={latestForm.correspondence_address_line3} />
                <DetailRow label="State" value={latestForm.correspondence_state} />
                <DetailRow label="Pincode" value={latestForm.correspondence_pincode} />
              </div>
            </dl>
          </section>

          {/* Academic Details */}
          <section className="details-card">
            <h3>Academic Details</h3>
            <dl className="details-grid">
              <DetailRow label="Course" value={latestForm.course} />
              <DetailRow label="Academic Session" value={latestForm.academic_session} />
              <DetailRow label="College Roll No" value={latestForm.college_roll_no} />
              <DetailRow label="DU Portal Form No" value={latestForm.du_portal_form_number} />
              <DetailRow label="DU Enrollment No" value={latestForm.du_enrollment_number} />
              <DetailRow label="Date of Admission" value={latestForm.date_of_admission} />
              <DetailRow label="Admission Category" value={latestForm.admission_category} />
            </dl>
          </section>

          {/* CUET Scores */}
          {(latestForm.cuet_score || latestForm.cuet_subject_1) && (
            <section className="details-card">
              <h3>CUET Scores</h3>
              <div className="cuet-table-container">
                <table className="cuet-table">
                  <thead>
                    <tr>
                      <th>Subject</th>
                      <th>Total</th>
                      <th>Obtained</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[1, 2, 3, 4, 5, 6].map(i => {
                      const subject = latestForm[`cuet_subject_${i}` as keyof FormDetail] as string;
                      const total = latestForm[`cuet_total_score_${i}` as keyof FormDetail] as string;
                      const obtained = latestForm[`cuet_score_obtained_${i}` as keyof FormDetail] as string;
                      if (!subject && !obtained) return null;
                      return (
                        <tr key={i}>
                          <td>{subject || '-'}</td>
                          <td>{total || '-'}</td>
                          <td>{obtained || '-'}</td>
                        </tr>
                      );
                    })}
                    <tr className="total-row">
                      <td><strong>Total CUET Score</strong></td>
                      <td></td>
                      <td><strong>{latestForm.cuet_score || latestForm.cuet_total_score || '-'}</strong></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* 12th Details */}
          <section className="details-card">
            <h3>Qualifying Examination (12th)</h3>
            <dl className="details-grid">
              <DetailRow label="Year" value={latestForm.twelfth_year} />
              <DetailRow label="Board" value={latestForm.twelfth_board} />
              <DetailRow label="School/Institution" value={latestForm.twelfth_school || latestForm.twelfth_institution} />
              <DetailRow label="Roll Number" value={latestForm.twelfth_roll_number} />
              <DetailRow label="Percentage" value={latestForm.twelfth_percentage} />
              <DetailRow label="Hindi Studied Upto" value={latestForm.hindi_studied_upto} />
            </dl>
          </section>

          {/* Parent/Guardian Details */}
          <section className="details-card">
            <h3>Parent / Guardian Details</h3>
            <dl className="details-grid three-cols">
              <div className="parent-block">
                <h4>Father</h4>
                <DetailRow label="Name" value={latestForm.father_name} />
                <DetailRow label="Occupation" value={latestForm.father_occupation} />
                <DetailRow label="Designation" value={latestForm.father_designation} />
                <DetailRow label="Organization" value={latestForm.father_organization} />
                <DetailRow label="Mobile" value={latestForm.father_mobile || latestForm.father_phone} />
                <DetailRow label="Email" value={latestForm.father_email} />
              </div>
              <div className="parent-block">
                <h4>Mother</h4>
                <DetailRow label="Name" value={latestForm.mother_name} />
                <DetailRow label="Occupation" value={latestForm.mother_occupation} />
                <DetailRow label="Designation" value={latestForm.mother_designation} />
                <DetailRow label="Organization" value={latestForm.mother_organization} />
                <DetailRow label="Mobile" value={latestForm.mother_mobile || latestForm.mother_phone} />
                <DetailRow label="Email" value={latestForm.mother_email} />
              </div>
              <div className="parent-block">
                <h4>Local Guardian</h4>
                <DetailRow label="Name" value={latestForm.guardian_name} />
                <DetailRow label="Relation" value={latestForm.guardian_relation} />
                <DetailRow label="Address" value={latestForm.guardian_residential_address} />
                <DetailRow label="Mobile" value={latestForm.guardian_mobile || latestForm.guardian_phone} />
                <DetailRow label="Email" value={latestForm.guardian_email} />
              </div>
            </dl>
          </section>

          {/* Other Details */}
          <section className="details-card">
            <h3>Other Information</h3>
            <dl className="details-grid">
              <DetailRow label="Annual Family Income" value={latestForm.annual_income} />
              <DetailRow label="Below Poverty Line" value={latestForm.below_poverty_line} />
              <DetailRow label="Minority Category" value={latestForm.minority_category} />
              <DetailRow label="Hindi Medium Preference" value={latestForm.hindi_medium_preference} />
              <DetailRow label="Disability Type" value={latestForm.disability_type} />
              <DetailRow label="Disability %" value={latestForm.disability_percentage} />
              <DetailRow label="UDID Number" value={latestForm.udid_number} />
            </dl>
          </section>
        </div>
      )}

      {activeTab === 'overview' && !latestForm && (
        <div className="profile-section">
          <div className="empty-state">
            <p>No form data available. Upload and verify a form to see student details.</p>
            <Link to="/upload" className="btn btn-primary">Upload Form</Link>
          </div>
        </div>
      )}

      {/* Forms Tab */}
      {activeTab === 'forms' && (
        <section className="profile-section">
          <header className="section-header">
            <div>
              <h2>Admission Forms</h2>
              <p>
                {profile.forms.length > 0
                  ? 'Review submission status and navigate directly to verification.'
                  : 'No forms on record yet. Upload a form to begin the digitization workflow.'}
              </p>
            </div>
            <Link to="/upload" className="btn btn-primary">+ Upload Form</Link>
          </header>

          {profile.forms.length === 0 ? (
            <div className="empty-state">
              No forms found for this student. Upload a form to get started.
            </div>
          ) : (
            <div className="forms-grid">
              {profile.forms.map((form) => (
                <article key={form.id} className="form-card">
                  <header className="form-card-header">
                    <div>
                      <h3>
                        <Link to={`/forms/${form.id}`}>{form.filename}</Link>
                      </h3>
                      <p>Uploaded {new Date(form.upload_date).toLocaleDateString()}</p>
                    </div>
                    <span className={`status-badge status-${form.status}`}>
                      {form.status}
                    </span>
                  </header>
                  <dl className="form-card-meta">
                    {form.course && (
                      <div>
                        <dt>Course</dt>
                        <dd>{form.course}</dd>
                      </div>
                    )}
                    {form.college_roll_no && (
                      <div>
                        <dt>Roll No</dt>
                        <dd>{form.college_roll_no}</dd>
                      </div>
                    )}
                    <div>
                      <dt>Provider</dt>
                      <dd>{form.ocr_provider}</dd>
                    </div>
                  </dl>
                  <footer className="form-card-actions">
                    <Link to={`/forms/${form.id}`} className="btn btn-sm btn-secondary">
                      View Details
                    </Link>
                    {form.status !== 'verified' && (
                      <Link to={`/forms/${form.id}`} className="btn btn-sm btn-primary">
                        Verify
                      </Link>
                    )}
                  </footer>
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <section className="profile-section">
          <header className="section-header">
            <div>
              <h2>Supporting Documents</h2>
              <p>
                Upload new files or manage existing documentation linked to this student profile.
              </p>
            </div>
            <span className="section-count">{allDocuments.length} total</span>
          </header>

          <div className="documents-panel">
            <DocumentUpload
              studentProfileId={profile.id}
              onUploadComplete={handleRefresh}
            />

            {/* Document Checklist from Form */}
            {latestForm && (
              <div className="details-card" style={{ marginTop: '1.5rem', marginBottom: '1.5rem' }}>
                <h3>📋 Document Checklist (from Form)</h3>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
                  gap: '8px',
                  padding: '12px',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '8px',
                  marginTop: '1rem'
                }}>
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
                    const value = (latestForm as any)[key] || 'No';
                    const isChecked = value === 'Yes';
                    return (
                      <div
                        key={key}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '8px 12px',
                          backgroundColor: isChecked ? '#e8f5e9' : '#fff',
                          borderRadius: '4px',
                          border: `1px solid ${isChecked ? '#4caf50' : '#ddd'}`,
                          fontSize: '13px'
                        }}
                      >
                        <span style={{ color: isChecked ? '#2e7d32' : '#666', fontWeight: isChecked ? 500 : 400 }}>
                          {isChecked ? '✓' : '○'} {label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {allDocuments.length === 0 ? (
              <div className="empty-state">
                No documents attached yet. Upload supporting documents above.
              </div>
            ) : (
              <div className="documents-grid">
                {allDocuments.map((doc) => (
                  <article key={doc.id} className="document-card">
                    <div className="document-icon">
                      {doc.filename.toLowerCase().endsWith('.pdf') ? '📄' : '🖼️'}
                    </div>
                    <div className="document-info">
                      <h4>{doc.filename}</h4>
                      <span className="document-category-badge">{doc.document_category}</span>
                      {doc.description && <p className="document-desc">{doc.description}</p>}
                      <div className="document-meta">
                        <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                        <span>{new Date(doc.upload_date).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="document-actions">
                      <a
                        href={`${API_BASE_URL}/uploads/${doc.file_path}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-sm btn-secondary"
                      >
                        View
                      </a>
                      <a
                        href={`${API_BASE_URL}/uploads/${doc.file_path}`}
                        download={doc.filename}
                        className="btn btn-sm btn-primary"
                      >
                        Download
                      </a>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}

export default StudentProfile;
