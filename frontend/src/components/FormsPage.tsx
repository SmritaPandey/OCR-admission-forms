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
  const [statusFilter, setStatusFilter] = useState<string>('');

  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' }>({
    key: 'upload_date',
    direction: 'desc'
  });
  const [selectedForms, setSelectedForms] = useState<number[]>([]);

  const loadForms = useCallback(async () => {
    try {
      setLoading(true);
      const skip = (currentPage - 1) * itemsPerPage;
      const statusParam = statusFilter && statusFilter !== '' ? statusFilter : undefined;
      const allForms = await apiService.listForms(
        skip,
        itemsPerPage,
        statusParam,
        sortConfig.key,
        sortConfig.direction
      );

      const searchFilteredForms = searchQuery.trim()
        ? allForms.filter(form =>
          form.filename?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          form.student_name?.toLowerCase().includes(searchQuery.toLowerCase())
        )
        : allForms;

      setForms(searchFilteredForms);

      if (searchFilteredForms.length < itemsPerPage) {
        setTotalCount(skip + searchFilteredForms.length);
      } else {
        setTotalCount(skip + itemsPerPage + 1);
      }
    } catch (error) {
      console.error('Failed to load forms:', error);
    } finally {
      setLoading(false);
    }
  }, [currentPage, itemsPerPage, statusFilter, searchQuery, sortConfig]);

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
    setCurrentPage(1);
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

  const handleSort = (key: string) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
    }));
    setCurrentPage(1);
  };

  const handleExport = async (format: string) => {
    window.location.href = `${apiService.getBaseUrl()}/api/forms/export?format=${format}${statusFilter ? `&status=${statusFilter}` : ''}`;
  };

  const toggleSelectAll = () => {
    if (selectedForms.length === forms.length && forms.length > 0) {
      setSelectedForms([]);
    } else {
      setSelectedForms(forms.map(f => f.id));
    }
  };

  const toggleSelect = (id: number) => {
    setSelectedForms(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const handleBulkDelete = async () => {
    if (selectedForms.length === 0) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedForms.length} selected forms?`)) return;

    try {
      await apiService.bulkDeleteForms(selectedForms);
      setSelectedForms([]);
      loadForms();
    } catch (error: any) {
      alert('Failed to delete forms');
    }
  };

  const handleDelete = async (formId: number, filename: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    try {
      await apiService.deleteForm(formId);
      loadForms();
    } catch (error: any) {
      alert('Failed to delete form');
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
          {selectedForms.length > 0 && (
            <button onClick={handleBulkDelete} className="btn btn-destructive btn-sm mr-2">
              Delete Selected ({selectedForms.length})
            </button>
          )}
          <div className="export-dropdown">
            <button className="btn btn-secondary btn-sm dropdown-trigger">
              Export Data ↓
            </button>
            <div className="dropdown-menu">
              <button onClick={() => handleExport('csv')} className="dropdown-item text-xs">CSV Format</button>
              <button onClick={() => handleExport('excel')} className="dropdown-item text-xs">Excel Spreadsheet</button>
              <button onClick={() => handleExport('pdf')} className="dropdown-item text-xs">PDF Document</button>
              <button onClick={() => handleExport('json')} className="dropdown-item text-xs">JSON Raw</button>
            </div>
          </div>
          <span className="total-badge">{totalCount.toLocaleString()} total</span>
        </div>
      </div>

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
                  <TableHeaderCell>
                    <input type="checkbox" checked={selectedForms.length === forms.length && forms.length > 0} onChange={toggleSelectAll} />
                  </TableHeaderCell>
                  <TableHeaderCell onClick={() => handleSort('id')} className="cursor-pointer">
                    ID {sortConfig.key === 'id' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
                  </TableHeaderCell>
                  <TableHeaderCell onClick={() => handleSort('filename')} className="cursor-pointer">
                    Filename {sortConfig.key === 'filename' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
                  </TableHeaderCell>
                  <TableHeaderCell onClick={() => handleSort('student_name')} className="cursor-pointer">
                    Student Name {sortConfig.key === 'student_name' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
                  </TableHeaderCell>
                  <TableHeaderCell onClick={() => handleSort('status')} className="cursor-pointer">
                    Status {sortConfig.key === 'status' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
                  </TableHeaderCell>
                  <TableHeaderCell>OCR Provider</TableHeaderCell>
                  <TableHeaderCell onClick={() => handleSort('upload_date')} className="cursor-pointer">
                    Upload Date {sortConfig.key === 'upload_date' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
                  </TableHeaderCell>
                  <TableHeaderCell>Actions</TableHeaderCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {forms.map((form) => (
                  <TableRow key={form.id}>
                    <TableCell>
                      <input type="checkbox" checked={selectedForms.includes(form.id)} onChange={() => toggleSelect(form.id)} />
                    </TableCell>
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
