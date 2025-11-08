import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiService, FormDetail, Document, DocumentCategory } from '../services/api';
import './SearchInterface.css';

function SearchInterface() {
  const [activeTab, setActiveTab] = useState<'forms' | 'documents'>('forms');
  const [searchParams, setSearchParams] = useState({
    student_name: '',
    phone_number: '',
    email: '',
    enrollment_number: '',
    application_number: '',
    course_applied: '',
    status: '',
  });
  const [documentSearchParams, setDocumentSearchParams] = useState({
    document_category: '',
    student_name: '',
  });
  const [results, setResults] = useState<FormDetail[]>([]);
  const [documentResults, setDocumentResults] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [categories, setCategories] = useState<{ value: string; name: string }[]>([]);

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      const result = await apiService.getDocumentCategories();
      setCategories(result.categories);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setSearched(true);
      const data = await apiService.searchForms({
        ...searchParams,
        page: 1,
        limit: 50,
      });
      setResults(data);
    } catch (error) {
      console.error('Search failed:', error);
      alert('Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      const blob = await apiService.exportForms(format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `admission_forms.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed');
    }
  };

  const handleChange = (field: string, value: string) => {
    setSearchParams(prev => ({ ...prev, [field]: value }));
  };

  const handleDocumentSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setSearched(true);
      const data = await apiService.searchDocuments({
        ...documentSearchParams,
        document_category: documentSearchParams.document_category || undefined,
        page: 1,
        limit: 50,
      });
      setDocumentResults(data);
    } catch (error) {
      console.error('Document search failed:', error);
      alert('Search failed');
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
      // Remove from results
      setResults(results.filter(f => f.id !== formId));
      alert('Form deleted successfully');
    } catch (error: any) {
      alert(`Failed to delete form: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleDeleteDocument = async (documentId: number, filename: string) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await apiService.deleteDocument(documentId);
      setDocumentResults(documentResults.filter(d => d.id !== documentId));
      alert('Document deleted successfully');
    } catch (error: any) {
      alert(`Failed to delete document: ${error.response?.data?.detail || error.message}`);
    }
  };

  const getDocumentUrl = (filePath: string): string => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    return `${baseUrl}/uploads/${filePath}`;
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  return (
    <div className="search-interface">
      <div className="search-header">
        <h2>Search Database</h2>
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'forms' ? 'active' : ''}`}
            onClick={() => setActiveTab('forms')}
          >
            Forms
          </button>
          <button
            className={`tab ${activeTab === 'documents' ? 'active' : ''}`}
            onClick={() => setActiveTab('documents')}
          >
            Documents
          </button>
        </div>
        <div className="export-buttons">
          <button onClick={() => handleExport('csv')} className="btn btn-secondary">
            Export CSV
          </button>
          <button onClick={() => handleExport('json')} className="btn btn-secondary">
            Export JSON
          </button>
        </div>
      </div>

      <form onSubmit={handleSearch} className="search-form">
        <div className="search-grid">
          <div className="form-group">
            <label>Student Name</label>
            <input
              type="text"
              value={searchParams.student_name}
              onChange={(e) => handleChange('student_name', e.target.value)}
              placeholder="Search by name"
            />
          </div>

          <div className="form-group">
            <label>Phone Number</label>
            <input
              type="text"
              value={searchParams.phone_number}
              onChange={(e) => handleChange('phone_number', e.target.value)}
              placeholder="Search by phone"
            />
          </div>

          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={searchParams.email}
              onChange={(e) => handleChange('email', e.target.value)}
              placeholder="Search by email"
            />
          </div>

          <div className="form-group">
            <label>Enrollment Number</label>
            <input
              type="text"
              value={searchParams.enrollment_number}
              onChange={(e) => handleChange('enrollment_number', e.target.value)}
              placeholder="Search by enrollment"
            />
          </div>

          <div className="form-group">
            <label>Application Number</label>
            <input
              type="text"
              value={searchParams.application_number}
              onChange={(e) => handleChange('application_number', e.target.value)}
              placeholder="Search by application"
            />
          </div>

          <div className="form-group">
            <label>Course Applied</label>
            <input
              type="text"
              value={searchParams.course_applied}
              onChange={(e) => handleChange('course_applied', e.target.value)}
              placeholder="Search by course"
            />
          </div>

          <div className="form-group">
            <label>Status</label>
            <select
              value={searchParams.status}
              onChange={(e) => handleChange('status', e.target.value)}
            >
              <option value="">All</option>
              <option value="uploaded">Uploaded</option>
              <option value="extracted">Pending Verification</option>
              <option value="verified">Verified</option>
            </select>
          </div>
        </div>

        <button type="submit" disabled={loading} className="btn btn-primary btn-large">
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {searched && (
        <div className="search-results">
          <h3>Results ({results.length})</h3>
          {results.length === 0 ? (
            <div className="empty-results">
              No forms found matching your criteria.
            </div>
          ) : (
            <div className="results-table-container">
              <table className="results-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Student Name</th>
                    <th>Phone</th>
                    <th>Email</th>
                    <th>Course</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((form) => (
                    <tr key={form.id}>
                      <td>{form.id}</td>
                      <td>{form.student_name || '-'}</td>
                      <td>{form.phone_number || '-'}</td>
                      <td>{form.email || '-'}</td>
                      <td>{form.course_applied || '-'}</td>
                      <td>
                        <span className={`status-badge status-${form.status}`}>
                          {form.status}
                        </span>
                      </td>
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
            </div>
          )}
        </div>
      )}

      {activeTab === 'documents' && (
        <>
          <form onSubmit={handleDocumentSearch} className="search-form">
            <div className="search-grid">
              <div className="form-group">
                <label>Document Category</label>
                <select
                  value={documentSearchParams.document_category}
                  onChange={(e) => setDocumentSearchParams(prev => ({ ...prev, document_category: e.target.value }))}
                >
                  <option value="">All Categories</option>
                  {categories.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Student Name</label>
                <input
                  type="text"
                  value={documentSearchParams.student_name}
                  onChange={(e) => setDocumentSearchParams(prev => ({ ...prev, student_name: e.target.value }))}
                  placeholder="Search by student name"
                />
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn btn-primary btn-large">
              {loading ? 'Searching...' : 'Search Documents'}
            </button>
          </form>

          {searched && (
            <div className="search-results">
              <h3>Document Results ({documentResults.length})</h3>
              {documentResults.length === 0 ? (
                <div className="empty-results">
                  No documents found matching your criteria.
                </div>
              ) : (
                <div className="results-table-container">
                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Filename</th>
                        <th>Category</th>
                        <th>Student Name</th>
                        <th>Size</th>
                        <th>Upload Date</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {documentResults.map((doc) => (
                        <tr key={doc.id}>
                          <td>{doc.id}</td>
                          <td>{doc.filename}</td>
                          <td>
                            <span className="document-category-badge">
                              {doc.document_category}
                            </span>
                          </td>
                          <td>{doc.student_profile_id ? 'See Profile' : '-'}</td>
                          <td>{formatFileSize(doc.file_size)}</td>
                          <td>{new Date(doc.upload_date).toLocaleDateString()}</td>
                          <td>
                            <div className="action-buttons">
                              <a
                                href={getDocumentUrl(doc.file_path)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn btn-sm btn-secondary"
                              >
                                View
                              </a>
                              <a
                                href={getDocumentUrl(doc.file_path)}
                                download={doc.filename}
                                className="btn btn-sm btn-secondary"
                              >
                                Download
                              </a>
                              {doc.student_profile_id && (
                                <Link
                                  to={`/students/${doc.student_profile_id}`}
                                  className="btn btn-sm btn-primary"
                                >
                                  Profile
                                </Link>
                              )}
                              <button
                                onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                                className="btn btn-sm btn-danger"
                                title="Delete document"
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default SearchInterface;

