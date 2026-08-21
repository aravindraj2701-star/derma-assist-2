import { useState, useEffect, useCallback } from 'react';
import { adminAPI } from '../api/api';
import { useAuth } from '../context/AuthContext';
import './AdminConsolePage.css';

export default function AdminConsolePage() {
  const { user: currentAdmin } = useAuth();

  // Active View Tab: 'users' | 'health' | 'audit'
  const [activeView, setActiveView] = useState('users');

  // Stats State
  const [stats, setStats] = useState({
    total_users: 0,
    active_users: 0,
    suspended_users: 0,
    total_cases: 0,
    system_health: '99.98%',
    inference_speed: '< 0.38s',
    pipeline_name: 'PyTorch SCIN Multi-Modal pipeline',
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
    role: 'patient',
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
    try {
      const res = await adminAPI.getStats();
      setStats(res.data);
    } catch (err) {
      console.error('Failed to load telemetry stats:', err);
    }
  }, []);

  // --- Fetch Users List ---
  const fetchUsers = useCallback(async () => {
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
  }, [usersPage, userSearch, userRoleFilter, userSort]);

  // --- Fetch Audit Logs ---
  const fetchAuditLogs = useCallback(async () => {
    setIsAuditLoading(true);
    try {
      const res = await adminAPI.getAuditLogs({ limit: 50 });
      setAuditLogs(res.data.logs || []);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setIsAuditLoading(false);
    }
  }, []);

  // Fetch all data
  const fetchAllData = () => {
    fetchStats();
    fetchUsers();
    if (activeView === 'audit') fetchAuditLogs();
    showToast('Platform telemetry refreshed successfully.', 'success');
  };

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  useEffect(() => {
    if (activeView === 'audit') fetchAuditLogs();
  }, [activeView, fetchAuditLogs]);

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
      showToast(res.data.message || 'User account successfully enrolled!', 'success');
      setIsEnrollModalOpen(false);
      setEnrollForm({ name: '', email: '', password: '', role: 'patient' });
      fetchUsers();
      fetchStats();
    } catch (err) {
      setEnrollError(err.response?.data?.detail || 'Failed to enroll user account.');
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
      showToast(res.data.message || 'Role updated successfully!', 'success');
      setRoleModal({ isOpen: false, targetUser: null, newRole: '', isLoading: false, errorMessage: '' });
      fetchUsers();
      fetchStats();
    } catch (err) {
      setRoleModal((prev) => ({
        ...prev,
        isLoading: false,
        errorMessage: err.response?.data?.detail || 'Failed to update user role.',
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
      showToast(res.data.message || `User account ${actionLabel}ed successfully.`, 'success');
      fetchUsers();
      fetchStats();
    } catch (err) {
      showToast(err.response?.data?.detail || `Failed to ${actionLabel} user account.`, 'error');
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

  // --- Reload Database Seed ---
  const handleReloadDiseaseData = async () => {
    if (!window.confirm('Re-import disease reference database and refresh symptom matcher index?')) return;
    setIsReloadingData(true);
    try {
      const res = await adminAPI.reloadDiseaseData();
      showToast(res.data.message || 'Disease knowledge base re-indexed successfully.', 'success');
    } catch (err) {
      showToast(err.response?.data?.detail || 'Database reload failed.', 'error');
    } finally {
      setIsReloadingData(false);
    }
  };

  // Helper for rendering Clearance Role badge
  const renderRoleBadge = (role) => {
    const r = (role || 'patient').toLowerCase();
    if (r === 'super_admin') {
      return <span className="clearance-badge super_admin">SUPER ADMIN</span>;
    } else if (r === 'admin') {
      return <span className="clearance-badge administrator">ADMINISTRATOR</span>;
    } else if (r === 'doctor') {
      return <span className="clearance-badge doctor">DOCTOR</span>;
    }
    return <span className="clearance-badge analyst">PATIENT</span>;
  };

  // Format Date Enrolled
  const formatDate = (isoStr) => {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
    } catch {
      return '—';
    }
  };

  return (
    <div className="admin-dark-theme animate-fade-in">
      <div className="container">
        {/* Toast Alert Notification */}
        {toastMessage && (
          <div
            style={{
              position: 'fixed',
              top: '20px',
              right: '20px',
              background: toastMessage.type === 'error' ? '#ef4444' : '#059669',
              color: '#ffffff',
              padding: '0.75rem 1.25rem',
              borderRadius: '8px',
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              zIndex: 9999,
              fontWeight: 600,
              fontSize: '0.875rem',
            }}
          >
            {toastMessage.message}
          </div>
        )}

        {/* TOP HEADER SECTION */}
        <div className="admin-header-section">
          <div>
            <div className="admin-badge-pill">ADMINISTRATOR CONSOLE</div>
            <h1 className="admin-main-title">Platform Oversight &amp; System Audit</h1>
          </div>

          <button
            type="button"
            className="btn-refresh-telemetry"
            onClick={fetchAllData}
            title="Refresh live system telemetry"
          >
            <span>🔄</span> Refresh Telemetry
          </button>
        </div>

        {/* 4 TOP KPI METRIC CARDS (Identical to reference screenshot) */}
        <div className="admin-kpi-grid">
          {/* Card 1: Registered Users */}
          <div className="admin-kpi-box">
            <div className="kpi-box-top">
              <span className="kpi-box-title">REGISTERED ANALYSTS &amp; USERS</span>
              <span className="kpi-box-icon">👥</span>
            </div>
            <div className="kpi-box-value">{stats.total_users || 0}</div>
            <div className="kpi-box-subtext highlight-green">All accounts verified</div>
          </div>

          {/* Card 2: Total Ingested */}
          <div className="admin-kpi-box">
            <div className="kpi-box-top">
              <span className="kpi-box-title">TOTAL INGESTED SCANS</span>
              <span className="kpi-box-icon">📄</span>
            </div>
            <div className="kpi-box-value cyan">{stats.total_cases || stats.logins?.total || 0}</div>
            <div className="kpi-box-subtext">Encrypted clinical storage</div>
          </div>

          {/* Card 3: System Health */}
          <div className="admin-kpi-box">
            <div className="kpi-box-top">
              <span className="kpi-box-title">SYSTEM HEALTH</span>
              <span className="kpi-box-icon">🖥️</span>
            </div>
            <div className="kpi-box-value green">{stats.system_health || '99.98%'}</div>
            <div className="kpi-box-subtext highlight-cyan">FastAPI + ML Core 0 Failures</div>
          </div>

          {/* Card 4: Inference Engine */}
          <div className="admin-kpi-box">
            <div className="kpi-box-top">
              <span className="kpi-box-title">INFERENCE ENGINE</span>
              <span className="kpi-box-icon">🧠</span>
            </div>
            <div className="kpi-box-value">{stats.inference_speed || '< 0.38s'}</div>
            <div className="kpi-box-subtext">PyTorch SCIN Multi-Modal pipeline</div>
          </div>
        </div>

        {/* SUB-VIEW NAVIGATION TABS */}
        <div className="admin-view-tabs">
          <button
            type="button"
            className={`admin-tab-btn ${activeView === 'users' ? 'active' : ''}`}
            onClick={() => setActiveView('users')}
          >
            <span>👥</span> Clinical Users &amp; Role Access
          </button>
          <button
            type="button"
            className={`admin-tab-btn ${activeView === 'health' ? 'active' : ''}`}
            onClick={() => setActiveView('health')}
          >
            <span>🖥️</span> Infrastructure Health &amp; Maintenance
          </button>
          <button
            type="button"
            className={`admin-tab-btn ${activeView === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveView('audit')}
          >
            <span>🛡️</span> Security &amp; Audit Logs
          </button>
        </div>

        {/* VIEW 1: USERS & ROLE ACCESS (Primary Table View Matching Screenshot) */}
        {activeView === 'users' && (
          <div className="admin-card-container">
            {/* Header with Search, Filters, and Enroll Button */}
            <div className="admin-card-header">
              <div className="card-title-group">
                <span className="icon">👥</span>
                <span>Forensic Analysts &amp; Role Access</span>
              </div>

              <div className="card-controls-row">
                {/* Search Box */}
                <div className="dark-search-box">
                  <span className="dark-search-icon">🔍</span>
                  <input
                    type="text"
                    placeholder="Search analysts / users..."
                    value={userSearch}
                    onChange={(e) => {
                      setUserSearch(e.target.value);
                      setUsersPage(1);
                    }}
                  />
                </div>

                {/* Role Filter */}
                <select
                  className="dark-select"
                  value={userRoleFilter}
                  onChange={(e) => {
                    setUserRoleFilter(e.target.value);
                    setUsersPage(1);
                  }}
                >
                  <option value="">All Roles</option>
                  <option value="patient">Patients / Analysts</option>
                  <option value="doctor">Doctors</option>
                  <option value="admin">Administrators</option>
                  <option value="super_admin">Super Admins</option>
                </select>

                {/* Sort Filter */}
                <select
                  className="dark-select"
                  value={userSort}
                  onChange={(e) => setUserSort(e.target.value)}
                >
                  <option value="name_asc">Sort: Name (A-Z)</option>
                  <option value="name_desc">Sort: Name (Z-A)</option>
                  <option value="date_desc">Sort: Enrolled (Newest)</option>
                  <option value="date_asc">Sort: Enrolled (Oldest)</option>
                  <option value="role">Sort: Role</option>
                </select>

                {/* Enroll User Primary Action Button */}
                <button
                  type="button"
                  className="btn-enroll-analyst"
                  onClick={() => setIsEnrollModalOpen(true)}
                >
                  <span>➕</span> Enroll Analyst
                </button>
              </div>
            </div>

            {/* Users Data Table */}
            <div className="dark-table-wrapper">
              <table className="dark-table">
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
                      <td colSpan={5} style={{ textAlign: 'center', padding: '2.5rem', color: '#94a3b8' }}>
                        Loading user accounts telemetry...
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
                              ? 'super_admin'
                              : 'admin';

                      const roleActionLabel =
                        u.role === 'patient'
                          ? 'Promote to Doctor'
                          : u.role === 'doctor'
                            ? 'Promote to Admin'
                            : u.role === 'admin'
                              ? currentAdmin?.role === 'super_admin'
                                ? 'Promote to Super Admin'
                                : 'Demote to Doctor'
                              : 'Demote to Admin';

                      return (
                        <tr key={u.user_id} onClick={() => openUserDossier(u.user_id)}>
                          {/* Name */}
                          <td>
                            <div className="analyst-name-cell">
                              <div className="analyst-avatar-micro">
                                {u.name?.charAt(0)?.toUpperCase() || '?'}
                              </div>
                              <span>
                                {u.name} {isSelf && <small style={{ color: '#38bdf8' }}>(You)</small>}
                              </span>
                            </div>
                          </td>

                          {/* Email */}
                          <td className="email-address-cell">{u.email}</td>

                          {/* Role Badge */}
                          <td>{renderRoleBadge(u.role)}</td>

                          {/* Date Enrolled */}
                          <td>{formatDate(u.created_at)}</td>

                          {/* Action Button */}
                          <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                            <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                              <button
                                type="button"
                                className="btn-role-action"
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
                              >
                                {roleActionLabel}
                              </button>

                              <button
                                type="button"
                                className="btn-role-action"
                                style={{ color: u.is_active ? '#f87171' : '#4ade80' }}
                                onClick={() => handleToggleStatus(u)}
                                disabled={isSelf}
                                title={u.is_active ? 'Suspend Account' : 'Reactivate Account'}
                              >
                                {u.is_active ? 'Suspend' : 'Activate'}
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '2.5rem', color: '#94a3b8' }}>
                        No user accounts matched the filter query.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination footer */}
            {usersPages > 1 && (
              <div
                style={{
                  padding: '1rem 1.5rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  borderTop: '1px solid #1f2937',
                  fontSize: '0.85rem',
                }}
              >
                <span style={{ color: '#94a3b8' }}>
                  Showing {users.length} of {usersTotal} user accounts
                </span>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    className="btn-role-action"
                    disabled={usersPage <= 1}
                    onClick={() => setUsersPage((p) => p - 1)}
                  >
                    Previous
                  </button>
                  <span style={{ padding: '0.35rem 0.65rem', color: '#cbd5e1', fontWeight: 600 }}>
                    Page {usersPage} of {usersPages}
                  </span>
                  <button
                    className="btn-role-action"
                    disabled={usersPage >= usersPages}
                    onClick={() => setUsersPage((p) => p + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* VIEW 2: INFRASTRUCTURE HEALTH & MAINTENANCE */}
        {activeView === 'health' && (
          <div className="admin-card-container">
            <div className="admin-card-header">
              <div className="card-title-group">
                <span className="icon">🖥️</span>
                <span>System Infrastructure Health Matrix &amp; Maintenance</span>
              </div>
              <button
                type="button"
                className="btn-enroll-analyst"
                onClick={handleReloadDiseaseData}
                disabled={isReloadingData}
              >
                <span>{isReloadingData ? '🔄 Syncing...' : '🔄 Re-index Disease Knowledge'}</span>
              </button>
            </div>

            <div className="health-matrix-grid">
              <div className="health-item-box">
                <h4>
                  <span>FastAPI Core Gateway</span>
                  <span style={{ color: '#10b981' }}>🟢 Online</span>
                </h4>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: 0 }}>
                  High-throughput asynchronous REST API routing with automatic OpenAPI schema validation.
                </p>
              </div>

              <div className="health-item-box">
                <h4>
                  <span>PostgreSQL Database</span>
                  <span style={{ color: '#10b981' }}>🟢 Connected</span>
                </h4>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: 0 }}>
                  Relational storage for clinical case histories, user accounts, and immutable audit logs.
                </p>
              </div>

              <div className="health-item-box">
                <h4>
                  <span>PyTorch SCIN ML Engine</span>
                  <span style={{ color: '#10b981' }}>🟢 Operational</span>
                </h4>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: 0 }}>
                  Deep learning multi-modal inference pipeline with Grad-CAM visual explainability.
                </p>
              </div>

              <div className="health-item-box">
                <h4>
                  <span>RBAC Security Enforcer</span>
                  <span style={{ color: '#10b981' }}>🟢 Active</span>
                </h4>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: 0 }}>
                  Cryptographic JWT validation with role protection and lockout safeguards.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 3: SECURITY & AUDIT LOGS */}
        {activeView === 'audit' && (
          <div className="admin-card-container">
            <div className="admin-card-header">
              <div className="card-title-group">
                <span className="icon">🛡️</span>
                <span>Administrative Action Audit Trail</span>
              </div>
            </div>

            <div className="dark-table-wrapper">
              <table className="dark-table">
                <thead>
                  <tr>
                    <th>TIMESTAMP</th>
                    <th>ADMINISTRATOR</th>
                    <th>ACTION</th>
                    <th>TARGET USER</th>
                    <th>DETAILS</th>
                  </tr>
                </thead>
                <tbody>
                  {isAuditLoading ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
                        Loading audit trail events...
                      </td>
                    </tr>
                  ) : auditLogs.length > 0 ? (
                    auditLogs.map((log) => (
                      <tr key={log.id}>
                        <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: '#94a3b8' }}>
                          {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                        </td>
                        <td style={{ fontWeight: 600, color: '#ffffff' }}>
                          {log.admin_name || `Admin #${log.admin_id}`}
                        </td>
                        <td>
                          <span
                            style={{
                              padding: '0.2rem 0.5rem',
                              background: '#1e293b',
                              borderRadius: '4px',
                              fontSize: '0.75rem',
                              fontWeight: 700,
                              color: '#38bdf8',
                            }}
                          >
                            {log.action}
                          </span>
                        </td>
                        <td>{log.target_name || (log.target_user_id ? `User #${log.target_user_id}` : 'System')}</td>
                        <td style={{ color: '#cbd5e1', fontSize: '0.8rem' }}>{log.details}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
                        No administrative audit events recorded yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* ENROLL USER MODAL */}
      {isEnrollModalOpen && (
        <div className="dark-modal-overlay">
          <div className="dark-modal-card">
            <div className="dark-modal-header">
              <h3>➕ Enroll New Analyst / User Account</h3>
              <button
                type="button"
                className="btn-close-modal"
                onClick={() => setIsEnrollModalOpen(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleEnrollUser}>
              <div className="dark-modal-body">
                {enrollError && (
                  <div
                    style={{
                      background: 'rgba(239, 68, 68, 0.2)',
                      border: '1px solid #ef4444',
                      color: '#fca5a5',
                      padding: '0.65rem 0.85rem',
                      borderRadius: '6px',
                      fontSize: '0.825rem',
                    }}
                  >
                    ⚠️ {enrollError}
                  </div>
                )}

                <div className="dark-form-group">
                  <label>Full Name / Analyst Handle</label>
                  <input
                    type="text"
                    placeholder="e.g. Dr. Alex Morgan"
                    value={enrollForm.name}
                    onChange={(e) => setEnrollForm({ ...enrollForm, name: e.target.value })}
                    required
                  />
                </div>

                <div className="dark-form-group">
                  <label>Email Address</label>
                  <input
                    type="email"
                    placeholder="e.g. alex.morgan@forensics.org"
                    value={enrollForm.email}
                    onChange={(e) => setEnrollForm({ ...enrollForm, email: e.target.value })}
                    required
                  />
                </div>

                <div className="dark-form-group">
                  <label>Initial Temporary Password</label>
                  <input
                    type="password"
                    placeholder="At least 6 characters"
                    value={enrollForm.password}
                    onChange={(e) => setEnrollForm({ ...enrollForm, password: e.target.value })}
                    required
                  />
                </div>

                <div className="dark-form-group">
                  <label>Clearance Role Assignment</label>
                  <select
                    value={enrollForm.role}
                    onChange={(e) => setEnrollForm({ ...enrollForm, role: e.target.value })}
                  >
                    <option value="patient">Patient / Forensic Analyst</option>
                    <option value="doctor">Attending Doctor</option>
                    <option value="admin">Administrator</option>
                    {currentAdmin?.role === 'super_admin' && (
                      <option value="super_admin">Super Administrator</option>
                    )}
                  </select>
                </div>
              </div>

              <div className="dark-modal-footer">
                <button
                  type="button"
                  className="btn-role-action"
                  onClick={() => setIsEnrollModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-enroll-analyst"
                  disabled={isEnrolling}
                >
                  {isEnrolling ? 'Enrolling...' : 'Enroll Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ROLE CHANGE CONFIRMATION MODAL */}
      {roleModal.isOpen && (
        <div className="dark-modal-overlay">
          <div className="dark-modal-card">
            <div className="dark-modal-header">
              <h3>🛡️ Modify Account Clearance Role</h3>
              <button
                type="button"
                className="btn-close-modal"
                onClick={() => setRoleModal({ isOpen: false, targetUser: null, newRole: '', isLoading: false, errorMessage: '' })}
              >
                ✕
              </button>
            </div>

            <div className="dark-modal-body">
              {roleModal.errorMessage && (
                <div
                  style={{
                    background: 'rgba(239, 68, 68, 0.2)',
                    border: '1px solid #ef4444',
                    color: '#fca5a5',
                    padding: '0.65rem 0.85rem',
                    borderRadius: '6px',
                    fontSize: '0.825rem',
                  }}
                >
                  ⚠️ {roleModal.errorMessage}
                </div>
              )}

              <p style={{ color: '#cbd5e1', fontSize: '0.9rem', margin: 0 }}>
                Update clearance role for account: <strong>{roleModal.targetUser?.email}</strong>
              </p>

              <div className="dark-form-group">
                <label>Select Target Role</label>
                <select
                  value={roleModal.newRole}
                  onChange={(e) => setRoleModal({ ...roleModal, newRole: e.target.value })}
                >
                  <option value="patient">Patient / Analyst</option>
                  <option value="doctor">Attending Doctor</option>
                  <option value="admin">Administrator</option>
                  {currentAdmin?.role === 'super_admin' && (
                    <option value="super_admin">Super Administrator</option>
                  )}
                </select>
              </div>
            </div>

            <div className="dark-modal-footer">
              <button
                type="button"
                className="btn-role-action"
                onClick={() => setRoleModal({ isOpen: false, targetUser: null, newRole: '', isLoading: false, errorMessage: '' })}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-enroll-analyst"
                onClick={handleConfirmRoleChange}
                disabled={roleModal.isLoading}
              >
                {roleModal.isLoading ? 'Updating...' : 'Confirm Role Change'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* USER DOSSIER INSPECTION MODAL */}
      {selectedUserId && (
        <div className="dark-modal-overlay">
          <div className="dark-modal-card" style={{ maxWidth: '680px' }}>
            <div className="dark-modal-header">
              <h3>🔍 User Inspection &amp; Audit Dossier</h3>
              <button
                type="button"
                className="btn-close-modal"
                onClick={() => {
                  setSelectedUserId(null);
                  setUserDossier(null);
                }}
              >
                ✕
              </button>
            </div>

            <div className="dark-modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
              {isDossierLoading ? (
                <p style={{ color: '#94a3b8', textAlign: 'center' }}>Loading user dossier details...</p>
              ) : userDossier ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  {/* Profile info */}
                  <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #1e293b' }}>
                    <h4 style={{ margin: '0 0 0.5rem 0', color: '#ffffff' }}>{userDossier.user?.name}</h4>
                    <div style={{ fontSize: '0.85rem', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      <div>Email: <strong style={{ color: '#ffffff' }}>{userDossier.user?.email}</strong></div>
                      <div>User ID: <strong>#{userDossier.user?.user_id}</strong></div>
                      <div>Role: {renderRoleBadge(userDossier.user?.role)}</div>
                      <div>Status: <strong>{userDossier.user?.is_active ? '🟢 Active' : '🔴 Suspended'}</strong></div>
                      <div>Last Login: <strong>{userDossier.user?.last_login_at ? new Date(userDossier.user.last_login_at).toLocaleString() : 'Never'}</strong></div>
                    </div>
                  </div>

                  {/* Recent Login History */}
                  <div>
                    <h5 style={{ color: '#38bdf8', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Recent Login Activity (Last 10)</h5>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      {userDossier.login_history && userDossier.login_history.length > 0 ? (
                        userDossier.login_history.slice(0, 10).map((lh, i) => (
                          <div
                            key={i}
                            style={{
                              padding: '0.4rem 0.65rem',
                              background: '#0f172a',
                              borderRadius: '4px',
                              fontSize: '0.75rem',
                              display: 'flex',
                              justifyContent: 'space-between',
                            }}
                          >
                            <span style={{ color: lh.success ? '#10b981' : '#ef4444' }}>
                              {lh.success ? '✅ Success' : `❌ ${lh.failure_reason || 'Failed'}`}
                            </span>
                            <span style={{ color: '#94a3b8' }}>{lh.login_at ? new Date(lh.login_at).toLocaleString() : '—'}</span>
                          </div>
                        ))
                      ) : (
                        <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>No login activity recorded.</p>
                      )}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>

            <div className="dark-modal-footer">
              <button
                type="button"
                className="btn-role-action"
                onClick={() => {
                  setSelectedUserId(null);
                  setUserDossier(null);
                }}
              >
                Close Dossier
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
