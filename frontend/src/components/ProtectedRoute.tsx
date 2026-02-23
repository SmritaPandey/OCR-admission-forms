import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: ReactNode;
  roles?: Array<'admin' | 'staff' | 'viewer'>;
}

export default function ProtectedRoute({ children, roles }: ProtectedRouteProps) {
  const { authEnabled, user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="text-gray-500">Loading…</div>
      </div>
    );
  }

  if (authEnabled && !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (roles && user && !roles.includes(user.role)) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-2 p-4">
        <p className="text-gray-600">You don’t have permission to view this page.</p>
        <a href="/" className="text-blue-600 hover:underline">Go to Dashboard</a>
      </div>
    );
  }

  return <>{children}</>;
}
