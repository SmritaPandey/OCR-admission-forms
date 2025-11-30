import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiService, FormDetail, Document, DocumentCategory, FormSearchQuery } from '../services/api';
import './SearchInterface.css';

const FILTER_LABELS: Record<string, string> = {
  student_name: 'Name',
  phone_number: 'Phone',
  email: 'Email',
  enrollment_number: 'Enrollment #',
  application_number: 'Application #',
  course_applied: 'Course',
  status: 'Status',
  date_from: 'Uploaded From',
  date_to: 'Uploaded To',
};

const STATUS_LABELS: Record<string, string> = {
  uploaded: 'Uploaded',
  extracted: 'Pending Verification',
  verified: 'Verified',
};
function SearchInterface() {
  const [activeTab, setActiveTab] = useState<'forms' | 'documents'>('forms');
  const INITIAL_FORM_PARAMS: FormSearchQuery = {
    student_name: '',
    phone_number: '',
    email: '',
    enrollment_number: '',
    application_number: '',
    course_applied: '',
    status: '',
    date_from: '',
    date_to: '',
  };

  const [searchParams, setSearchParams] = useState<FormSearchQuery>(INITIAL_FORM_PARAMS);
  const [documentSearchParams, setDocumentSearchParams] = useState({
    document_category: '',
    student_name: '',
  });
  const [results, setResults] = useState<FormDetail[]>([]);
  const [documentResults, setDocumentResults] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [searched, setSearched] = useState(false);
  const [categories, setCategories] = useState<{ value: string; name: string }[]>([]);
  const [lastUsedFilters, setLastUsedFilters] = useState<FormSearchQuery>({});

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

  const buildFormFilters = (): FormSearchQuery => {
    const filters: FormSearchQuery = {};
    Object.entries(searchParams).forEach(([key, value]) => {
      if (value) {
        filters[key as keyof FormSearchQuery] = value;
      }
    });
    return filters;
  };

  const handleResetFilters = () => {
    setSearchParams({ ...INITIAL_FORM_PARAMS });
    setLastUsedFilters({});
    setResults([]);
    setSearched(false);
  };

  const formatDate = (value?: string): string => {
    if (!value) return '-';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    return parsed.toLocaleDateString();
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setSearched(true);
      const filters = buildFormFilters();
      const data = await apiService.searchForms({
        ...filters,
        page: 1,
        limit: 50,
      });
      setResults(data);
      setLastUsedFilters(filters);
    } catch (error) {
      console.error('Search failed:', error);
      alert('Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      setExporting(true);
      const filters = Object.keys(lastUsedFilters).length > 0 ? lastUsedFilters : buildFormFilters();
      const exportFilters: FormSearchQuery = { ...filters };
      delete exportFilters.page;
      delete exportFilters.limit;
      const blob = await apiService.exportForms(format, exportFilters);
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
    } finally {
      setExporting(false);
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

  const formResultCount = results.length;
  const documentResultCount = documentResults.length;
  const activeFilters = Object.entries(lastUsedFilters).filter(
    ([, value]) => value !== undefined && value !== ''
  );

  return (
    <div className="search-interface">
      <section className="search-hero">
        <div className="hero-body">
          <span className="page-eyebrow">Admissions Intelligence</span>
          <h2>Search Applications &amp; Documents</h2>
          <p>
            Run precise queries across verified applicants, pending forms, and supporting documentation.
            Filter by contact details, enrollment information, or course preferences to quickly locate
            the records you need.
          </p>
          <div className="hero-actions">
            <div className="tab-group" role="tablist" aria-label="Search filters">
              <button
                role="tab"
                aria-selected={activeTab === 'forms'}
                className={`tab ${activeTab === 'forms' ? 'active' : ''}`}
                onClick={() => setActiveTab('forms')}
              >
                Admission Forms
              </button>
              <button
                role="tab"
                aria-selected={activeTab === 'documents'}
                className={`tab ${activeTab === 'documents' ? 'active' : ''}`}
                onClick={() => setActiveTab('documents')}
              >
                Supporting Documents
              </button>
            </div>
            <div className="export-buttons">
              <button
                onClick={() => handleExport('csv')}
                className="btn btn-secondary"
                disabled={exporting || loading}
              >
                {exporting ? 'Exporting…' : 'Export CSV'}
              </button>
              <button
                onClick={() => handleExport('json')}
                className="btn btn-secondary"
                disabled={exporting || loading}
              >
                {exporting ? 'Exporting…' : 'Export JSON'}
              </button>
            </div>
          </div>
        </div>
        <div className="search-glance">
          <div className="glance-card">
            <span className="glance-label">Form Matches</span>
            <span className="glance-value">{searched ? formResultCount : '—'}</span>
            <span className="glance-description">Results from the last query</span>
          </div>
          <div className="glance-card">
            <span className="glance-label">Document Matches</span>
            <span className="glance-value">{searched ? documentResultCount : '—'}</span>
            <span className="glance-description">Filtered by category &amp; student</span>
          </div>
        </div>
      </section>

      <section className="search-card">
        <header className="search-card-header">
          <div>
            <h3>{activeTab === 'forms' ? 'Filter Admission Forms' : 'Filter Supporting Documents'}</h3>
            <p>
              {activeTab === 'forms'
                ? 'Combine student details, enrollment IDs, or application numbers to narrow down submissions.'
                : 'Locate documentation tied to specific students or categories for rapid follow-up.'}
            </p>
          </div>
        </header>

        {activeTab === 'forms' ? (
          <form onSubmit={handleSearch} className="search-form">
            <div className="search-grid">
              <div className="form-group">
                <label htmlFor="student_name">Student Name</label>
                <input
                  id="student_name"
                  type="text"
                  value={searchParams.student_name}
                  onChange={(e) => handleChange('student_name', e.target.value)}
                  placeholder="Search by name"
                />
              </div>
              <div className="form-group">
                <label htmlFor="phone_number">Phone Number</label>
                <input
                  id="phone_number"
                  type="text"
                  value={searchParams.phone_number}
                  onChange={(e) => handleChange('phone_number', e.target.value)}
                  placeholder="Search by phone"
                />
              </div>
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  value={searchParams.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                  placeholder="Search by email"
                />
              </div>
              <div className="form-group">
                <label htmlFor="enrollment_number">Enrollment Number</label>
                <input
                  id="enrollment_number"
                  type="text"
                  value={searchParams.enrollment_number}
                  onChange={(e) => handleChange('enrollment_number', e.target.value)}
                  placeholder="Search by enrollment"
                />
              </div>
              <div className="form-group">
                <label htmlFor="application_number">Application Number</label>
                <input
                  id="application_number"
                  type="text"
                  value={searchParams.application_number}
                  onChange={(e) => handleChange('application_number', e.target.value)}
                  placeholder="Search by application"
                />
              </div>
              <div className="form-group">
                <label htmlFor="course_applied">Course Applied</label>
                <input
                  id="course_applied"
                  type="text"
                  value={searchParams.course_applied}
                  onChange={(e) => handleChange('course_applied', e.target.value)}
                  placeholder="Search by course"
                />
              </div>
              <div className="form-group">
                <label htmlFor="status">Status</label>
                <select
                  id="status"
                  value={searchParams.status}
                  onChange={(e) => handleChange('status', e.target.value)}
                >
                  <option value="">All statuses</option>
                  <option value="uploaded">Uploaded</option>
                  <option value="extracted">Pending Verification</option>
                  <option value="verified">Verified</option>
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="date_from">Upload Date From</label>
                <input
                  id="date_from"
                  type="date"
                  value={searchParams.date_from || ''}
                  onChange={(e) => handleChange('date_from', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label htmlFor="date_to">Upload Date To</label>
                <input
                  id="date_to"
                  type="date"
                  value={searchParams.date_to || ''}
                  onChange={(e) => handleChange('date_to', e.target.value)}
                />
              </div>
            </div>
            <div className="form-actions">
              <button
                type="button"
                onClick={handleResetFilters}
                className="btn btn-secondary"
                disabled={loading}
              >
                Clear Filters
              </button>
              <button type="submit" disabled={loading} className="btn btn-primary btn-large">
                {loading ? 'Searching...' : 'Run Form Search'}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleDocumentSearch} className="search-form">
            <div className="search-grid">
              <div className="form-group">
                <label htmlFor="document_category">Document Category</label>
                <select
                  id="document_category"
                  value={documentSearchParams.document_category}
                  onChange={(e) =>
                    setDocumentSearchParams(prev => ({ ...prev, document_category: e.target.value }))
                  }
                >
                  <option value="">All categories</option>
                  {categories.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="document_student_name">Student Name</label>
                <input
                  id="document_student_name"
                  type="text"
                  value={documentSearchParams.student_name}
                  onChange={(e) =>
                    setDocumentSearchParams(prev => ({ ...prev, student_name: e.target.value }))
                  }
                  placeholder="Search by student name"
                />
              </div>
            </div>
            <div className="form-actions">
              <button type="submit" disabled={loading} className="btn btn-primary btn-large">
                {loading ? 'Searching...' : 'Run Document Search'}
              </button>
            </div>
          </form>
        )}
      </section>

      {searched && (
        <section className="search-results">
          <header className="search-results-header">
            <div>
              <h3>
                {activeTab === 'forms'
                  ? `Form Results (${formResultCount})`
                  : `Document Results (${documentResultCount})`}
              </h3>
              <p>
                {activeTab === 'forms'
                  ? 'Review applicant submissions and navigate directly to verification.'
                  : 'View, download, or navigate to the student profile for each document.'}
              </p>
            </div>
          </header>
          {activeTab === 'forms' && activeFilters.length > 0 && (
            <div className="active-filters" aria-label="Active form filters">
              {activeFilters.map(([key, value]) => {
                const label = FILTER_LABELS[key] || key;
                const rawValue = String(value);
                let displayValue = rawValue;
                if (key === 'status') {
                  displayValue = STATUS_LABELS[rawValue.toLowerCase()] || rawValue;
                } else if (key === 'date_from' || key === 'date_to') {
                  displayValue = formatDate(rawValue);
                }
                return (
                  <span key={key} className="filter-chip">
                    {label}: {displayValue}
                  </span>
                );
              })}
            </div>
          )}

          {activeTab === 'forms' ? (
            formResultCount === 0 ? (
              <div className="empty-results">No forms found matching your criteria.</div>
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
                      <th>Application #</th>
                      <th>Enrollment #</th>
                      <th>Uploaded</th>
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
                        <td>{form.application_number || '-'}</td>
                        <td>{form.enrollment_number || '-'}</td>
                        <td>{formatDate(form.upload_date)}</td>
                        <td>
                          <span className={`status-badge status-${form.status}`}>
                            {STATUS_LABELS[form.status] || form.status}
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
            )
          ) : documentResultCount === 0 ? (
            <div className="empty-results">No documents found matching your criteria.</div>
          ) : (
            <div className="results-table-container">
              <table className="results-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Filename</th>
                    <th>Category</th>
                    <th>Student</th>
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
        </section>
      )}
    </div>
  );
}

export default SearchInterface;

