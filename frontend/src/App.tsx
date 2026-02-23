import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import UploadForm from './components/UploadForm';
import BatchUpload from './components/BatchUpload';
import VerificationView from './components/VerificationView';
import SearchInterface from './components/SearchInterface';
import StudentsPage from './components/StudentsPage';
import FormsPage from './components/FormsPage';
import StudentProfile from './components/StudentProfile';
import StudentEditView from './components/StudentEditView';
import TrainingInterface from './components/TrainingInterface';
import UsersPage from './components/UsersPage';
import { BatchUploadProvider } from './contexts/BatchUploadContext';

function LoginOrRedirect() {
  const { authEnabled } = useAuth();
  if (!authEnabled) return <Navigate to="/" replace />;
  return <Login />;
}

function App() {
  return (
    <AuthProvider>
      <BatchUploadProvider>
        <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/login" element={<LoginOrRedirect />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="upload" element={<ProtectedRoute roles={['admin', 'staff']}><UploadForm /></ProtectedRoute>} />
              <Route path="batch-upload" element={<ProtectedRoute roles={['admin', 'staff']}><BatchUpload /></ProtectedRoute>} />
              <Route path="training" element={<ProtectedRoute roles={['admin']}><TrainingInterface /></ProtectedRoute>} />
              <Route path="forms" element={<FormsPage />} />
              <Route path="forms/:id" element={<VerificationView />} />
              <Route path="verify/:id" element={<VerificationView />} />
              <Route path="students" element={<StudentsPage />} />
              <Route path="students/:id" element={<StudentProfile />} />
              <Route path="students/:id/edit" element={<StudentEditView />} />
              <Route path="search" element={<SearchInterface />} />
              <Route path="users" element={<ProtectedRoute roles={['admin']}><UsersPage /></ProtectedRoute>} />
            </Route>
          </Routes>
        </Router>
      </BatchUploadProvider>
    </AuthProvider>
  );
}

export default App;
