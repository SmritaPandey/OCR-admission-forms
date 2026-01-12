import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { apiService, FormDetail } from '../services/api';
import { Table, TableHeader, TableHeaderCell, TableBody, TableRow, TableCell } from './ui/Table';
import { Select, SelectItem } from './ui/Select';
import Pagination from './Pagination';
import './FormsPage.css';

const DocumentIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
  </svg>
);

const SearchIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const STATUS_LABELS: Record<string, string> = {
  uploaded: 'Uploaded',
  extracted: 'Pending Verification',
  verified: 'Verified',
};

const getStatusBadgeClass = (status: string) => {
  switch (status) {
    case 'verified':
      return 'status-badge status-verified';
    case 'extracted':
      return 'status-badge status-extracted';
    default:
      return 'status-badge status-uploaded';
  }
};

function FormsPage() {
  const [forms, setForms] = useState<FormDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50);
  const [totalCount, setTotalCount] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>(''); // Empty means all statuses

  const loadForms = useCallback(async () => {
    try {
      setLoading(true);
      
      const skip = (currentPage - 1) * itemsPerPage;
      
      // Use status filter - backend listForms accepts status parameter
      // If statusFilter is empty, pass undefined to get all forms (all statuses)
      const statusParam = statusFilter && statusFilter !== '' ? statusFilter : undefined;
      const allForms = await apiService.listForms(skip, itemsPerPage, statusParam);
      
      // Filter by search query if provided (client-side)
      // Note: For large datasets, search should be server-side
      const searchFilteredForms = searchQuery.trim()
        ? allForms.filter(form => 
            form.filename?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            form.student_name?.toLowerCase().includes(searchQuery.toLowerCase())
          )
        : allForms;
      
      setForms(searchFilteredForms);
      
      // Estimate total - if we got less than requested, that's likely the total for this page
      if (searchFilteredForms.length < itemsPerPage) {
        setTotalCount(skip + searchFilteredForms.length);
      } else {
        // Estimate there are more pages
        setTotalCount(skip + itemsPerPage + 1);
      }
    } catch (error) {
      console.error('Failed to load forms:', error);
      alert('Failed to load forms. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, itemsPerPage, statusFilter, searchQuery]);

  useEffect(() => {
    loadForms();
  }, [loadForms]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    loadForms();
  };

  const handleStatusChange = (status: string) => {
    setStatusFilter(status);
    setCurrentPage(1); // Reset to first page when status changes
  };

  const handleResetFilters = () => {
    setStatusFilter('');
    setSearchQuery('');
    setCurrentPage(1);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleItemsPerPageChange = (newItemsPerPage: number) => {
    setItemsPerPage(newItemsPerPage);
    setCurrentPage(1);
  };

  const handleDelete = async (formId: number, filename: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!window.confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await apiService.deleteForm(formId);
      setForms(forms.filter(f => f.id !== formId));
      // Reload to get updated count
      loadForms();
    } catch (error: any) {
      alert(`Failed to delete form: ${error.response?.data?.detail || error.message}`);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const totalPages = Math.ceil(totalCount / itemsPerPage);

  return (
    <div className="forms-page">
      <div className="page-header">
        <div className="page-title-section">
          <div className="page-icon">
            <DocumentIcon />
          </div>
          <div>
            <h1>Admission Forms</h1>
            <p>View and manage all uploaded admission forms</p>
          </div>
        </div>
        <div className="page-actions">
          <span className="total-badge">{totalCount.toLocaleString()} total</span>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="filters-bar-container">
        <form onSubmit={handleSearch} className="filters-form">
          <div className="filters-row">
            <div className="filter-group">
              <label className="filter-label">Status</label>
              <Select
                selectedKey={statusFilter || undefined}
                onSelectionChange={(key: any) => handleStatusChange(key ? String(key) : '')}
                className="filter-select"
              >
                <SelectItem id="">All Statuses</SelectItem>
                <SelectItem id="uploaded">Uploaded</SelectItem>
                <SelectItem id="extracted">Pending Verification</SelectItem>
                <SelectItem id="verified">Verified</SelectItem>
              </Select>
            </div>
            <div className="search-input-wrapper">
              <SearchIcon />
              <input
                type="text"
                placeholder="Search by filename or student name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
              />
              <button type="submit" className="search-button" disabled={loading}>
                Search
              </button>
            </div>
            {(statusFilter || searchQuery) && (
              <button
                type="button"
                onClick={handleResetFilters}
                className="reset-button"
              >
                Clear Filters
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Table */}
      {loading && forms.length === 0 ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading forms...</p>
        </div>
      ) : forms.length === 0 ? (
        <div className="empty-state">
          <DocumentIcon />
          <h3>No forms found</h3>
          <p>
            {searchQuery || statusFilter
              ? 'No forms match your search criteria. Try adjusting your filters.'
              : 'No forms found. New forms will appear here when uploaded.'}
          </p>
          {(searchQuery || statusFilter) && (
            <button
              onClick={handleResetFilters}
              className="btn btn-secondary"
            >
              Clear Filters
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="table-container">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHeaderCell>ID</TableHeaderCell>
                  <TableHeaderCell>Filename</TableHeaderCell>
                  <TableHeaderCell>Student Name</TableHeaderCell>
                  <TableHeaderCell>Status</TableHeaderCell>
                  <TableHeaderCell>OCR Provider</TableHeaderCell>
                  <TableHeaderCell>Upload Date</TableHeaderCell>
                  <TableHeaderCell>Actions</TableHeaderCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {forms.map((form) => (
                  <TableRow key={form.id}>
                    <TableCell className="font-medium">{form.id}</TableCell>
                    <TableCell className="font-semibold">
                      <Link to={`/forms/${form.id}`} className="form-link">
                        {form.filename}
                      </Link>
                    </TableCell>
                    <TableCell>{form.student_name || '-'}</TableCell>
                    <TableCell>
                      <span className={getStatusBadgeClass(form.status)}>
                        {STATUS_LABELS[form.status] || form.status}
                      </span>
                    </TableCell>
                    <TableCell>{form.ocr_provider || '-'}</TableCell>
                    <TableCell>{formatDate(form.upload_date)}</TableCell>
                    <TableCell>
                      <div className="action-buttons">
                        <Link to={`/forms/${form.id}`} className="action-link">
                          Verify
                        </Link>
                        <button
                          onClick={(e) => handleDelete(form.id, form.filename, e)}
                          className="action-link danger"
                        >
                          Delete
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            totalItems={totalCount}
            itemsPerPage={itemsPerPage}
            onPageChange={handlePageChange}
            onItemsPerPageChange={handleItemsPerPageChange}
          />
        </>
      )}
    </div>
  );
}

export default FormsPage;
