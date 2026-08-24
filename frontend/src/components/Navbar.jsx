import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { remindersAPI } from '../api/api';
import GlobalSearchBar from './GlobalSearchBar';
import './Navbar.css';

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [dueCount, setDueCount] = useState(0);

  useEffect(() => {
    if (user) {
      remindersAPI.getAll()
        .then((res) => {
          setDueCount(res.data.due_count || 0);
        })
        .catch(() => { });
    }
  }, [user, location.pathname]);

  const baseLinks = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/analyze', label: 'Analyze', icon: '🔬' },
    { path: '/dataset', label: 'Dataset', icon: '🗂️' },
    { path: '/history', label: 'History', icon: '📋' },
  ];

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';
  const adminLinks = isAdmin
    ? [{ path: '/admin', label: 'Admin Console', icon: '🛡️' }]
    : [];

  const navLinks = [...baseLinks, ...adminLinks];

  const isLinkActive = (path) => {
    if (path === '/admin') {
      return location.pathname === '/admin' || location.pathname.startsWith('/admin/');
    }
    return location.pathname === path;
  };

  return (
    <nav className="navbar">
      <div className="navbar-inner container">
        {/* Left: Brand Logo */}
        <Link to="/dashboard" className="navbar-brand">
          <span className="brand-icon">🩺</span>
          <span className="brand-text">Derma<span className="brand-accent">Assist</span></span>
        </Link>

        {/* Center: Main Navigation Links */}
        <div className="navbar-links">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className={`nav-link ${isLinkActive(link.path) ? 'active' : ''}`}
            >
              <span className="nav-icon">{link.icon}</span>
              <span>{link.label}</span>
            </Link>
          ))}
        </div>

        {/* Right: Search, Due Reminders Bell, Profile & Logout */}
        <div className="navbar-user">
          {/* Global Spotlight Search Trigger */}
          <GlobalSearchBar />

          {/* Notification Bell for Due Reminders */}
          <Link to="/dashboard" className="nav-notification-bell" title={`${dueCount} Due Follow-Up Reminders`}>
            <span>🔔</span>
            {dueCount > 0 && (
              <span className="bell-badge-count">{dueCount}</span>
            )}
          </Link>

          {user && (
            <>
              <Link to="/profile" className="user-info">
                <div className="user-avatar">
                  {user.picture ? (
                    <img src={user.picture} alt={user.name} />
                  ) : (
                    <span>{user.name?.charAt(0) || '?'}</span>
                  )}
                </div>
                <span className="user-name">{user.name}</span>
              </Link>
              <button onClick={logout} className="btn btn-sm btn-secondary logout-btn">
                Logout
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
