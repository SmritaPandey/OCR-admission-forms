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
  const [selectingAll, setSelectingAll] = useState(false);

  const loadForms = useCallback(async (overrideSortConfig?: { key: string, direction: 'asc' | 'desc' }) => {
    // Skip if already loading to prevent overlapping requests
    // But allow initial load even if loading is true
    if (loading && forms.length > 0 && !overrideSortConfig) {
      return;
    }

    try {
      setLoading(true);
      const skip = (currentPage - 1) * itemsPerPage;
      const statusParam = statusFilter && statusFilter !== '' ? statusFilter : undefined;
      const currentSort = overrideSortConfig || sortConfig;

      let allForms: FormDetail[];

      if (searchQuery.trim()) {
        // Use server-side search
        allForms = await apiService.searchForms({
          skip,
          limit: itemsPerPage,
          status: statusParam,
          student_name: searchQuery.trim(),
          filename: searchQuery.trim(),
          sort_by: currentSort.key,
          sort_order: currentSort.direction
        } as any);
      } else {
        // Use regular list
        allForms = await apiService.listForms(
          skip,
          itemsPerPage,
          statusParam,
          currentSort.key,
          currentSort.direction
        );
      }

      setForms(allForms);

      // Update total count for pagination purposes
      // If we got fewer items than requested, we're on the last page
      if (allForms.length < itemsPerPage) {
        setTotalCount(skip + allForms.length);
      } else {
        // Otherwise, assume there are more pages (until we have a real count from API)
        setTotalCount(skip + itemsPerPage + 1);
      }
    } catch (error: any) {
      // Don't show error for timeout if it's during batch processing
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        console.warn('Forms request timed out - this may happen during heavy batch processing');
        return;
      }
      console.error('Failed to load forms:', error);
    } finally {
      setLoading(false);
    }
  }, [currentPage, itemsPerPage, statusFilter, searchQuery, sortConfig]);

  useEffect(() => {
    loadForms();
    // Auto-refresh every 5 seconds (reduced frequency to avoid timeouts)
    // Use a ref to track if we're currently loading to avoid stale closures
    let isRefreshing = false;
    let timeoutId: NodeJS.Timeout;
    const interval = setInterval(() => {
      // Skip refresh if already loading
      if (!isRefreshing) {
        isRefreshing = true;
        timeoutId = setTimeout(async () => {
          try {
            await loadForms();
          } finally {
            isRefreshing = false;
          }
        }, 100); // Small delay to debounce
      }
    }, 5000);
    return () => {
      clearInterval(interval);
      if (timeoutId) clearTimeout(timeoutId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, itemsPerPage, statusFilter, searchQuery, sortConfig]); // Include sortConfig to reload when sorting changes

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
    const newDirection = sortConfig.key === key && sortConfig.direction === 'desc' ? 'asc' : 'desc';
    const newSortConfig: { key: string, direction: 'asc' | 'desc' } = {
      key,
      direction: newDirection
    };
    setSortConfig(newSortConfig);
    setCurrentPage(1);
    // Immediately reload with new sort config
    loadForms(newSortConfig);
  };

  const handleExport = async (format: string) => {
    try {
      // If forms are selected, export only those forms
      // Otherwise, export all forms matching the current filters
      let exportFilters: any = {
        status: statusFilter || undefined,
      };

      // If specific forms are selected, include their IDs in the export
      if (selectedForms.length > 0) {
        exportFilters.form_ids = selectedForms.join(',');
      }

      const blob = await apiService.exportForms(format as 'csv' | 'json' | 'excel' | 'pdf', exportFilters);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const filename = selectedForms.length > 0
        ? `admission_forms_selected_${selectedForms.length}_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : format}`
        : `admission_forms_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : format}`;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: any) {
      console.error('Export failed:', error);
      alert(`Export failed: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
    }
  };

  const toggleSelectAll = () => {
    // Toggle selection for current page only
    if (selectedForms.length === forms.length && forms.length > 0) {
      // Deselect all items from current page
      const currentPageIds = forms.map(f => f.id);
      setSelectedForms(prev => prev.filter(id => !currentPageIds.includes(id)));
    } else {
      // Select all items from current page (add to existing selection)
      const currentPageIds = forms.map(f => f.id);
      setSelectedForms(prev => {
        const newSelection = [...prev];
        currentPageIds.forEach(id => {
          if (!newSelection.includes(id)) {
            newSelection.push(id);
          }
        });
        return newSelection;
      });
    }
  };

  const handleSelectAllInDatabase = async () => {
    try {
      setSelectingAll(true);

      // Use lightweight endpoint to get all form IDs matching current filters
      const statusParam = statusFilter && statusFilter !== '' ? statusFilter : undefined;
      let allIds = await apiService.listFormIds(
        statusParam,
        sortConfig.key,
        sortConfig.direction
      );

      // Apply client-side search filter if needed
      // Note: For search, we need to fetch full forms to filter by filename/student_name
      if (searchQuery.trim()) {
        // Fetch forms with a reasonable limit to apply search filter
        const allForms = await apiService.listForms(
          0,
          50000, // Large but within backend limit
          statusParam,
          sortConfig.key,
          sortConfig.direction
        );

        const filteredForms = allForms.filter(form =>
          form.filename?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          form.student_name?.toLowerCase().includes(searchQuery.toLowerCase())
        );

        allIds = filteredForms.map(f => f.id);
      }

      if (selectedForms.length === allIds.length && allIds.length > 0) {
        // If all are selected, deselect all
        setSelectedForms([]);
      } else {
        // Select all
        setSelectedForms(allIds);
      }
    } catch (error: any) {
      console.error('Failed to select all forms:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Unknown error';
      alert(`Failed to select all forms: ${errorMessage}`);
    } finally {
      setSelectingAll(false);
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
            <>
              <button onClick={handleBulkDelete} className="btn btn-destructive btn-sm mr-2">
                Delete Selected ({selectedForms.length})
              </button>
              <span className="total-badge mr-2" style={{ marginRight: '8px' }}>
                {selectedForms.length} selected
              </span>
            </>
          )}
          <div className="export-dropdown-wrapper">
            <button className="btn btn-outline btn-sm dropdown-trigger">
              <span>⬇ Export Data</span>
            </button>
            <div className="dropdown-menu">
              <div className="dropdown-header">Choose Format</div>
              <button onClick={() => handleExport('csv')} className="dropdown-item">
                <span className="icon">📄</span> CSV File
              </button>
              <button onClick={() => handleExport('excel')} className="dropdown-item">
                <span className="icon">📊</span> Excel Spreadsheet
              </button>
              <button onClick={() => handleExport('pdf')} className="dropdown-item">
                <span className="icon">📑</span> PDF Document
              </button>
              <button onClick={() => handleExport('json')} className="dropdown-item">
                <span className="icon">⚙️</span> JSON Raw Data
              </button>
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
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-start' }}>
                      <input
                        type="checkbox"
                        checked={forms.length > 0 && forms.every(f => selectedForms.includes(f.id))}
                        onChange={toggleSelectAll}
                        title="Select all on current page"
                      />
                      <button
                        onClick={handleSelectAllInDatabase}
                        disabled={selectingAll}
                        className="btn btn-link btn-xs"
                        style={{
                          padding: '2px 4px',
                          fontSize: '10px',
                          textDecoration: 'none',
                          cursor: selectingAll ? 'wait' : 'pointer'
                        }}
                        title="Select all forms in database matching current filters"
                      >
                        {selectingAll ? 'Loading...' : selectedForms.length > 0 ? `Clear All (${selectedForms.length})` : 'Select All'}
                      </button>
                    </div>
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
