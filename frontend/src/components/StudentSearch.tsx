import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { apiService, StudentProfile } from '../services/api';
import './StudentSearch.css';

interface SearchParams {
  student_name: string;
  roll_number: string;
  aadhar_number: string;
  // Contact Details
  phone_number: string;
  email: string;
  // Academic Details
  enrollment_number: string;
  application_number: string;
  course_applied: string;
  // Personal Details
  gender: string;
  category: string;
  // Parent Details
  father_name: string;
  mother_name: string;
  // Address Details
  city: string;
  state: string;
  pincode: string;
}

function StudentSearch() {
  const [searchParams, setSearchParams] = useState<SearchParams>({
    student_name: '',
    roll_number: '',
    aadhar_number: '',
    phone_number: '',
    email: '',
    enrollment_number: '',
    application_number: '',
    course_applied: '',
    gender: '',
    category: '',
    father_name: '',
    mother_name: '',
    city: '',
    state: '',
    pincode: '',
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [students, setStudents] = useState<StudentProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);

  // Load all students on mount
  useEffect(() => {
    loadStudents();
  }, []);

  // Debounced search effect
  useEffect(() => {
    if (!initialLoad) {
      const timer = setTimeout(() => {
        loadStudents();
      }, 300); // 300ms debounce

      return () => clearTimeout(timer);
    }
  }, [searchParams, initialLoad]);

  const loadStudents = useCallback(async () => {
    try {
      setLoading(true);
      const basicFilters: {
        student_name?: string;
        roll_number?: string;
        aadhar_number?: string;
      } = {};

      if (searchParams.student_name.trim()) {
        basicFilters.student_name = searchParams.student_name.trim();
      }
      if (searchParams.roll_number.trim()) {
        basicFilters.roll_number = searchParams.roll_number.trim();
      }
      if (searchParams.aadhar_number.trim()) {
        basicFilters.aadhar_number = searchParams.aadhar_number.trim();
      }

      // Build advanced filters object
      const advancedFilters: {
        phone_number?: string;
        email?: string;
        enrollment_number?: string;
        application_number?: string;
        course_applied?: string;
        gender?: string;
        category?: string;
        father_name?: string;
        mother_name?: string;
        city?: string;
        state?: string;
        pincode?: string;
      } = {};

      if (searchParams.phone_number.trim()) {
        advancedFilters.phone_number = searchParams.phone_number.trim();
      }
      if (searchParams.email.trim()) {
        advancedFilters.email = searchParams.email.trim();
      }
      if (searchParams.enrollment_number.trim()) {
        advancedFilters.enrollment_number = searchParams.enrollment_number.trim();
      }
      if (searchParams.application_number.trim()) {
        advancedFilters.application_number = searchParams.application_number.trim();
      }
      if (searchParams.course_applied.trim()) {
        advancedFilters.course_applied = searchParams.course_applied.trim();
      }
      if (searchParams.gender.trim()) {
        advancedFilters.gender = searchParams.gender.trim();
      }
      if (searchParams.category.trim()) {
        advancedFilters.category = searchParams.category.trim();
      }
      if (searchParams.father_name.trim()) {
        advancedFilters.father_name = searchParams.father_name.trim();
      }
      if (searchParams.mother_name.trim()) {
        advancedFilters.mother_name = searchParams.mother_name.trim();
      }
      if (searchParams.city.trim()) {
        advancedFilters.city = searchParams.city.trim();
      }
      if (searchParams.state.trim()) {
        advancedFilters.state = searchParams.state.trim();
      }
      if (searchParams.pincode.trim()) {
        advancedFilters.pincode = searchParams.pincode.trim();
      }

      const data = await apiService.listStudentProfiles(
        0,
        500,
        basicFilters.student_name,
        basicFilters.roll_number,
        basicFilters.aadhar_number,
        Object.keys(advancedFilters).length > 0 ? advancedFilters : undefined
      );
      setStudents(data);
      setInitialLoad(false);
    } catch (error) {
      console.error('Failed to load students:', error);
      alert('Failed to load students. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [searchParams]);

  const handleChange = (field: keyof SearchParams, value: string) => {
    setSearchParams(prev => ({ ...prev, [field]: value }));
  };

  const handleReset = () => {
    setSearchParams({
      student_name: '',
      roll_number: '',
      aadhar_number: '',
      phone_number: '',
      email: '',
      enrollment_number: '',
      application_number: '',
      course_applied: '',
      gender: '',
      category: '',
      father_name: '',
      mother_name: '',
      city: '',
      state: '',
      pincode: '',
    });
    setShowAdvanced(false);
  };

  const hasActiveFilters = Object.values(searchParams).some(value => value.trim() !== '');

  return (
    <div className="student-search">
      <section className="search-hero">
        <div className="hero-body">
          <span className="page-eyebrow">Student Directory</span>
          <h2>Search Students</h2>
          <p>
            Find students by name or roll number. Use advanced search for additional filters.
            All students are displayed by default, sorted by most recently updated.
          </p>
        </div>
        <div className="search-glance">
          <div className="glance-card">
            <span className="glance-label">Total Students</span>
            <span className="glance-value">{students.length}</span>
            <span className="glance-description">
              {hasActiveFilters ? 'Matching your search' : 'In the system'}
            </span>
          </div>
        </div>
      </section>

      <section className="search-card">
        <header className="search-card-header">
          <div>
            <h3>Search Filters</h3>
            <p>
              Enter student name or roll number to filter results. Results update automatically as you type.
            </p>
          </div>
        </header>

        <form 
          className="search-form"
          onSubmit={(e) => {
            e.preventDefault();
            loadStudents();
          }}
        >
          <div className="basic-search-fields">
            <div className="form-group">
              <label htmlFor="student_name">
                Student Name <span className="required">*</span>
              </label>
              <input
                id="student_name"
                type="text"
                value={searchParams.student_name}
                onChange={(e) => handleChange('student_name', e.target.value)}
                placeholder="Enter student name"
                autoComplete="off"
              />
            </div>
            <div className="form-group">
              <label htmlFor="roll_number">Roll Number</label>
              <input
                id="roll_number"
                type="text"
                value={searchParams.roll_number}
                onChange={(e) => handleChange('roll_number', e.target.value)}
                placeholder="Enter roll number"
                autoComplete="off"
              />
            </div>
          </div>

          <div className="advanced-search-toggle">
            <button
              type="button"
              className="toggle-advanced"
              onClick={() => setShowAdvanced(!showAdvanced)}
              aria-expanded={showAdvanced}
            >
              <span>{showAdvanced ? 'Hide' : 'Show'} Advanced Search</span>
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                className={showAdvanced ? 'rotated' : ''}
              >
                <path
                  d="M4 6L8 10L12 6"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>

          {showAdvanced && (
            <div className="advanced-search-fields">
              <div className="advanced-section">
                <h4 className="section-title">Contact Details</h4>
                <div className="fields-grid">
                  <div className="form-group">
                    <label htmlFor="phone_number">Phone Number</label>
                    <input
                      id="phone_number"
                      type="text"
                      value={searchParams.phone_number}
                      onChange={(e) => handleChange('phone_number', e.target.value)}
                      placeholder="Enter phone number"
                      autoComplete="off"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="email">Email</label>
                    <input
                      id="email"
                      type="email"
                      value={searchParams.email}
                      onChange={(e) => handleChange('email', e.target.value)}
                      placeholder="Enter email address"
                      autoComplete="off"
                    />
                  </div>
                </div>
              </div>

              <div className="advanced-section">
                <h4 className="section-title">Academic Details</h4>
                <div className="fields-grid">
                  <div className="form-group">
                    <label htmlFor="enrollment_number">Enrollment Number</label>
                    <input
                      id="enrollment_number"
                      type="text"
                      value={searchParams.enrollment_number}
                      onChange={(e) => handleChange('enrollment_number', e.target.value)}
                      placeholder="Enter enrollment number"
                      autoComplete="off"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="application_number">Application Number</label>
                    <input
                      id="application_number"
                      type="text"
                      value={searchParams.application_number}
                      onChange={(e) => handleChange('application_number', e.target.value)}
                      placeholder="Enter application number"
                      autoComplete="off"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="course_applied">Course Applied</label>
                    <input
                      id="course_applied"
                      type="text"
                      value={searchParams.course_applied}
                      onChange={(e) => handleChange('course_applied', e.target.value)}
                      placeholder="Enter course name"
                      autoComplete="off"
                    />
                  </div>
                </div>
              </div>

              <div className="advanced-section">
                <h4 className="section-title">Personal Details</h4>
                <div className="fields-grid">
                  <div className="form-group">
                    <label htmlFor="gender">Gender</label>
                    <select
                      id="gender"
                      value={searchParams.gender}
                      onChange={(e) => handleChange('gender', e.target.value)}
                    >
                      <option value="">All</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Transgender">Transgender</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label htmlFor="category">Category</label>
                    <select
                      id="category"
                      value={searchParams.category}
                      onChange={(e) => handleChange('category', e.target.value)}
                    >
                      <option value="">All</option>
                      <option value="GEN">General (GEN)</option>
                      <option value="OBC">OBC</option>
                      <option value="SC">SC</option>
                      <option value="ST">ST</option>
                      <option value="EWS">EWS</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label htmlFor="aadhar_number">Aadhar Number</label>
                    <input
                      id="aadhar_number"
                      type="text"
                      value={searchParams.aadhar_number}
                      onChange={(e) => handleChange('aadhar_number', e.target.value)}
                      placeholder="Enter Aadhar number"
                      autoComplete="off"
                    />
                  </div>
                </div>
              </div>

              <div className="advanced-section">
                <h4 className="section-title">Parent/Guardian Details</h4>
                <div className="fields-grid">
                  <div className="form-group">
                    <label htmlFor="father_name">Father's Name</label>
                    <input
                      id="father_name"
                      type="text"
                      value={searchParams.father_name}
                      onChange={(e) => handleChange('father_name', e.target.value)}
                      placeholder="Enter father's name"
                      autoComplete="off"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="mother_name">Mother's Name</label>
                    <input
                      id="mother_name"
                      type="text"
                      value={searchParams.mother_name}
                      onChange={(e) => handleChange('mother_name', e.target.value)}
                      placeholder="Enter mother's name"
                      autoComplete="off"
                    />
                  </div>
                </div>
              </div>

              <div className="advanced-section">
                <h4 className="section-title">Address Details</h4>
                <div className="fields-grid">
                  <div className="form-group">
                    <label htmlFor="city">City</label>
                    <input
                      id="city"
                      type="text"
                      value={searchParams.city}
                      onChange={(e) => handleChange('city', e.target.value)}
                      placeholder="Enter city"
                      autoComplete="off"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="state">State</label>
                    <input
                      id="state"
                      type="text"
                      value={searchParams.state}
                      onChange={(e) => handleChange('state', e.target.value)}
                      placeholder="Enter state"
                      autoComplete="off"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="pincode">PIN Code</label>
                    <input
                      id="pincode"
                      type="text"
                      value={searchParams.pincode}
                      onChange={(e) => handleChange('pincode', e.target.value)}
                      placeholder="Enter PIN code"
                      autoComplete="off"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="form-actions">
            <button
              type="button"
              onClick={handleReset}
              className="btn btn-secondary"
              disabled={loading || !hasActiveFilters}
            >
              Clear Filters
            </button>
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary btn-large"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>
      </section>

      <section className="students-table-section">
        <header className="table-header">
          <div>
            <h3>Students ({students.length})</h3>
            <p>
              {hasActiveFilters
                ? 'Filtered results based on your search criteria'
                : 'All students in the system, sorted by most recently updated'}
            </p>
          </div>
        </header>

        {loading && initialLoad ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading students...</p>
          </div>
        ) : students.length === 0 ? (
          <div className="empty-results">
            <p>No students found.</p>
            {hasActiveFilters && (
              <button onClick={handleReset} className="btn btn-secondary">
                Clear Filters
              </button>
            )}
          </div>
        ) : (
          <div className="table-container">
            <table className="students-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Student Name</th>
                  <th>Roll Number</th>
                  <th>Aadhar Number</th>
                  <th>Forms</th>
                  <th>Documents</th>
                  <th>Last Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {students.map((student) => (
                  <tr key={student.id}>
                    <td>{student.id}</td>
                    <td className="student-name">{student.student_name}</td>
                    <td>{student.roll_number || '-'}</td>
                    <td>{student.aadhar_number || '-'}</td>
                    <td>
                      <span className="count-badge">{student.forms_count}</span>
                    </td>
                    <td>
                      <span className="count-badge">{student.documents_count}</span>
                    </td>
                    <td>{new Date(student.updated_date).toLocaleDateString()}</td>
                    <td>
                      <Link
                        to={`/students/${student.id}`}
                        className="btn btn-sm btn-primary"
                      >
                        View Profile
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default StudentSearch;


