import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="page container">
      <div className="page-header animate-fade-in">
        <h1 className="page-title">Profile</h1>
        <p className="page-subtitle">Your account information</p>
      </div>

      <div className="card animate-fade-in stagger-1" style={{ maxWidth: 500 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', marginBottom: '2rem' }}>
          <div style={{
            width: 80, height: 80, borderRadius: '50%',
            background: 'var(--gradient-primary)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '2rem', fontWeight: 700, color: 'white',
            overflow: 'hidden',
          }}>
            {user?.picture ? (
              <img src={user.picture} alt={user.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              user?.name?.charAt(0) || '?'
            )}
          </div>
          <div>
            <h2 style={{ marginBottom: '0.25rem' }}>{user?.name || 'User'}</h2>
            <p style={{ color: 'var(--text-secondary)' }}>{user?.email || ''}</p>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            padding: '0.75rem 0', borderBottom: '1px solid var(--border-default)',
          }}>
            <span style={{ color: 'var(--text-secondary)' }}>User ID</span>
            <span style={{ fontWeight: 600 }}>{user?.user_id || '—'}</span>
          </div>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            padding: '0.75rem 0', borderBottom: '1px solid var(--border-default)',
          }}>
            <span style={{ color: 'var(--text-secondary)' }}>Email</span>
            <span style={{ fontWeight: 600 }}>{user?.email || '—'}</span>
          </div>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            padding: '0.75rem 0',
          }}>
            <span style={{ color: 'var(--text-secondary)' }}>Auth Method</span>
            <span className="badge badge-primary">{user?.picture ? 'Google' : 'Email & Password'}</span>
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="btn btn-danger"
          style={{ width: '100%', marginTop: '2rem' }}
        >
          🚪 Logout
        </button>
      </div>
    </div>
  );
}
