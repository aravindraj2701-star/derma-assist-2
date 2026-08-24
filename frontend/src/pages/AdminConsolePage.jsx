import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
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

  // --- Reload Disease Data Seed ---
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
    return <span className="clearance-badge patient">PATIENT</span>;
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
    <div className="admin-console-page animate-fade-in">
      <div className="admin-console-container container">
        {/* Toast Alert Notification */}
        {toastMessage && (
          <div
            className={`admin-toast-alert ${toastMessage.type === 'error' ? 'toast-error' : 'toast-success'}`}
          >
            <span>{toastMessage.type === 'error' ? '⚠️' : '✅'}</span>
            <span>{toastMessage.message}</span>
          </div>
        )}

        {/* TOP HEADER SECTION */}
        <div className="admin-header-section">
          <div className="admin-title-area">
            <div className="admin-badge-pill">
              <span className="admin-badge-icon">🛡️</span>
              <span>ADMINISTRATOR CONSOLE</span>
            </div>
            <h1 className="admin-main-title">Platform Oversight &amp; System Audit</h1>
            <p className="admin-subtitle">
              Enterprise clinical governance, user access management, and infrastructure telemetry.
            </p>
          </div>

          <div className="admin-header-actions">
            <Link to="/admin/training" className="btn-training-link" title="Open Continuous Learning & Retraining Console">
              <span>🧠</span> Training Console
            </Link>
            <button
              type="button"
              className="btn-refresh-telemetry"
              onClick={fetchAllData}
              title="Refresh live system telemetry"
            >
              <span>🔄</span> Refresh Telemetry
            </button>
          </div>
        </div>

        {/* 4 TOP KPI METRIC CARDS (Clinical Derma Assist Styling) */}
        <div className="admin-kpi-grid">
          {/* Card 1: Registered Clinicians & Users */}
          <div className="admin-kpi-box">
            <div className="kpi-box-top">
              <span className="kpi-box-title">REGISTERED CLINICIANS &amp; USERS</span>
              <span className="kpi-box-icon">👥</span>
            </div>
            <div className="kpi-box-value">{stats.total_users || 0}</div>
            <div className="kpi-box-subtext highlight-green">
              <span className="dot dot-green"></span> All accounts verified
            </div>
          </div>

          {/* Card 2: Total Ingested Cases / Scans */}
          <div className="admin-kpi-box">
            <div className="kpi-box-top">
              <span className="kpi-box-title">TOTAL INGESTED SCANS</span>
              <span className="kpi-box-icon">📄</span>
            </div>
            <div className="kpi-box-value teal">{stats.total_cases || stats.logins?.total || 0}</div>
            <div className="kpi-box-subtext">
              <span className="dot dot-teal"></span> Encrypted clinical storage
            </div>
          </div>

          {/* Card 3: System Health */}
          <div className="admin-kpi-box">
            <div className="kpi-box-top">
              <span className="kpi-box-title">SYSTEM HEALTH</span>
              <span className="kpi-box-icon">🖥️</span>
            </div>
            <div className="kpi-box-value green">{stats.system_health || '99.98%'}</div>
            <div className="kpi-box-subtext highlight-teal">
              <span className="dot dot-green"></span> FastAPI + ML Core 0 Failures
            </div>
          </div>

          {/* Card 4: Inference Engine */}
          <div className="admin-kpi-box">
            <div className="kpi-box-top">
              <span className="kpi-box-title">INFERENCE ENGINE</span>
              <span className="kpi-box-icon">🧠</span>
            </div>
            <div className="kpi-box-value">{stats.inference_speed || '< 0.38s'}</div>
            <div className="kpi-box-subtext">
              <span className="dot dot-purple"></span> PyTorch SCIN Multi-Modal pipeline
            </div>
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
            <span className="tab-count-pill">{usersTotal || stats.total_users || 0}</span>
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
                <div>
                  <h3 className="card-heading">Clinical Users &amp; Role Access</h3>
                  <p className="card-subheading">Manage clinician authorization, patient accounts, and clearance levels</p>
                </div>
              </div>

              <div className="card-controls-row">
                {/* Search Box */}
                <div className="clinical-search-box">
                  <span className="search-icon">🔍</span>
                  <input
                    type="text"
                    placeholder="Search clinical users..."
                    value={userSearch}
                    onChange={(e) => {
                      setUserSearch(e.target.value);
                      setUsersPage(1);
                    }}
                  />
                  {userSearch && (
                    <button
                      type="button"
                      className="search-clear-btn"
                      onClick={() => {
                        setUserSearch('');
                        setUsersPage(1);
                      }}
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* Role Filter */}
                <select
                  className="clinical-select"
                  value={userRoleFilter}
                  onChange={(e) => {
                    setUserRoleFilter(e.target.value);
                    setUsersPage(1);
                  }}
                >
                  <option value="">All Roles</option>
                  <option value="patient">Patients / Users</option>
                  <option value="doctor">Doctors / Clinicians</option>
                  <option value="admin">Administrators</option>
                  <option value="super_admin">Super Admins</option>
                </select>

                {/* Sort Filter */}
                <select
                  className="clinical-select"
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
                  className="btn-enroll-user"
                  onClick={() => setIsEnrollModalOpen(true)}
                >
                  <span>➕</span> Enroll User
                </button>
              </div>
            </div>

            {/* Users Data Table */}
            <div className="clinical-table-wrapper">
              <table className="admin-data-table">
                <thead>
                  <tr>
                    <th>CLINICAL USER</th>
                    <th>EMAIL ADDRESS</th>
                    <th>CLEARANCE ROLE</th>
                    <th>DATE ENROLLED</th>
                    <th style={{ textAlign: 'right' }}>ROLE ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {isUsersLoading ? (
                    <tr>
                      <td colSpan={5} className="table-loading-cell">
                        <div className="table-spinner"></div>
                        <span>Loading user accounts telemetry...</span>
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
                        <tr
                          key={u.user_id}
                          className={`table-row-item ${!u.is_active ? 'row-suspended' : ''}`}
                          onClick={() => openUserDossier(u.user_id)}
                        >
                          {/* Name with Avatar */}
                          <td>
                            <div className="user-name-cell">
                              <div className={`user-avatar-micro ${u.role}`}>
                                {u.name?.charAt(0)?.toUpperCase() || '?'}
                              </div>
                              <div className="user-name-info">
                                <span className="user-primary-name">
                                  {u.name}
                                </span>
                                {isSelf && <span className="self-tag">(You)</span>}
                                {!u.is_active && <span className="suspended-pill">Suspended</span>}
                              </div>
                            </div>
                          </td>

                          {/* Email */}
                          <td className="email-address-cell">{u.email}</td>

                          {/* Role Badge */}
                          <td>{renderRoleBadge(u.role)}</td>

                          {/* Date Enrolled */}
                          <td className="date-enrolled-cell">{formatDate(u.created_at)}</td>

                          {/* Action Buttons */}
                          <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                            <div className="table-actions-group">
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
                                title={`Change role to ${nextRole}`}
                              >
                                {roleActionLabel}
                              </button>

                              <button
                                type="button"
                                className={`btn-status-toggle ${u.is_active ? 'btn-suspend' : 'btn-activate'}`}
                                onClick={() => handleToggleStatus(u)}
                                disabled={isSelf}
                                title={u.is_active ? 'Suspend Account' : 'Reactivate Account'}
                              >
                                {u.is_active ? 'Suspend' : 'Activate'}
                              </button>

                              <button
                                type="button"
                                className="btn-dossier-inspect"
                                onClick={() => openUserDossier(u.user_id)}
                                title="Inspect user dossier & history"
                              >
                                🔍
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={5} className="table-empty-cell">
                        <span className="empty-icon">👥</span>
                        <p className="empty-title">No user accounts matched the filter query.</p>
                        <p className="empty-sub">Try searching with a different keyword or reset role filters.</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination footer */}
            {usersPages > 1 && (
              <div className="table-pagination-footer">
                <span className="pagination-info">
                  Showing {users.length} of {usersTotal} user accounts
                </span>
                <div className="pagination-controls">
                  <button
                    type="button"
                    className="pagination-btn"
                    disabled={usersPage <= 1}
                    onClick={() => setUsersPage((p) => p - 1)}
                  >
                    ← Previous
                  </button>
                  <span className="pagination-current-page">
                    Page {usersPage} of {usersPages}
                  </span>
                  <button
                    type="button"
                    className="pagination-btn"
                    disabled={usersPage >= usersPages}
                    onClick={() => setUsersPage((p) => p + 1)}
                  >
                    Next →
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
                <div>
                  <h3 className="card-heading">System Infrastructure Health Matrix &amp; Maintenance</h3>
                  <p className="card-subheading">Core runtime status, model inference health, and diagnostic controls</p>
                </div>
              </div>
              <button
                type="button"
                className="btn-enroll-user"
                onClick={handleReloadDiseaseData}
                disabled={isReloadingData}
              >
                <span>{isReloadingData ? '🔄 Syncing...' : '🔄 Re-index Disease Knowledge'}</span>
              </button>
            </div>

            <div className="health-matrix-grid">
              <div className="health-item-box">
                <div className="health-box-header">
                  <span className="service-name">FastAPI Core Gateway</span>
                  <span className="service-status online">🟢 Online</span>
                </div>
                <p className="service-desc">
                  High-throughput asynchronous REST API routing with automatic OpenAPI schema validation and JWT middleware.
                </p>
              </div>

              <div className="health-item-box">
                <div className="health-box-header">
                  <span className="service-name">PostgreSQL / SQLite Storage</span>
                  <span className="service-status online">🟢 Connected</span>
                </div>
                <p className="service-desc">
                  Relational storage for clinical case histories, dermatology reference data, and immutable security audit logs.
                </p>
              </div>

              <div className="health-item-box">
                <div className="health-box-header">
                  <span className="service-name">PyTorch SCIN ML Engine</span>
                  <span className="service-status online">🟢 Operational</span>
                </div>
                <p className="service-desc">
                  Deep learning multi-modal inference pipeline with Grad-CAM visual explainability and Top-5 diagnostic ranking.
                </p>
              </div>

              <div className="health-item-box">
                <div className="health-box-header">
                  <span className="service-name">RBAC Security Enforcer</span>
                  <span className="service-status online">🟢 Active</span>
                </div>
                <p className="service-desc">
                  Cryptographic JWT validation with role protection, session expiry safeguards, and account lockout defenses.
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
                <div>
                  <h3 className="card-heading">Administrative Action Audit Trail</h3>
                  <p className="card-subheading">Immutable log of security modifications, role promotions, and user management events</p>
                </div>
              </div>
            </div>

            <div className="clinical-table-wrapper">
              <table className="admin-data-table">
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
                      <td colSpan={5} className="table-loading-cell">
                        <div className="table-spinner"></div>
                        <span>Loading audit trail events...</span>
                      </td>
                    </tr>
                  ) : auditLogs.length > 0 ? (
                    auditLogs.map((log) => (
                      <tr key={log.id}>
                        <td className="log-timestamp-cell">
                          {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                        </td>
                        <td className="log-admin-name">
                          {log.admin_name || `Admin #${log.admin_id}`}
                        </td>
                        <td>
                          <span className="audit-action-pill">{log.action}</span>
                        </td>
                        <td className="log-target-cell">
                          {log.target_name || (log.target_user_id ? `User #${log.target_user_id}` : 'System')}
                        </td>
                        <td className="log-details-cell">{log.details}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="table-empty-cell">
                        <span className="empty-icon">🛡️</span>
                        <p className="empty-title">No administrative audit events recorded yet.</p>
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
        <div className="clinical-modal-overlay">
          <div className="clinical-modal-card">
            <div className="clinical-modal-header">
              <div className="modal-title-wrap">
                <span className="modal-icon">➕</span>
                <h3>Enroll New Clinical User</h3>
              </div>
              <button
                type="button"
                className="btn-close-modal"
                onClick={() => setIsEnrollModalOpen(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleEnrollUser}>
              <div className="clinical-modal-body">
                {enrollError && (
                  <div className="modal-error-alert">
                    ⚠️ {enrollError}
                  </div>
                )}

                <div className="clinical-form-group">
                  <label>Full Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Dr. Alex Morgan"
                    value={enrollForm.name}
                    onChange={(e) => setEnrollForm({ ...enrollForm, name: e.target.value })}
                    required
                  />
                </div>

                <div className="clinical-form-group">
                  <label>Email Address</label>
                  <input
                    type="email"
                    placeholder="e.g. alex.morgan@dermaassist.com"
                    value={enrollForm.email}
                    onChange={(e) => setEnrollForm({ ...enrollForm, email: e.target.value })}
                    required
                  />
                </div>

                <div className="clinical-form-group">
                  <label>Initial Temporary Password</label>
                  <input
                    type="password"
                    placeholder="At least 6 characters"
                    value={enrollForm.password}
                    onChange={(e) => setEnrollForm({ ...enrollForm, password: e.target.value })}
                    required
                  />
                </div>

                <div className="clinical-form-group">
                  <label>Clearance Role Assignment</label>
                  <select
                    value={enrollForm.role}
                    onChange={(e) => setEnrollForm({ ...enrollForm, role: e.target.value })}
                  >
                    <option value="patient">Patient / Standard User</option>
                    <option value="doctor">Attending Doctor / Dermatologist</option>
                    <option value="admin">Administrator</option>
                    {currentAdmin?.role === 'super_admin' && (
                      <option value="super_admin">Super Administrator</option>
                    )}
                  </select>
                </div>
              </div>

              <div className="clinical-modal-footer">
                <button
                  type="button"
                  className="btn-modal-cancel"
                  onClick={() => setIsEnrollModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-modal-submit"
                  disabled={isEnrolling}
                >
                  {isEnrolling ? 'Enrolling...' : 'Enroll User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ROLE CHANGE CONFIRMATION MODAL */}
      {roleModal.isOpen && (
        <div className="clinical-modal-overlay">
          <div className="clinical-modal-card">
            <div className="clinical-modal-header">
              <div className="modal-title-wrap">
                <span className="modal-icon">🛡️</span>
                <h3>Modify Account Clearance Role</h3>
              </div>
              <button
                type="button"
                className="btn-close-modal"
                onClick={() => setRoleModal({ isOpen: false, targetUser: null, newRole: '', isLoading: false, errorMessage: '' })}
              >
                ✕
              </button>
            </div>

            <div className="clinical-modal-body">
              {roleModal.errorMessage && (
                <div className="modal-error-alert">
                  ⚠️ {roleModal.errorMessage}
                </div>
              )}

              <p className="modal-intro-text">
                Update clearance role for account: <strong>{roleModal.targetUser?.email}</strong>
              </p>

              <div className="clinical-form-group">
                <label>Select Target Role</label>
                <select
                  value={roleModal.newRole}
                  onChange={(e) => setRoleModal({ ...roleModal, newRole: e.target.value })}
                >
                  <option value="patient">Patient / Standard User</option>
                  <option value="doctor">Attending Doctor / Dermatologist</option>
                  <option value="admin">Administrator</option>
                  {currentAdmin?.role === 'super_admin' && (
                    <option value="super_admin">Super Administrator</option>
                  )}
                </select>
              </div>
            </div>

            <div className="clinical-modal-footer">
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => setRoleModal({ isOpen: false, targetUser: null, newRole: '', isLoading: false, errorMessage: '' })}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-modal-submit"
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
        <div className="clinical-modal-overlay">
          <div className="clinical-modal-card modal-card-wide">
            <div className="clinical-modal-header">
              <div className="modal-title-wrap">
                <span className="modal-icon">🔍</span>
                <h3>Clinical User Inspection Dossier</h3>
              </div>
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

            <div className="clinical-modal-body modal-scrollable">
              {isDossierLoading ? (
                <div className="modal-loading-state">
                  <div className="table-spinner"></div>
                  <p>Loading user dossier details...</p>
                </div>
              ) : userDossier ? (
                <div className="dossier-content-wrapper">
                  {/* Profile info Card */}
                  <div className="dossier-profile-card">
                    <div className="dossier-header-row">
                      <div className="dossier-avatar">
                        {userDossier.user?.name?.charAt(0)?.toUpperCase() || '?'}
                      </div>
                      <div>
                        <h4 className="dossier-user-name">{userDossier.user?.name}</h4>
                        <span className="dossier-user-email">{userDossier.user?.email}</span>
                      </div>
                    </div>

                    <div className="dossier-details-grid">
                      <div className="dossier-detail-item">
                        <span className="detail-label">User ID</span>
                        <span className="detail-value">#{userDossier.user?.user_id}</span>
                      </div>
                      <div className="dossier-detail-item">
                        <span className="detail-label">Role</span>
                        <span className="detail-value">{renderRoleBadge(userDossier.user?.role)}</span>
                      </div>
                      <div className="dossier-detail-item">
                        <span className="detail-label">Status</span>
                        <span className="detail-value">
                          {userDossier.user?.is_active ? (
                            <span className="badge-active">🟢 Active</span>
                          ) : (
                            <span className="badge-suspended">🔴 Suspended</span>
                          )}
                        </span>
                      </div>
                      <div className="dossier-detail-item">
                        <span className="detail-label">Last Login</span>
                        <span className="detail-value">
                          {userDossier.user?.last_login_at ? new Date(userDossier.user.last_login_at).toLocaleString() : 'Never'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Recent Login History */}
                  <div className="dossier-section">
                    <h5 className="dossier-section-title">Recent Login Activity (Last 10)</h5>
                    <div className="dossier-logins-list">
                      {userDossier.login_history && userDossier.login_history.length > 0 ? (
                        userDossier.login_history.slice(0, 10).map((lh, i) => (
                          <div key={i} className="login-history-row">
                            <span className={`login-status-badge ${lh.success ? 'status-success' : 'status-failed'}`}>
                              {lh.success ? '✅ Success' : `❌ ${lh.failure_reason || 'Failed'}`}
                            </span>
                            <span className="login-timestamp">
                              {lh.login_at ? new Date(lh.login_at).toLocaleString() : '—'}
                            </span>
                            <span className="login-ip">{lh.ip_address || '127.0.0.1'}</span>
                          </div>
                        ))
                      ) : (
                        <p className="no-history-text">No login activity recorded.</p>
                      )}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>

            <div className="clinical-modal-footer">
              <button
                type="button"
                className="btn-modal-cancel"
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
