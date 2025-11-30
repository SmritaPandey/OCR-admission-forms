import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { apiService, StudentProfileDetail } from '../services/api';
import DocumentUpload from './DocumentUpload';
import DocumentList from './DocumentList';
import './StudentProfile.css';

function StudentProfile() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<StudentProfileDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    return <div className="student-profile loading">Loading student profile...</div>;
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

  return (
    <div className="student-profile">
      <section className="profile-hero">
        <div className="hero-details">
          <button onClick={() => navigate(-1)} className="btn btn-outline back-btn">
            ← Back
          </button>
          <span className="page-eyebrow">Student Record</span>
          <h1>{profile.student_name}</h1>
          <p>
            Centralized profile of supporting documents, verification history, and admission forms for
            this applicant. Track outstanding actions and upload additional paperwork without leaving
            the admissions console.
          </p>
          <div className="hero-meta">
            <div className="meta-item">
              <span className="meta-label">Profile Created</span>
              <span className="meta-value">
                {new Date(profile.created_date).toLocaleDateString()}
              </span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Last Updated</span>
              <span className="meta-value">
                {new Date(profile.updated_date).toLocaleDateString()}
              </span>
            </div>
            {profile.aadhar_number && (
              <div className="meta-item">
                <span className="meta-label">Aadhar</span>
                <span className="meta-value">{profile.aadhar_number}</span>
              </div>
            )}
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
            <span className="stat-value">{profile.documents_count}</span>
            <span className="stat-description">Archived for compliance</span>
          </div>
        </div>
      </section>

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
          <span className="section-count">{profile.forms.length} total</span>
        </header>

        {profile.forms.length === 0 ? (
          <div className="empty-state">
            No forms found for this student. Upload a form from the documents section below.
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
                  {form.student_name && (
                    <div>
                      <dt>Student</dt>
                      <dd>{form.student_name}</dd>
                    </div>
                  )}
                  {form.course_applied && (
                    <div>
                      <dt>Course</dt>
                      <dd>{form.course_applied}</dd>
                    </div>
                  )}
                  <div>
                    <dt>Provider</dt>
                    <dd>{form.ocr_provider}</dd>
                  </div>
                </dl>
                {form.documents && form.documents.length > 0 && (
                  <footer className="form-card-footer">
                    {form.documents.length} supporting document
                    {form.documents.length === 1 ? '' : 's'} attached
                  </footer>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="profile-section">
        <header className="section-header">
          <div>
            <h2>Supporting Documents</h2>
            <p>
              Upload new files or manage existing documentation linked to this student profile. These
              assets remain accessible during verification and auditing.
            </p>
          </div>
          <span className="section-count">{profile.documents.length} total</span>
        </header>
        <div className="documents-panel">
          <DocumentUpload
            studentProfileId={profile.id}
            onUploadComplete={handleRefresh}
          />
          <DocumentList
            studentProfileId={profile.id}
            onRefresh={handleRefresh}
          />
        </div>
      </section>
    </div>
  );
}

export default StudentProfile;

