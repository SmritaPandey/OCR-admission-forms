import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import UploadForm from './components/UploadForm';
import VerificationView from './components/VerificationView';
import SearchInterface from './components/SearchInterface';
import StudentProfile from './components/StudentProfile';
import './App.css';

function NavLinks() {
  const location = useLocation();
  
  return (
    <div className="nav-menu">
      <Link 
        to="/" 
        className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
      >
        Dashboard
      </Link>
      <Link 
        to="/upload" 
        className={`nav-link ${location.pathname === '/upload' ? 'active' : ''}`}
      >
        Upload
      </Link>
      <Link 
        to="/search" 
        className={`nav-link ${location.pathname === '/search' ? 'active' : ''}`}
      >
        Search
      </Link>
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
              <h1>Admission Form System</h1>
            </Link>
            <NavLinks />
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<UploadForm />} />
            <Route path="/forms/:id" element={<VerificationView />} />
            <Route path="/students/:id" element={<StudentProfile />} />
            <Route path="/search" element={<SearchInterface />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;

