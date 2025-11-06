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
      <div className="profile-header">
        <button onClick={() => navigate(-1)} className="btn btn-secondary">
          ← Back
        </button>
        <h1>Student Profile: {profile.student_name}</h1>
      </div>

      <div className="profile-info">
        <div className="info-card">
          <h3>Basic Information</h3>
          <div className="info-grid">
            <div className="info-item">
              <label>Student Name:</label>
              <span>{profile.student_name}</span>
            </div>
            {profile.aadhar_number && (
              <div className="info-item">
                <label>Aadhar Number:</label>
                <span>{profile.aadhar_number}</span>
              </div>
            )}
            <div className="info-item">
              <label>Profile Created:</label>
              <span>{new Date(profile.created_date).toLocaleDateString()}</span>
            </div>
            <div className="info-item">
              <label>Last Updated:</label>
              <span>{new Date(profile.updated_date).toLocaleDateString()}</span>
            </div>
          </div>
        </div>

        <div className="stats-card">
          <h3>Statistics</h3>
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-value">{profile.forms_count}</div>
              <div className="stat-label">Forms</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{profile.documents_count}</div>
              <div className="stat-label">Documents</div>
            </div>
          </div>
        </div>
      </div>

      {/* Forms Section */}
      <div className="profile-section">
        <h2>Admission Forms ({profile.forms.length})</h2>
        {profile.forms.length === 0 ? (
          <p className="empty-message">No forms found for this student</p>
        ) : (
          <div className="forms-list">
            {profile.forms.map((form) => (
              <div key={form.id} className="form-card">
                <div className="form-header">
                  <h4>
                    <Link to={`/forms/${form.id}`}>{form.filename}</Link>
                  </h4>
                  <span className={`status-badge status-${form.status}`}>
                    {form.status}
                  </span>
                </div>
                <div className="form-meta">
                  <span>Uploaded: {new Date(form.upload_date).toLocaleDateString()}</span>
                  {form.student_name && <span>Student: {form.student_name}</span>}
                  {form.course_applied && <span>Course: {form.course_applied}</span>}
                </div>
                {form.documents && form.documents.length > 0 && (
                  <div className="form-documents">
                    <small>{form.documents.length} document(s) attached</small>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Documents Section */}
      <div className="profile-section">
        <h2>Student Documents ({profile.documents.length})</h2>
        <DocumentUpload
          studentProfileId={profile.id}
          onUploadComplete={handleRefresh}
        />
        <DocumentList
          studentProfileId={profile.id}
          onRefresh={handleRefresh}
        />
      </div>
    </div>
  );
}

export default StudentProfile;

