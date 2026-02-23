import StudentSearch from './StudentSearch';
import './SearchInterface.css';

function SearchInterface() {
  // Search page now only shows verified students
  // All search functionality is handled by StudentSearch component

  return (
    <div className="search-interface">
      <section className="search-hero">
        <div className="hero-body">
          <span className="page-eyebrow">Admissions Intelligence</span>
          <h2>Search Verified Students</h2>
          <p>
            Search verified student records. Filter by contact details, enrollment information, or course preferences 
            to quickly locate the student records you need.
          </p>
          <div className="hero-actions">
            {/* Only show students tab - verified students only */}
            <div className="tab-group" role="tablist" aria-label="Search filters">
              <button
                role="tab"
                aria-selected={true}
                className="tab active"
              >
                Students (Verified)
              </button>
            </div>
            {/* Export functionality is handled in StudentSearch component */}
          </div>
        </div>
        <div className="search-glance">
          <div className="glance-card">
            <span className="glance-label">Verified Students</span>
            <span className="glance-value">—</span>
            <span className="glance-description">Search verified student records</span>
          </div>
        </div>
      </section>

      {/* Only show students search - verified students only */}
      <StudentSearch />

      {/* Results are shown in StudentSearch component */}
    </div>
  );
}

export default SearchInterface;

