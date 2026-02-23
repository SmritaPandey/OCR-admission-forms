import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { apiService, StudentProfile } from '../services/api';
import { Table, TableHeader, TableHeaderCell, TableBody, TableRow, TableCell } from './ui/Table';
import Pagination from './Pagination';
import './StudentsPage.css';

const UsersIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
  </svg>
);

const SearchIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

function StudentsPage() {
  const [students, setStudents] = useState<StudentProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50);
  const [totalCount, setTotalCount] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  const loadStudents = useCallback(async () => {
    try {
      setLoading(true);
      const skip = (currentPage - 1) * itemsPerPage;

      // Load only verified students
      const data = await apiService.listStudentProfiles(
        skip,
        itemsPerPage,
        searchQuery.trim() || undefined,
        undefined, // rollNumber
        undefined, // aadharNumber
        { is_verified: true } // filters - only verified students
      );

      setStudents(data);

      // Estimate total: if we got less than requested, that's the total
      // Otherwise, estimate based on current page
      if (data.length < itemsPerPage) {
        setTotalCount(skip + data.length);
      } else {
        // Estimate - in production, API should return actual total
        setTotalCount(skip + data.length + 1); // +1 to show there might be more
      }
    } catch (error: any) {
      console.error('Failed to load students:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Unknown error';
      alert(`Failed to load students: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  }, [currentPage, itemsPerPage, searchQuery]);

  useEffect(() => {
    loadStudents();
    // Auto-refresh every 5 seconds (reduced frequency to avoid timeouts)
    // Use a ref to track if we're currently loading to avoid stale closures
    let isRefreshing = false;
    let timeoutId: NodeJS.Timeout;
    const interval = setInterval(() => {
      if (!isRefreshing) {
        isRefreshing = true;
        timeoutId = setTimeout(async () => {
          try {
            await loadStudents();
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
  }, []); // loadStudents is already memoized with useCallback and its own dependencies

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    loadStudents();
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleItemsPerPageChange = (newItemsPerPage: number) => {
    setItemsPerPage(newItemsPerPage);
    setCurrentPage(1);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const totalPages = Math.ceil(totalCount / itemsPerPage);

  return (
    <div className="students-page">
      <div className="page-header">
        <div className="page-title-section">
          <div className="page-icon">
            <UsersIcon />
          </div>
          <div>
            <h1>Students</h1>
            <p>Verified student records and profiles</p>
          </div>
        </div>
        <div className="page-actions">
          <div className="export-dropdown">
            <button className="btn btn-secondary btn-sm dropdown-trigger">
              Export Students ↓
            </button>
            <div className="dropdown-menu">
              <button onClick={async () => {
                try {
                  const blob = await apiService.exportStudentsCSV({});
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `students_export_${new Date().toISOString().split('T')[0]}.csv`;
                  document.body.appendChild(a);
                  a.click();
                  window.URL.revokeObjectURL(url);
                  document.body.removeChild(a);
                } catch (error: any) {
                  alert(`Export failed: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
                }
              }} className="dropdown-item text-xs">CSV Data</button>
              <button onClick={async () => {
                try {
                  const blob = await apiService.exportStudentsExcel({});
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `students_export_${new Date().toISOString().split('T')[0]}.xlsx`;
                  document.body.appendChild(a);
                  a.click();
                  window.URL.revokeObjectURL(url);
                  document.body.removeChild(a);
                } catch (error: any) {
                  alert(`Export failed: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
                }
              }} className="dropdown-item text-xs">Excel Sheet</button>
              <button onClick={async () => {
                try {
                  const blob = await apiService.exportStudentsPDF({});
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `students_export_${new Date().toISOString().split('T')[0]}.pdf`;
                  document.body.appendChild(a);
                  a.click();
                  window.URL.revokeObjectURL(url);
                  document.body.removeChild(a);
                } catch (error: any) {
                  alert(`Export failed: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
                }
              }} className="dropdown-item text-xs">PDF Report</button>
              <button onClick={async () => {
                try {
                  const blob = await apiService.exportStudentsJSON({});
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `students_export_${new Date().toISOString().split('T')[0]}.json`;
                  document.body.appendChild(a);
                  a.click();
                  window.URL.revokeObjectURL(url);
                  document.body.removeChild(a);
                } catch (error: any) {
                  alert(`Export failed: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
                }
              }} className="dropdown-item text-xs">JSON Raw</button>
            </div>
          </div>
          <span className="total-badge">{totalCount.toLocaleString()} total</span>
        </div>
      </div>

      {/* Search Bar */}
      <div className="search-bar-container">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-wrapper">
            <SearchIcon />
            <input
              type="text"
              placeholder="Search by name, roll number, or Aadhar..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            <button type="submit" className="search-button" disabled={loading}>
              Search
            </button>
          </div>
        </form>
      </div>

      {/* Table */}
      {loading && students.length === 0 ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading students...</p>
        </div>
      ) : students.length === 0 ? (
        <div className="empty-state">
          <UsersIcon />
          <h3>No students found</h3>
          <p>
            {searchQuery
              ? 'No students match your search criteria.'
              : 'Students will appear here once their forms have been verified.'}
          </p>
          {searchQuery && (
            <button
              onClick={() => {
                setSearchQuery('');
                setCurrentPage(1);
              }}
              className="btn btn-secondary"
            >
              Clear Search
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
                  <TableHeaderCell>Student Name</TableHeaderCell>
                  <TableHeaderCell>Roll Number</TableHeaderCell>
                  <TableHeaderCell>Aadhar Number</TableHeaderCell>
                  <TableHeaderCell>Forms</TableHeaderCell>
                  <TableHeaderCell>Documents</TableHeaderCell>
                  <TableHeaderCell>Last Updated</TableHeaderCell>
                  <TableHeaderCell>Actions</TableHeaderCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {students.map((student) => (
                  <TableRow key={student.id}>
                    <TableCell className="font-medium">{student.id}</TableCell>
                    <TableCell className="font-semibold">
                      <Link to={`/students/${student.id}`} className="student-link">
                        {student.student_name}
                      </Link>
                      {student.is_verified && (
                        <span className="verified-badge" title="Verified record">
                          <svg className="w-4 h-4 text-green-500 inline ml-1" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        </span>
                      )}
                    </TableCell>
                    <TableCell>{student.roll_number || '-'}</TableCell>
                    <TableCell>{student.aadhar_number || '-'}</TableCell>
                    <TableCell>
                      <span className="count-badge">{student.forms_count}</span>
                    </TableCell>
                    <TableCell>
                      <span className="count-badge">{student.documents_count}</span>
                    </TableCell>
                    <TableCell>{formatDate(student.updated_date)}</TableCell>
                    <TableCell className="flex gap-2">
                      <Link to={`/students/${student.id}`} className="action-link">
                        View Profile →
                      </Link>
                      <button
                        onClick={async () => {
                          if (window.confirm(`Are you sure you want to delete profile for "${student.student_name}"?`)) {
                            try {
                              await apiService.deleteStudentProfile(student.id);
                              loadStudents();
                            } catch (err) {
                              alert('Failed to delete student profile');
                            }
                          }
                        }}
                        className="action-link danger"
                        style={{ border: 'none', background: 'none', cursor: 'pointer' }}
                      >
                        Delete
                      </button>
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

export default StudentsPage;
