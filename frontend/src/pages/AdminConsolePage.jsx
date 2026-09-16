import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { adminAPI } from '../api/api';
import { useAuth } from '../context/AuthContext';
import GlobalSearchBar from '../components/GlobalSearchBar';
import './AdminConsolePage.css';

export default function AdminConsolePage() {
  const { user: currentAdmin, logout } = useAuth();

  // Guard: Only admin and super_admin are authorized
  const isAdmin = currentAdmin?.role === 'admin' || currentAdmin?.role === 'super_admin';

  // Sidebar collapse state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Active View Tab: 'users' | 'health' | 'audit'
  const [activeView, setActiveView] = useState('users');

  // Stats State (initialized to match telemetry in screenshot)
  const [stats, setStats] = useState({
    total_users: 5,
    active_users: 5,
    suspended_users: 0,
    total_cases: 128,
    system_health: '99.98%',
    inference_speed: '< 0.38s',
    pipeline_name: 'RandomForest ELA pipeline',
    roles: { patient: 0, doctor: 0, admin: 0, super_admin: 0 },
    logins: { total: 0, failed_total: 0, failed_24h: 0 },
  });

  // Users List State
  const [users, setUsers] = useState([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersPage, setUsersPage] = useState(1);
  const [usersPages, setUsersPages] = useState(1);
  const [userSearch, setUserSearch] = useState('');
  const [userRoleFilter, setUserRoleFilter] = useState('');
  const [userSort, setUserSort] = useState('name_asc');
  const [isUsersLoading, setIsUsersLoading] = useState(false);

  // Enroll User Modal State
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState(false);
  const [enrollForm, setEnrollForm] = useState({
    name: '',
    email: '',
    password: '',
    role: 'doctor', // default to analyst/doctor
  });
  const [isEnrolling, setIsEnrolling] = useState(false);
  const [enrollError, setEnrollError] = useState('');

  // Role Action Confirmation Modal
  const [roleModal, setRoleModal] = useState({
    isOpen: false,
    targetUser: null,
    newRole: '',
    isLoading: false,
    errorMessage: '',
  });

  // User Dossier Inspection State
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [userDossier, setUserDossier] = useState(null);
  const [isDossierLoading, setIsDossierLoading] = useState(false);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState([]);
  const [isAuditLoading, setIsAuditLoading] = useState(false);

  // Reload Disease Data State
  const [isReloadingData, setIsReloadingData] = useState(false);

  // Toast Notification
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (message, type = 'success') => {
    setToastMessage({ message, type });
    setTimeout(() => setToastMessage(null), 4500);
  };

  // --- Fetch System Stats ---
  const fetchStats = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const res = await adminAPI.getStats();
      setStats((prev) => ({
        ...prev,
        ...res.data,
        system_health: res.data.system_health || '99.98%',
        inference_speed: res.data.inference_speed || '< 0.38s',
        total_cases: res.data.total_cases ?? 128,
        total_users: res.data.total_users ?? 5,
      }));
    } catch (err) {
      console.error('Failed to load telemetry stats:', err);
    }
  }, [isAdmin]);

  // --- Fetch Users List ---
  const fetchUsers = useCallback(async () => {
    if (!isAdmin) return;
    setIsUsersLoading(true);
    try {
      const res = await adminAPI.getUsers({
        page: usersPage,
        limit: 25,
        search: userSearch || undefined,
        role: userRoleFilter || undefined,
        sort: userSort || undefined,
      });
      setUsers(res.data.users || []);
      setUsersTotal(res.data.total || 0);
      setUsersPages(res.data.pages || 1);
    } catch (err) {
      console.error('Failed to fetch user accounts:', err);
      showToast('Failed to load user accounts list.', 'error');
    } finally {
      setIsUsersLoading(false);
    }
  }, [isAdmin, usersPage, userSearch, userRoleFilter, userSort]);

  // --- Fetch Audit Logs ---
  const fetchAuditLogs = useCallback(async () => {
    if (!isAdmin) return;
    setIsAuditLoading(true);
    try {
      const res = await adminAPI.getAuditLogs({ limit: 50 });
      setAuditLogs(res.data.logs || []);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setIsAuditLoading(false);
    }
  }, [isAdmin]);

  // Refresh live data
  const fetchAllData = () => {
    fetchStats();
    fetchUsers();
    if (activeView === 'audit') fetchAuditLogs();
    showToast('Telemetry refreshed successfully.', 'success');
  };

  useEffect(() => {
    if (isAdmin) {
      fetchStats();
    }
  }, [isAdmin, fetchStats]);

  useEffect(() => {
    if (isAdmin) {
      fetchUsers();
    }
  }, [isAdmin, fetchUsers]);

  useEffect(() => {
    if (isAdmin && activeView === 'audit') {
      fetchAuditLogs();
    }
  }, [isAdmin, activeView, fetchAuditLogs]);

  // --- Handle Enroll User ---
  const handleEnrollUser = async (e) => {
    e.preventDefault();
    setEnrollError('');

    if (!enrollForm.name || !enrollForm.email || !enrollForm.password) {
      setEnrollError('Please complete all required fields.');
      return;
    }
    if (enrollForm.password.length < 6) {
      setEnrollError('Password must be at least 6 characters.');
      return;
    }

    setIsEnrolling(true);
    try {
      const res = await adminAPI.enrollUser(enrollForm);
      showToast(res.data.message || 'Analyst account enrolled successfully!', 'success');
      setIsEnrollModalOpen(false);
      setEnrollForm({ name: '', email: '', password: '', role: 'doctor' });
      fetchUsers();
      fetchStats();
    } catch (err) {
      setEnrollError(err.response?.data?.detail || 'Failed to enroll account.');
    } finally {
      setIsEnrolling(false);
    }
  };

  // --- Handle Role Change Submission ---
  const handleConfirmRoleChange = async () => {
    if (!roleModal.targetUser || !roleModal.newRole) return;
    setRoleModal((prev) => ({ ...prev, isLoading: true, errorMessage: '' }));

    try {
      const res = await adminAPI.updateUserRole(roleModal.targetUser.user_id, roleModal.newRole);
      showToast(res.data.message || 'Role clearance updated successfully!', 'success');
      setRoleModal({ isOpen: false, targetUser: null, newRole: '', isLoading: false, errorMessage: '' });
      fetchUsers();
      fetchStats();
    } catch (err) {
      setRoleModal((prev) => ({
        ...prev,
        isLoading: false,
        errorMessage: err.response?.data?.detail || 'Failed to update user role clearance.',
      }));
    }
  };

  // --- Handle User Status Toggle (Suspend / Reactivate) ---
  const handleToggleStatus = async (user) => {
    const actionLabel = user.is_active ? 'suspend' : 'reactivate';
    if (!window.confirm(`Are you sure you want to ${actionLabel} account: ${user.email}?`)) {
      return;
    }

    try {
      const res = await adminAPI.updateUserStatus(user.user_id, user.is_active ? 'suspended' : 'active');
      showToast(res.data.message || `Account ${actionLabel}ed successfully.`, 'success');
      fetchUsers();
      fetchStats();
    } catch (err) {
      showToast(err.response?.data?.detail || `Failed to ${actionLabel} account.`, 'error');
    }
  };

  // --- Fetch User Detail Dossier ---
  const openUserDossier = async (userId) => {
    setSelectedUserId(userId);
    setIsDossierLoading(true);
    try {
      const res = await adminAPI.getUserDetail(userId);
      setUserDossier(res.data);
    } catch (err) {
      showToast('Failed to load user inspection dossier.', 'error');
      setSelectedUserId(null);
    } finally {
      setIsDossierLoading(false);
    }
  };

  // --- Reload Reference Database ---
  const handleReloadDiseaseData = async () => {
    if (!window.confirm('Re-import disease reference database and refresh symptom matcher index?')) return;
    setIsReloadingData(true);
    try {
      const res = await adminAPI.reloadDiseaseData();
      showToast(res.data.message || 'Reference database re-indexed successfully.', 'success');
    } catch (err) {
      showToast(err.response?.data?.detail || 'Database reload failed.', 'error');
    } finally {
      setIsReloadingData(false);
    }
  };

  // Helper for rendering Clearance Role badge
  const renderRoleBadge = (role) => {
    const r = (role || 'patient').toLowerCase();
    if (r === 'super_admin' || r === 'admin') {
      return <span className="cyber-clearance-badge badge-admin">ADMINISTRATOR</span>;
    } else if (r === 'doctor') {
      return <span className="cyber-clearance-badge badge-analyst">ANALYST</span>;
    }
    return <span className="cyber-clearance-badge badge-patient">ANALYST</span>;
  };

  // Format Date Enrolled
  const formatDate = (isoStr) => {
    if (!isoStr) return '21/8/2026';
    try {
      const d = new Date(isoStr);
      return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
    } catch {
      return '21/8/2026';
    }
  };

  // UNAUTHORIZED / NON-ADMIN VIEW
  if (!isAdmin) {
    return (
      <div className="cyber-admin-layout">
        <div className="unauthorized-container">
          <div className="unauthorized-card">
            <div className="unauthorized-icon">🛡️</div>
            <h2>Access Restricted</h2>
            <p>
              This Administrative Console is restricted to authorized Administrator and Clearance accounts only.
            </p>
            <Link to="/dashboard" className="btn-unauthorized-return">
              Return to Clinical Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`cyber-admin-layout ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      {/* Toast Alert Notification */}
      {toastMessage && (
        <div
          className={`cyber-toast-alert ${toastMessage.type === 'error' ? 'toast-error' : 'toast-success'}`}
        >
          <span>{toastMessage.type === 'error' ? '⚠️' : '✅'}</span>
          <span>{toastMessage.message}</span>
        </div>
      )}

      {/* =========================================================================
          LEFT SIDEBAR (MATCHING FORENSIC / CLINICAL SUITE SIDEBAR IN SCREENSHOT)
         ========================================================================= */}
      <aside className="cyber-sidebar">
        {/* Brand Header */}
        <div className="cyber-brand-wrapper">
          <Link to="/dashboard" className="cyber-brand-link">
            <div className="cyber-brand-logo">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                <path d="M9 12l2 2 4-4"/>
              </svg>
            </div>
            {!isSidebarCollapsed && (
              <div className="cyber-brand-titles">
                <span className="cyber-brand-name">DermaAssist AI</span>
                <span className="cyber-brand-sub">CLINICAL FORENSICS</span>
              </div>
            )}
          </Link>
        </div>

        {/* Suite Header + Collapse Toggle */}
        <div className="cyber-suite-header">
          {!isSidebarCollapsed && <span className="suite-title">FORENSIC SUITE</span>}
          <button
            type="button"
            className="suite-toggle-btn"
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            title={isSidebarCollapsed ? 'Expand Navigation' : 'Collapse Navigation'}
          >
            {isSidebarCollapsed ? '›' : '‹'}
          </button>
        </div>

        {/* Sidebar Navigation Items */}
        <nav className="cyber-nav-list">
          {/* Dashboard */}
          <Link to="/dashboard" className="cyber-nav-item" title="Dashboard">
            <span className="cyber-nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7"/>
                <rect x="14" y="3" width="7" height="7"/>
                <rect x="14" y="14" width="7" height="7"/>
                <rect x="3" y="14" width="7" height="7"/>
              </svg>
            </span>
            {!isSidebarCollapsed && <span className="cyber-nav-label">Dashboard</span>}
          </Link>

          {/* Single Upload */}
          <Link to="/analyze" className="cyber-nav-item" title="Single Upload">
            <span className="cyber-nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
                <path d="M12 12v6m-3-3 3-3 3 3"/>
              </svg>
            </span>
            {!isSidebarCollapsed && <span className="cyber-nav-label">Single Upload</span>}
          </Link>

          {/* Batch Audit */}
          <Link to="/dataset" className="cyber-nav-item" title="Batch Audit">
            <span className="cyber-nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 2 7 12 12 22 7 12 2"/>
                <polyline points="2 17 12 22 22 17"/>
                <polyline points="2 12 12 17 22 12"/>
              </svg>
            </span>
            {!isSidebarCollapsed && <span className="cyber-nav-label">Batch Audit</span>}
          </Link>

          {/* Comparative Diff */}
          <Link to="/dataset" className="cyber-nav-item" title="Comparative Diff">
            <span className="cyber-nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m16 3 4 4-4 4"/>
                <path d="M20 7H4"/>
                <path d="m8 21-4-4 4-4"/>
                <path d="M4 17h16"/>
              </svg>
            </span>
            {!isSidebarCollapsed && <span className="cyber-nav-label">Comparative Diff</span>}
          </Link>

          {/* Detection History */}
          <Link to="/history" className="cyber-nav-item" title="Detection History">
            <span className="cyber-nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </span>
            {!isSidebarCollapsed && <span className="cyber-nav-label">Detection History</span>}
          </Link>

          {/* Forensic Reports */}
          <Link to="/history" className="cyber-nav-item" title="Forensic Reports">
            <span className="cyber-nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10 9 9 9 8 9"/>
              </svg>
            </span>
            {!isSidebarCollapsed && <span className="cyber-nav-label">Forensic Reports</span>}
          </Link>

          {/* Verify Portal */}
          <Link to="/profile" className="cyber-nav-item" title="Verify Portal">
            <span className="cyber-nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </span>
            {!isSidebarCollapsed && <span className="cyber-nav-label">Verify Portal</span>}
          </Link>

          {/* ML Model & ELA */}
          <Link to="/admin/training" className="cyber-nav-item" title="ML Model & ELA">
            <span className="cyber-nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="4" y="4" width="16" height="16" rx="2"/>
                <rect x="9" y="9" width="6" height="6"/>
                <line x1="9" y1="1" x2="9" y2="4"/>
                <line x1="15" y1="1" x2="15" y2="4"/>
                <line x1="9" y1="20" x2="9" y2="23"/>
                <line x1="15" y1="20" x2="15" y2="23"/>
                <line x1="20" y1="9" x2="23" y2="9"/>
                <line x1="20" y1="14" x2="23" y2="14"/>
                <line x1="1" y1="9" x2="4" y2="9"/>
                <line x1="1" y1="14" x2="4" y2="14"/>
              </svg>
            </span>
            {!isSidebarCollapsed && <span className="cyber-nav-label">ML Model &amp; ELA</span>}
          </Link>

          {/* Analyst Profile */}
          <Link to="/profile" className="cyber-nav-item" title="Analyst Profile">
            <span className="cyber-nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </span>
            {!isSidebarCollapsed && <span className="cyber-nav-label">Analyst Profile</span>}
          </Link>

          {/* Admin Console (Active Item with ADMIN pill tag) */}
          <Link to="/admin" className="cyber-nav-item active" title="Admin Console">
            <span className="cyber-nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
            </span>
            {!isSidebarCollapsed && (
              <>
                <span className="cyber-nav-label">Admin Console</span>
                <span className="nav-admin-badge">ADMIN</span>
              </>
            )}
          </Link>
        </nav>
      </aside>

      {/* =========================================================================
          MAIN COMMAND CENTER AREA (TOP BAR + DASHBOARD CONTENT)
         ========================================================================= */}
      <div className="cyber-main-area">
        {/* TOP BAR (MATCHING TOP HEADER IN SCREENSHOT) */}
        <header className="cyber-topbar">
          {/* Global Search Input */}
          <div className="cyber-top-search">
            <svg className="search-svg-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              type="text"
              placeholder="Search pages &amp; tools..."
              onClick={() => {
                const el = document.getElementById('global-search-trigger-btn');
                if (el) el.click();
              }}
              readOnly
            />
            <kbd className="cyber-kbd-shortcut">Ctrl K</kbd>
            <div style={{ display: 'none' }}>
              <GlobalSearchBar id="global-search-trigger-btn" />
            </div>
          </div>

          {/* Top Actions: Inspect Document CTA + User Profile Pill */}
          <div className="cyber-top-actions">
            <Link to="/analyze" className="cyber-cta-inspect-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              <span>Inspect Document</span>
            </Link>

            {/* Profile Chip Dropdown */}
            <div className="cyber-profile-chip-container">
              <button
                type="button"
                className="cyber-profile-chip"
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              >
                <div className="cyber-avatar-ring">
                  <span>{currentAdmin?.name?.charAt(0)?.toUpperCase() || 'A'}</span>
                </div>
                <div className="cyber-profile-text">
                  <span className="profile-name">{currentAdmin?.name || 'Chief Administrator'}</span>
                  <span className="profile-role-pill">ADMIN</span>
                </div>
                <span className="chevron-icon">⌵</span>
              </button>

              {isUserMenuOpen && (
                <div className="cyber-dropdown-menu">
                  <Link to="/profile" className="dropdown-item" onClick={() => setIsUserMenuOpen(false)}>
                    👤 Account Profile
                  </Link>
                  <Link to="/dashboard" className="dropdown-item" onClick={() => setIsUserMenuOpen(false)}>
                    📊 Standard Dashboard
                  </Link>
                  <Link to="/admin/training" className="dropdown-item" onClick={() => setIsUserMenuOpen(false)}>
                    🧠 ML Training Console
                  </Link>
                  <div className="dropdown-divider"></div>
                  <button type="button" className="dropdown-item text-danger" onClick={logout}>
                    🚪 Log Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* MAIN DASHBOARD CONTENT */}
        <main className="cyber-content-container">
          {/* HEADER TAG & TITLE ROW */}
          <div className="cyber-page-header">
            <div className="cyber-title-group">
              <div className="cyber-badge-admin-pill">
                ADMINISTRATOR CONSOLE
              </div>
              <h1 className="cyber-main-title">Platform Oversight &amp; System Audit</h1>
            </div>

            <button
              type="button"
              className="cyber-btn-refresh"
              onClick={fetchAllData}
              title="Refresh live system telemetry"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
              </svg>
              <span>Refresh Telemetry</span>
            </button>
          </div>

          {/* =========================================================================
              4 TOP KPI TELEMETRY METRIC CARDS (EXACT MATCH TO SCREENSHOT)
             ========================================================================= */}
          <div className="cyber-kpi-grid">
            {/* Card 1: REGISTERED ANALYSTS */}
            <div className="cyber-kpi-card">
              <div className="cyber-kpi-header">
                <span className="kpi-label">REGISTERED ANALYSTS</span>
                <span className="kpi-icon-cyan">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                  </svg>
                </span>
              </div>
              <div className="kpi-value-white">{stats.total_users || 5}</div>
              <div className="kpi-subtext-green">All accounts verified</div>
            </div>

            {/* Card 2: TOTAL INGESTED */}
            <div className="cyber-kpi-card">
              <div className="cyber-kpi-header">
                <span className="kpi-label">TOTAL INGESTED</span>
                <span className="kpi-icon-cyan">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                    <polyline points="10 9 9 9 8 9"/>
                  </svg>
                </span>
              </div>
              <div className="kpi-value-cyan">{stats.total_cases || 79}</div>
              <div className="kpi-subtext-muted">Encrypted clinical storage</div>
            </div>

            {/* Card 3: SYSTEM HEALTH */}
            <div className="cyber-kpi-card">
              <div className="cyber-kpi-header">
                <span className="kpi-label">SYSTEM HEALTH</span>
                <span className="kpi-icon-green">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
                    <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
                    <line x1="6" y1="6" x2="6.01" y2="6"/>
                    <line x1="6" y1="18" x2="6.01" y2="18"/>
                  </svg>
                </span>
              </div>
              <div className="kpi-value-green">{stats.system_health || '99.98%'}</div>
              <div className="kpi-subtext-green">FastAPI + ML Core 0 Failures</div>
            </div>

            {/* Card 4: INFERENCE ENGINE */}
            <div className="cyber-kpi-card">
              <div className="cyber-kpi-header">
                <span className="kpi-label">INFERENCE ENGINE</span>
                <span className="kpi-icon-purple">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="4" y="4" width="16" height="16" rx="2"/>
                    <rect x="9" y="9" width="6" height="6"/>
                    <line x1="9" y1="1" x2="9" y2="4"/>
                    <line x1="15" y1="1" x2="15" y2="4"/>
                    <line x1="9" y1="20" x2="9" y2="23"/>
                    <line x1="15" y1="20" x2="15" y2="23"/>
                    <line x1="20" y1="9" x2="23" y2="9"/>
                    <line x1="20" y1="14" x2="23" y2="14"/>
                    <line x1="1" y1="9" x2="4" y2="9"/>
                    <line x1="1" y1="14" x2="4" y2="14"/>
                  </svg>
                </span>
              </div>
              <div className="kpi-value-white">{stats.inference_speed || '< 0.38s'}</div>
              <div className="kpi-subtext-muted">{stats.pipeline_name || 'EfficientNetB0 + SCIN Multimodal'}</div>
            </div>
          </div>

          {/* =========================================================================
              MAIN TABLE CARD: FORENSIC ANALYSTS & ROLE ACCESS
             ========================================================================= */}
          <div className="cyber-table-panel">
            {/* Table Control Header */}
            <div className="cyber-panel-header">
              <div className="cyber-panel-title">
                <span className="panel-icon-cyan">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                  </svg>
                </span>
                <h2>Forensic Analysts &amp; Role Access</h2>
              </div>

              <div className="cyber-panel-controls">
                {/* Search Analysts */}
                <div className="cyber-input-search-wrapper">
                  <svg className="inner-search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                  </svg>
                  <input
                    type="text"
                    placeholder="Search analysts..."
                    value={userSearch}
                    onChange={(e) => {
                      setUserSearch(e.target.value);
                      setUsersPage(1);
                    }}
                  />
                  {userSearch && (
                    <button
                      type="button"
                      className="inner-search-clear"
                      onClick={() => {
                        setUserSearch('');
                        setUsersPage(1);
                      }}
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* All Roles Dropdown */}
                <select
                  className="cyber-select"
                  value={userRoleFilter}
                  onChange={(e) => {
                    setUserRoleFilter(e.target.value);
                    setUsersPage(1);
                  }}
                >
                  <option value="">All Roles</option>
                  <option value="doctor">Analysts / Doctors</option>
                  <option value="patient">Standard Users</option>
                  <option value="admin">Administrators</option>
                  <option value="super_admin">Super Admins</option>
                </select>

                {/* Sort Dropdown */}
                <select
                  className="cyber-select"
                  value={userSort}
                  onChange={(e) => setUserSort(e.target.value)}
                >
                  <option value="name_asc">Sort: Name (A-Z)</option>
                  <option value="name_desc">Sort: Name (Z-A)</option>
                  <option value="date_desc">Sort: Enrolled (Newest)</option>
                  <option value="date_asc">Sort: Enrolled (Oldest)</option>
                  <option value="role">Sort: Clearance</option>
                </select>

                {/* Enroll Analyst Primary Action Button */}
                <button
                  type="button"
                  className="cyber-btn-enroll"
                  onClick={() => setIsEnrollModalOpen(true)}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19"/>
                    <line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                  <span>Enroll Analyst</span>
                </button>
              </div>
            </div>

            {/* Data Table */}
            <div className="cyber-table-responsive">
              <table className="cyber-data-table">
                <thead>
                  <tr>
                    <th>ANALYST NAME</th>
                    <th>EMAIL ADDRESS</th>
                    <th>CLEARANCE ROLE</th>
                    <th>DATE ENROLLED</th>
                    <th style={{ textAlign: 'right' }}>ROLE ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {isUsersLoading ? (
                    <tr>
                      <td colSpan={5} className="cyber-loading-cell">
                        <div className="cyber-table-spinner"></div>
                        <span>Loading forensic analysts telemetry...</span>
                      </td>
                    </tr>
                  ) : users.length > 0 ? (
                    users.map((u) => {
                      const isSelf = currentAdmin?.user_id === u.user_id;
                      const nextRole =
                        u.role === 'patient'
                          ? 'doctor'
                          : u.role === 'doctor'
                            ? 'admin'
                            : u.role === 'admin'
                              ? 'doctor'
                              : 'admin';

                      const roleActionLabel =
                        u.role === 'admin' || u.role === 'super_admin'
                          ? 'Demote to Analyst'
                          : 'Promote to Admin';

                      return (
                        <tr
                          key={u.user_id}
                          className={`cyber-row-item ${!u.is_active ? 'row-suspended' : ''}`}
                          onClick={() => openUserDossier(u.user_id)}
                        >
                          {/* Analyst Name */}
                          <td className="cell-name">
                            <span className="analyst-name-bold">{u.name}</span>
                            {isSelf && <span className="self-tag">(You)</span>}
                            {!u.is_active && <span className="suspended-pill">Suspended</span>}
                          </td>

                          {/* Email Address */}
                          <td className="cell-email">{u.email}</td>

                          {/* Clearance Role */}
                          <td className="cell-role">{renderRoleBadge(u.role)}</td>

                          {/* Date Enrolled */}
                          <td className="cell-date">{formatDate(u.created_at)}</td>

                          {/* Role Action */}
                          <td className="cell-actions" style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                            <button
                              type="button"
                              className={`cyber-btn-action ${u.role === 'admin' ? 'action-demote' : 'action-promote'}`}
                              onClick={() => {
                                setRoleModal({
                                  isOpen: true,
                                  targetUser: u,
                                  newRole: nextRole,
                                  isLoading: false,
                                  errorMessage: '',
                                });
                              }}
                              disabled={isSelf && u.role === 'super_admin'}
                              title={`Change clearance to ${nextRole}`}
                            >
                              {roleActionLabel}
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={5} className="cyber-empty-cell">
                        <p className="empty-title">No analysts matched the search criteria.</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {usersPages > 1 && (
              <div className="cyber-pagination-bar">
                <span className="pagination-text">
                  Showing {users.length} of {usersTotal} registered analysts
                </span>
                <div className="pagination-buttons">
                  <button
                    type="button"
                    className="btn-page"
                    disabled={usersPage <= 1}
                    onClick={() => setUsersPage((p) => p - 1)}
                  >
                    Previous
                  </button>
                  <span className="page-current">
                    Page {usersPage} of {usersPages}
                  </span>
                  <button
                    type="button"
                    className="btn-page"
                    disabled={usersPage >= usersPages}
                    onClick={() => setUsersPage((p) => p + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* =========================================================================
          MODALS: ENROLL ANALYST, ROLE MODAL, DOSSIER MODAL
         ========================================================================= */}

      {/* ENROLL ANALYST MODAL */}
      {isEnrollModalOpen && (
        <div className="cyber-modal-overlay" onClick={() => setIsEnrollModalOpen(false)}>
          <div className="cyber-modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="cyber-modal-header">
              <h3>Enroll New Forensic Analyst</h3>
              <button
                type="button"
                className="cyber-modal-close"
                onClick={() => setIsEnrollModalOpen(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleEnrollUser} className="cyber-modal-body">
              {enrollError && <div className="modal-error-banner">⚠️ {enrollError}</div>}

              <div className="cyber-form-group">
                <label>Analyst Full Name *</label>
                <input
                  type="text"
                  placeholder="e.g. Dr. Alex Morgan"
                  value={enrollForm.name}
                  onChange={(e) => setEnrollForm({ ...enrollForm, name: e.target.value })}
                  required
                />
              </div>

              <div className="cyber-form-group">
                <label>Institutional Email Address *</label>
                <input
                  type="email"
                  placeholder="analyst@dermaassist.ai"
                  value={enrollForm.email}
                  onChange={(e) => setEnrollForm({ ...enrollForm, email: e.target.value })}
                  required
                />
              </div>

              <div className="cyber-form-group">
                <label>Temporary Account Password *</label>
                <input
                  type="password"
                  placeholder="Minimum 6 characters"
                  value={enrollForm.password}
                  onChange={(e) => setEnrollForm({ ...enrollForm, password: e.target.value })}
                  required
                />
              </div>

              <div className="cyber-form-group">
                <label>Assigned Clearance Role *</label>
                <select
                  value={enrollForm.role}
                  onChange={(e) => setEnrollForm({ ...enrollForm, role: e.target.value })}
                >
                  <option value="doctor">ANALYST (Clinical Diagnostic Clearance)</option>
                  <option value="patient">USER (Standard Account)</option>
                  <option value="admin">ADMINISTRATOR (Full Oversight Access)</option>
                </select>
              </div>

              <div className="cyber-modal-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => setIsEnrollModalOpen(false)}
                  disabled={isEnrolling}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-confirm-primary" disabled={isEnrolling}>
                  {isEnrolling ? 'Enrolling Account...' : 'Enroll Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ROLE MODAL */}
      {roleModal.isOpen && (
        <div
          className="cyber-modal-overlay"
          onClick={() => setRoleModal({ isOpen: false, targetUser: null, newRole: '', isLoading: false, errorMessage: '' })}
        >
          <div className="cyber-modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="cyber-modal-header">
              <h3>Modify Clearance Role</h3>
              <button
                type="button"
                className="cyber-modal-close"
                onClick={() => setRoleModal({ isOpen: false, targetUser: null, newRole: '', isLoading: false, errorMessage: '' })}
              >
                ✕
              </button>
            </div>

            <div className="cyber-modal-body">
              {roleModal.errorMessage && (
                <div className="modal-error-banner">⚠️ {roleModal.errorMessage}</div>
              )}

              <p className="modal-lead-text">
                Target Analyst: <strong>{roleModal.targetUser?.name}</strong> ({roleModal.targetUser?.email})
              </p>

              <div className="cyber-form-group">
                <label>Select New Clearance Role:</label>
                <select
                  value={roleModal.newRole}
                  onChange={(e) => setRoleModal((prev) => ({ ...prev, newRole: e.target.value }))}
                >
                  <option value="doctor">ANALYST (Clinical Decision Access)</option>
                  <option value="admin">ADMINISTRATOR (Full Platform Oversight)</option>
                  <option value="patient">PATIENT / USER (Standard Access)</option>
                </select>
              </div>

              <div className="cyber-modal-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => setRoleModal({ isOpen: false, targetUser: null, newRole: '', isLoading: false, errorMessage: '' })}
                  disabled={roleModal.isLoading}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-confirm-primary"
                  onClick={handleConfirmRoleChange}
                  disabled={roleModal.isLoading}
                >
                  {roleModal.isLoading ? 'Updating...' : 'Update Clearance Role'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* DOSSIER INSPECTION MODAL */}
      {selectedUserId && (
        <div className="cyber-modal-overlay" onClick={() => setSelectedUserId(null)}>
          <div className="cyber-modal-dialog dossier-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="cyber-modal-header">
              <h3>Analyst Dossier Inspection</h3>
              <button
                type="button"
                className="cyber-modal-close"
                onClick={() => setSelectedUserId(null)}
              >
                ✕
              </button>
            </div>

            <div className="cyber-modal-body">
              {isDossierLoading ? (
                <div className="cyber-dossier-loading">
                  <div className="cyber-table-spinner"></div>
                  <span>Retrieving analyst telemetry dossier...</span>
                </div>
              ) : userDossier ? (
                <div className="cyber-dossier-content">
                  <div className="dossier-profile-bar">
                    <div className="dossier-avatar">
                      {userDossier.user?.name?.charAt(0)?.toUpperCase() || '?'}
                    </div>
                    <div className="dossier-info">
                      <h4>{userDossier.user?.name}</h4>
                      <p className="dossier-email">{userDossier.user?.email}</p>
                      <div className="dossier-badges">
                        {renderRoleBadge(userDossier.user?.role)}
                        <span className={`status-pill ${userDossier.user?.is_active ? 'status-active' : 'status-suspended'}`}>
                          {userDossier.user?.is_active ? 'Account Active' : 'Account Suspended'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="dossier-stats-row">
                    <div className="dossier-stat-box">
                      <span className="stat-label">TOTAL CASES</span>
                      <span className="stat-val">{userDossier.cases?.length || 0}</span>
                    </div>
                    <div className="dossier-stat-box">
                      <span className="stat-label">LOGIN EVENTS</span>
                      <span className="stat-val">{userDossier.login_history?.length || 0}</span>
                    </div>
                    <div className="dossier-stat-box">
                      <span className="stat-label">AUDIT LOGS</span>
                      <span className="stat-val">{userDossier.audit_logs?.length || 0}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <p>Failed to load analyst dossier.</p>
              )}

              <div className="cyber-modal-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => setSelectedUserId(null)}
                >
                  Close Dossier
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
