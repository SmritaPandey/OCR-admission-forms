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

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Dashboard</h2>
        <Link to="/upload" className="btn btn-primary">
          Upload New Form
        </Link>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.total}</div>
          <div className="stat-label">Total Forms</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.verified}</div>
          <div className="stat-label">Verified</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.pending}</div>
          <div className="stat-label">Pending Verification</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.documents}</div>
          <div className="stat-label">Documents</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.students}</div>
          <div className="stat-label">Student Profiles</div>
        </div>
      </div>

      <div className="recent-forms">
        <h3>Recent Forms</h3>
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

