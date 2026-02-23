import { Link, useLocation, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import GlobalProgressIndicator from './GlobalProgressIndicator';

const IconHome = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
  </svg>
);
const IconUpload = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
  </svg>
);
const IconUsers = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
  </svg>
);
const IconDocument = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
  </svg>
);
const IconSearch = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
  </svg>
);
const IconCog = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);
const IconStack = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M6.429 9.75L2.25 12l4.179 2.25m0-4.5l5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L21.75 12l-4.179 2.25m0 0l4.179 2.25L12 21.75 2.25 16.5l4.179-2.25m11.142 0l-5.571 3-5.571-3" />
  </svg>
);
const IconUserCircle = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975m11.963 0a9 9 0 10-11.963 0m11.963 0A8.966 8.966 0 0112 21a8.966 8.966 0 01-5.982-2.275M15 9.75a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

export default function Layout() {
  const location = useLocation();
  const { user, authEnabled, logout, hasRole } = useAuth();
  const navigate = useNavigate();

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const navItems = [
    { to: '/', label: 'Dashboard', icon: IconHome },
    { to: '/students', label: 'Students', icon: IconUsers },
    { to: '/forms', label: 'Forms', icon: IconDocument },
    { to: '/search', label: 'Search', icon: IconSearch },
  ];

  const canUpload = hasRole('admin', 'staff');
  const actionItems = canUpload
    ? [
        { to: '/upload', label: 'Upload Form', icon: IconUpload },
        { to: '/batch-upload', label: 'Batch Upload', icon: IconStack },
      ]
    : [];

  const canTrain = hasRole('admin');
  const canUsers = hasRole('admin');
  const settingsItems = [
    ...(canTrain ? [{ to: '/training', label: 'Model Training', icon: IconCog }] : []),
    ...(canUsers ? [{ to: '/users', label: 'Users', icon: IconUserCircle }] : []),
  ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="sidebar">
        <div className="sidebar-header" style={{ borderBottom: '1px solid #e5e7eb', padding: '1rem' }}>
          <Link to="/" style={{ display: 'block', textDecoration: 'none' }}>
            <img
              src="srcc-logo.png"
              alt="SRCC - Shri Ram College of Commerce"
              style={{ width: '100%', height: 'auto', objectFit: 'contain', maxHeight: '80px' }}
              onError={(e) => {
                const t = e.target as HTMLImageElement;
                t.style.display = 'none';
                const fb = t.parentElement?.querySelector('.logo-fallback') as HTMLElement;
                if (fb) fb.style.display = 'flex';
              }}
            />
            <div className="logo-fallback" style={{ display: 'none', backgroundColor: '#1a3a6e', width: '100%', height: '60px', borderRadius: '8px', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold', fontSize: '18px', textAlign: 'center' }}>
              SRCC - Admissions Portal
            </div>
          </Link>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-section">
            <div className="sidebar-section-title">Main</div>
            {navItems.map((item) => (
              <Link key={item.to} to={item.to} className={`nav-item ${isActive(item.to) ? 'active' : ''}`}>
                <item.icon />
                {item.label}
              </Link>
            ))}
          </div>
          {actionItems.length > 0 && (
            <div className="sidebar-section">
              <div className="sidebar-section-title">Actions</div>
              {actionItems.map((item) => (
                <Link key={item.to} to={item.to} className={`nav-item ${isActive(item.to) ? 'active' : ''}`}>
                  <item.icon />
                  {item.label}
                </Link>
              ))}
            </div>
          )}
          {settingsItems.length > 0 && (
            <div className="sidebar-section">
              <div className="sidebar-section-title">Settings</div>
              {settingsItems.map((item) => (
                <Link key={item.to} to={item.to} className={`nav-item ${isActive(item.to) ? 'active' : ''}`}>
                  <item.icon />
                  {item.label}
                </Link>
              ))}
            </div>
          )}
        </nav>

        <div className="sidebar-footer">
          {authEnabled && user && (
            <div className="flex flex-col gap-1 px-2 py-2 border-t border-gray-200">
              <div className="text-xs text-gray-500 truncate" title={user.username}>
                {user.username} · {user.role}
              </div>
              <button type="button" onClick={handleLogout} className="text-left text-xs text-red-600 hover:underline">
                Sign out
              </button>
            </div>
          )}
          <div className="text-xs text-gray-500 text-center">
            © {new Date().getFullYear()} SRCC Admissions
          </div>
        </div>
      </aside>

      <main className="main-content flex-1">
        <Outlet />
      </main>
      <GlobalProgressIndicator />
    </div>
  );
}
