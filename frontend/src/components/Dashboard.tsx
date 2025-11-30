import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiService, FormDetail } from '../services/api';
import './Dashboard.css';

function Dashboard() {
  const [forms, setForms] = useState<FormDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    verified: 0,
    pending: 0,
    documents: 0,
    students: 0,
  });

  useEffect(() => {
    loadForms();
  }, []);

  const loadForms = async () => {
    try {
      setLoading(true);
      const data = await apiService.listForms(0, 10);
      setForms(data);
      
      // Calculate stats
      const allForms = await apiService.listForms(0, 1000);
      
      // Count documents
      let documentCount = 0;
      try {
        const documents = await apiService.searchDocuments({ page: 1, limit: 1000 });
        documentCount = documents.length;
      } catch (err) {
        console.error('Failed to load documents:', err);
      }
      
      // Count students
      let studentCount = 0;
      try {
        const students = await apiService.listStudentProfiles(0, 1000);
        studentCount = students.length;
      } catch (err) {
        console.error('Failed to load students:', err);
      }
      
      setStats({
        total: allForms.length,
        verified: allForms.filter(f => f.status === 'verified').length,
        pending: allForms.filter(f => f.status === 'extracted').length,
        documents: documentCount,
        students: studentCount,
      });
    } catch (error) {
      console.error('Failed to load forms:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (formId: number, filename: string) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await apiService.deleteForm(formId);
      await loadForms(); // Reload the list
      alert('Form deleted successfully');
    } catch (error: any) {
      alert(`Failed to delete form: ${error.response?.data?.detail || error.message}`);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusMap: { [key: string]: { label: string; class: string } } = {
      uploaded: { label: 'Uploaded', class: 'status-uploaded' },
      extracting: { label: 'Extracting', class: 'status-extracting' },
      extracted: { label: 'Pending Verification', class: 'status-extracted' },
      verified: { label: 'Verified', class: 'status-verified' },
      error: { label: 'Error', class: 'status-error' },
    };
    const statusInfo = statusMap[status] || { label: status, class: 'status-unknown' };
    return <span className={`status-badge ${statusInfo.class}`}>{statusInfo.label}</span>;
  };

  const overviewStats = [
    {
      label: 'Total Forms',
      value: stats.total,
      description: 'Overall submissions received this cycle',
    },
    {
      label: 'Verified',
      value: stats.verified,
      description: 'Applications cleared for enrollment',
    },
    {
      label: 'Pending Verification',
      value: stats.pending,
      description: 'Awaiting manual review and confirmation',
    },
    {
      label: 'Supporting Documents',
      value: stats.documents,
      description: 'Files on record across all applicants',
    },
    {
      label: 'Student Profiles',
      value: stats.students,
      description: 'Applicants actively tracked in the system',
    },
  ];

  const currentYear = new Date().getFullYear();
  const nextYear = currentYear + 1;

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div className="dashboard">
      <section className="dashboard-hero">
        <div className="hero-content">
          <p className="hero-eyebrow">Admissions Cycle {currentYear} – {nextYear}</p>
          <h1>Admissions Command Center</h1>
          <p className="hero-copy">
            Monitor intake momentum, track verification progress, and coordinate applicant follow-up
            — all from a single, college-ready workspace.
          </p>
          <div className="hero-actions">
            <Link to="/upload" className="btn btn-primary">
              Upload New Form
            </Link>
            <Link to="/search" className="btn btn-outline">
              Advanced Search
            </Link>
          </div>
        </div>
        <div className="hero-summary">
          <div className="summary-card">
            <span className="summary-label">Verified</span>
            <span className="summary-value">{stats.verified}</span>
            <span className="summary-description">Students cleared for onboarding</span>
          </div>
          <div className="summary-card">
            <span className="summary-label">Pending Review</span>
            <span className="summary-value">{stats.pending}</span>
            <span className="summary-description">Awaiting quality checks</span>
          </div>
          <div className="summary-card">
            <span className="summary-label">Documents on File</span>
            <span className="summary-value">{stats.documents}</span>
            <span className="summary-description">Supporting records archived</span>
          </div>
        </div>
      </section>

      <div className="stats-grid">
        {overviewStats.map((item) => (
          <div className="stat-card" key={item.label}>
            <span className="stat-chip">{item.label}</span>
            <div className="stat-value">{item.value}</div>
            <p className="stat-description">{item.description}</p>
          </div>
        ))}
      </div>

      <div className="recent-forms">
        <div className="recent-header">
          <div>
            <h3>Recent Form Activity</h3>
            <p className="recent-subtitle">
              Latest submissions across the admissions cycle, ready for review or follow-up.
            </p>
          </div>
          <div className="recent-actions">
            <Link to="/upload" className="btn btn-secondary">
              Upload Files
            </Link>
            <Link to="/search" className="btn btn-link">
              View all records →
            </Link>
          </div>
        </div>

        {forms.length === 0 ? (
          <div className="empty-state">
            <p>No forms uploaded yet.</p>
            <Link to="/upload" className="btn btn-primary">
              Upload Your First Form
            </Link>
          </div>
        ) : (
          <table className="forms-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Filename</th>
                <th>Student Name</th>
                <th>Status</th>
                <th>Upload Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {forms.map((form) => (
                <tr key={form.id}>
                  <td>{form.id}</td>
                  <td>{form.filename}</td>
                  <td>{form.student_name || '-'}</td>
                  <td>{getStatusBadge(form.status)}</td>
                  <td>{new Date(form.upload_date).toLocaleDateString()}</td>
                  <td>
                    <div className="action-buttons">
                      <Link to={`/forms/${form.id}`} className="btn btn-sm btn-secondary">
                        View
                      </Link>
                      <button
                        onClick={() => handleDelete(form.id, form.filename)}
                        className="btn btn-sm btn-danger"
                        title="Delete form"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default Dashboard;

