import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { historyAPI, remindersAPI } from '../api/api';
import './DashboardPage.css';

export default function DashboardPage() {
  const { user } = useAuth();
  const [recentCases, setRecentCases] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [totalAnalyses, setTotalAnalyses] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [histRes, remRes] = await Promise.allSettled([
        historyAPI.getAll(5, 0),
        remindersAPI.getAll(),
      ]);
      if (histRes.status === 'fulfilled') {
        setRecentCases(histRes.value.data.cases || []);
        setTotalAnalyses(histRes.value.data.total || 0);
      }
      if (remRes.status === 'fulfilled') {
        setReminders(remRes.value.data.reminders || []);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDismissReminder = async (id) => {
    try {
      await remindersAPI.dismiss(id);
      setReminders((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      console.error('Failed to dismiss reminder:', err);
    }
  };

  const handleCompleteReminder = async (id) => {
    try {
      await remindersAPI.complete(id);
      setReminders((prev) => prev.map((r) => r.id === id ? { ...r, status: 'completed' } : r));
    } catch (err) {
      console.error('Failed to complete reminder:', err);
    }
  };

  return (
    <div className="page container">
      {/* Welcome Section */}
      <div className="dashboard-welcome animate-fade-in">
        <div className="welcome-content">
          <h1 className="welcome-title">
            Welcome back, <span className="accent">{user?.name || 'Practitioner'}</span>
          </h1>
          <p className="welcome-subtitle">
            AI-powered dermatological lesion screening &amp; decision support
          </p>
        </div>
        <Link to="/analyze" className="btn btn-primary btn-lg analyze-cta">
          <span>🔬</span>
          Analyze New Skin Image
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-3 dashboard-stats animate-fade-in stagger-1">
        <div className="card stat-card">
          <div className="stat-value">{totalAnalyses}</div>
          <div className="stat-label">Total Analyses</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">
            {recentCases.length > 0
              ? Math.round((recentCases[0]?.confidence || 0) * 100) + '%'
              : '—'}
          </div>
          <div className="stat-label">Last Confidence</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">
            {recentCases.length > 0
              ? recentCases[0]?.predicted_disease || '—'
              : '—'}
          </div>
          <div className="stat-label">Last Prediction</div>
        </div>
      </div>

      {/* Clinical Follow-up Reminders Section */}
      {reminders.filter(r => r.status !== 'dismissed').length > 0 && (
        <div className="dashboard-reminders animate-fade-in stagger-2" style={{ marginBottom: '2rem' }}>
          <div className="section-header" style={{ marginBottom: '1rem' }}>
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.2rem', margin: 0 }}>
              <span>🔔</span>
              Clinical Follow-Up &amp; Re-Scan Reminders ({reminders.filter(r => r.status !== 'dismissed').length})
            </h2>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Severity-calibrated lesion monitoring intervals
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {reminders.filter(r => r.status !== 'dismissed').slice(0, 4).map((rem) => {
              const isDue = new Date(rem.scheduled_for) <= new Date();
              const isMalignant = rem.severity_tier === 'malignant';
              const isPrecancerous = rem.severity_tier === 'precancerous';

              return (
                <div
                  key={rem.id}
                  className="card"
                  style={{
                    padding: '1.25rem',
                    borderLeft: `4px solid ${isMalignant ? '#ef4444' : isPrecancerous ? '#f59e0b' : '#0d9488'}`,
                    background: rem.status === 'completed' ? '#f8fafc' : '#ffffff',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                    <span className={`badge ${isMalignant ? 'badge-danger' : isPrecancerous ? 'badge-warning' : 'badge-success'}`}>
                      {rem.severity_tier.replace('_', ' ').toUpperCase()}
                    </span>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: isDue ? '#dc2626' : '#64748b' }}>
                      {isDue ? '⚠️ Due Now' : `Due: ${new Date(rem.scheduled_for).toLocaleDateString()}`}
                    </span>
                  </div>

                  <h3 style={{ fontSize: '1.05rem', margin: '0 0 4px 0', color: 'var(--text-primary)' }}>
                    Case #{rem.case_id} — {rem.predicted_disease || 'Lesion Re-check'}
                  </h3>

                  <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '0 0 1rem 0' }}>
                    {rem.notes || 'Follow-up lesion re-scan recommended.'}
                  </p>

                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                    {rem.status !== 'completed' && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                        onClick={() => handleDismissReminder(rem.id)}
                      >
                        Dismiss
                      </button>
                    )}
                    {rem.status !== 'completed' ? (
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                        onClick={() => handleCompleteReminder(rem.id)}
                      >
                        ✓ Mark Done
                      </button>
                    ) : (
                      <span style={{ fontSize: '0.75rem', color: '#166534', fontWeight: 700 }}>
                        ✓ Completed
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Recent Cases Section */}
      <div className="dashboard-recent animate-fade-in stagger-3">
        <div className="section-header">
          <h2>Recent Analyses</h2>
          {totalAnalyses > 0 && (
            <Link to="/history" className="btn btn-secondary btn-sm">
              View All History →
            </Link>
          )}
        </div>

        {/* Boxed Table Card Container */}
        <div className="dashboard-table-card">
          {loading ? (
            <div className="loading-overlay" style={{ padding: '3rem 1.5rem' }}>
              <div className="spinner"></div>
              <p className="loading-text">Loading clinical history...</p>
            </div>
          ) : recentCases.length === 0 ? (
            <div className="empty-table-state">
              <div className="empty-icon">🔬</div>
              <h3 className="empty-title">No analyses recorded yet</h3>
              <p className="empty-text">Upload your first skin lesion image to begin AI screening</p>
              <Link to="/analyze" className="btn btn-primary btn-sm">
                Start First Analysis
              </Link>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="clinical-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Predicted Disease</th>
                    <th>Confidence</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {recentCases.map((c) => (
                    <tr key={c.case_id}>
                      <td className="table-date-cell">
                        {new Date(c.created_at).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </td>
                      <td className="table-disease-cell">
                        <strong>{c.predicted_disease || 'Unknown Condition'}</strong>
                      </td>
                      <td>
                        <div className="confidence-cell">
                          <div className="confidence-mini-bar">
                            <div
                              className="confidence-mini-fill"
                              style={{ width: `${Math.min((c.confidence || 0) * 100, 100)}%` }}
                            ></div>
                          </div>
                          <span>{Math.round((c.confidence || 0) * 100)}%</span>
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${c.is_low_confidence ? 'badge-warning' : 'badge-success'}`}>
                          {c.is_low_confidence ? 'Review Advised' : 'Complete'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <Link to={`/history/${c.case_id}`} className="btn btn-secondary btn-sm table-action-btn">
                          View Report →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
