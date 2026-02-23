import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './UsersPage.css';

interface UserRow {
  id: number;
  username: string;
  email?: string;
  role: string;
  is_active: boolean;
}

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState<'admin' | 'staff' | 'viewer'>('staff');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const list = await apiService.listUsers(0, 500);
        setUsers(list);
      } catch {
        setError('Failed to load users');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newUsername.trim() || !newPassword) return;
    setSubmitting(true);
    setError('');
    try {
      await apiService.createUser(newUsername.trim(), newPassword, newRole);
      const list = await apiService.listUsers(0, 500);
      setUsers(list);
      setCreateOpen(false);
      setNewUsername('');
      setNewPassword('');
      setNewRole('staff');
    } catch (err: unknown) {
      const res = err && typeof err === 'object' && 'response' in err ? (err as { response?: { data?: { detail?: string } } }).response : undefined;
      setError(res?.data?.detail && typeof res.data.detail === 'string' ? res.data.detail : 'Create failed');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number) {
    if (id === currentUser?.id) {
      setError('You cannot delete yourself');
      return;
    }
    if (!window.confirm('Delete this user?')) return;
    try {
      await apiService.deleteUser(id);
      setUsers((prev) => prev.filter((u) => u.id !== id));
    } catch {
      setError('Delete failed');
    }
  }

  if (loading) {
    return (
      <div className="users-page">
        <div className="users-loading">Loading users…</div>
      </div>
    );
  }

  return (
    <div className="users-page">
      <div className="users-header">
        <h1>Users</h1>
        <button type="button" className="users-btn-primary" onClick={() => setCreateOpen(true)}>
          Add user
        </button>
      </div>
      {error && <div className="users-error">{error}</div>}

      {createOpen && (
        <div className="users-modal">
          <div className="users-modal-inner">
            <h2>Add user</h2>
            <form onSubmit={handleCreate}>
              <label>
                Username
                <input value={newUsername} onChange={(e) => setNewUsername(e.target.value)} required />
              </label>
              <label>
                Password
                <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
              </label>
              <label>
                Role
                <select value={newRole} onChange={(e) => setNewRole(e.target.value as 'admin' | 'staff' | 'viewer')}>
                  <option value="viewer">Viewer</option>
                  <option value="staff">Staff</option>
                  <option value="admin">Admin</option>
                </select>
              </label>
              <div className="users-modal-actions">
                <button type="button" onClick={() => setCreateOpen(false)} disabled={submitting}>
                  Cancel
                </button>
                <button type="submit" disabled={submitting}>
                  {submitting ? 'Creating…' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="users-table-wrap">
        <table className="users-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Active</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{u.email ?? '—'}</td>
                <td>{u.role}</td>
                <td>{u.is_active ? 'Yes' : 'No'}</td>
                <td>
                  {u.id !== currentUser?.id && (
                    <button type="button" className="users-btn-delete" onClick={() => handleDelete(u.id)}>
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
