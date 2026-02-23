import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';
import api from '../services/api';

export type Role = 'admin' | 'staff' | 'viewer';

export interface User {
  id: number;
  username: string;
  role: Role;
}

interface AuthConfig {
  auth_enabled: boolean;
}

interface AuthContextValue {
  authEnabled: boolean;
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (...roles: Role[]) => boolean;
  setToken: (t: string | null) => void;
  setUser: (u: User | null) => void;
  fetchMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY = 'ocr_admission_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authEnabled, setAuthEnabled] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY)
  );
  const [loading, setLoading] = useState(true);

  const setToken = useCallback((t: string | null) => {
    setTokenState(t);
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  }, []);

  const fetchConfig = useCallback(async () => {
    try {
      const { data } = await api.get<AuthConfig>('/api/auth/config');
      setAuthEnabled(!!data.auth_enabled);
      return !!data.auth_enabled;
    } catch {
      setAuthEnabled(false);
      return false;
    }
  }, []);

  const fetchMe = useCallback(async () => {
    if (!token) return;
    try {
      const { data } = await api.get<{ id: number; username: string; role: string }>('/api/auth/me');
      setUser({
        id: data.id,
        username: data.username,
        role: data.role as Role,
      });
    } catch {
      setToken(null);
      setUser(null);
    }
  }, [token, setToken]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const enabled = await fetchConfig();
      if (cancelled) return;
      if (!enabled) {
        setUser({ id: 0, username: 'default', role: 'admin' });
        setLoading(false);
        return;
      }
      if (token) {
        await fetchMe();
      }
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [fetchConfig, token, fetchMe]);

  useEffect(() => {
    const onLogout = () => logout();
    window.addEventListener('auth-logout', onLogout);
    return () => window.removeEventListener('auth-logout', onLogout);
  }, [logout]);

  const login = useCallback(
    async (username: string, password: string) => {
      const body = new URLSearchParams({ username, password }).toString();
      const { data } = await api.post<{
        access_token: string;
        user_id: number;
        username: string;
        role: string;
      }>('/api/auth/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      setToken(data.access_token);
      setUser({
        id: data.user_id,
        username: data.username,
        role: data.role as Role,
      });
    },
    [setToken]
  );

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, [setToken]);

  const hasRole = useCallback(
    (...roles: Role[]) => {
      if (!user) return false;
      return roles.includes(user.role);
    },
    [user]
  );

  const value: AuthContextValue = {
    authEnabled,
    user,
    token,
    loading,
    login,
    logout,
    hasRole,
    setToken,
    setUser,
    fetchMe,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
