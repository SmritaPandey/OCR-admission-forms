import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import UploadForm from './components/UploadForm';
import BatchUpload from './components/BatchUpload';
import VerificationView from './components/VerificationView';
import SearchInterface from './components/SearchInterface';
import StudentProfile from './components/StudentProfile';
import TrainingInterface from './components/TrainingInterface';
import './App.css';

function NavLinks() {
  const location = useLocation();
  const links = [
    { to: '/', label: 'Dashboard' },
    { to: '/search', label: 'Search' },
  ];

  const allLinks = [
    ...links,
    { to: '/batch-upload', label: 'Batch Upload' },
    { to: '/training', label: 'Training' }
  ];

  return (
    <div className="nav-menu">
      {allLinks.map((link) => (
        <Link
          key={link.to}
          to={link.to}
          className={`nav-link ${location.pathname === link.to ? 'active' : ''}`}
        >
          {link.label}
        </Link>
      ))}
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-container">
            <Link to="/" className="nav-logo">
              <div className="nav-emblem" aria-hidden="true">AP</div>
              <div className="nav-brand">
                <span className="nav-brand-title">Admissions Portal</span>
                <span className="nav-brand-subtitle">College Enrollment Command Center</span>
              </div>
            </Link>
            <div className="nav-actions">
              <NavLinks />
              <Link
                to="/upload"
                className="nav-cta"
              >
                New Submission
              </Link>
            </div>
          </div>
        </nav>

        <main className="main-content">
          <div className="page-container">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/upload" element={<UploadForm />} />
              <Route path="/batch-upload" element={<BatchUpload />} />
              <Route path="/training" element={<TrainingInterface />} />
              <Route path="/forms/:id" element={<VerificationView />} />
              <Route path="/students/:id" element={<StudentProfile />} />
              <Route path="/search" element={<SearchInterface />} />
            </Routes>
          </div>
        </main>

        <footer className="site-footer">
          <p>
            © {new Date().getFullYear()} Admissions Office · Empowering a seamless college onboarding experience.
          </p>
        </footer>
      </div>
    </Router>
  );
}

export default App;

