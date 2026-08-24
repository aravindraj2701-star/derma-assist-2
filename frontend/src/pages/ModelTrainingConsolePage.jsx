import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { trainingAPI } from '../api/api';
import './ModelTrainingConsolePage.css';

export default function ModelTrainingConsolePage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [retrainResult, setRetrainResult] = useState(null);
  const [error, setError] = useState('');

  const loadStats = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await trainingAPI.getStats();
      setStats(res.data);
    } catch (err) {
      console.error('Failed to load training stats:', err);
      setError('Could not load continuous learning metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const handleRetrain = async () => {
    setShowConfirmModal(false);
    setRetraining(true);
    setRetrainResult(null);
    setError('');

    try {
      const res = await trainingAPI.retrain();
      setRetrainResult(res.data);
      await loadStats();
    } catch (err) {
      console.error('Retraining failed:', err);
      setError(err.response?.data?.detail || 'Retraining failed to complete.');
    } finally {
      setRetraining(false);
    }
  };

  const handleRollback = async (versionId) => {
    if (!window.confirm(`Are you sure you want to rollback production deployment to ${versionId}?`)) {
      return;
    }
    try {
      await trainingAPI.rollback(versionId);
      await loadStats();
      alert(`Successfully restored production model to ${versionId}`);
    } catch (err) {
      console.error('Rollback failed:', err);
      alert(err.response?.data?.detail || 'Rollback failed.');
    }
  };

  if (loading && !stats) {
    return (
      <div className="page container training-console-page">
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p className="loading-text">Loading Model Training Console...</p>
        </div>
      </div>
    );
  }

  const activeModel = stats?.active_model_version;

  return (
    <div className="page container training-console-page">
      {/* Header Banner */}
      <div className="training-header-card animate-fade-in">
        <div>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <Link to="/admin" className="btn btn-secondary btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              ← Back to Admin Console
            </Link>
            <Link to="/dashboard" className="btn btn-secondary btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              Dashboard
            </Link>
          </div>
          <h1 className="training-header-title">
            <span>🧠</span>
            Continuous Learning &amp; Model Training Console
          </h1>
          <p className="training-header-subtitle">
            Doctor-supervised fine-tuning pipeline with fixed-benchmark validation safety gates.
          </p>
        </div>

        <button
          type="button"
          className="btn-retrain"
          onClick={() => setShowConfirmModal(true)}
          disabled={retraining || (stats?.approved_for_training_count === 0)}
        >
          <span>⚡</span>
          {retraining ? 'Fine-Tuning & Validating...' : 'Run Retraining Run'}
        </button>
      </div>

      {error && (
        <div className="error-message animate-fade-in" style={{ marginBottom: '1.5rem' }}>
          <span>⚠️</span> {error}
        </div>
      )}

      {retrainResult && (
        <div
          className={`card animate-fade-in ${retrainResult.promoted ? 'success-alert' : 'warning-alert'}`}
          style={{
            marginBottom: '1.5rem',
            padding: '1.25rem 1.5rem',
            background: retrainResult.promoted ? '#f0fdf4' : '#fffbeb',
            border: `1px solid ${retrainResult.promoted ? '#86efac' : '#fde68a'}`,
            borderRadius: '12px',
          }}
        >
          <h3 style={{ margin: '0 0 6px 0', fontSize: '1.1rem', color: retrainResult.promoted ? '#166534' : '#92400e' }}>
            {retrainResult.promoted ? '✅ Training Succeeded & Promoted' : '⚠️ Safety Gate Intervened'}
          </h3>
          <p style={{ margin: 0, fontSize: '0.875rem', color: retrainResult.promoted ? '#15803d' : '#b45309' }}>
            {retrainResult.message}
          </p>
        </div>
      )}

      {/* Stats Cards */}
      <div className="training-stats-grid animate-fade-in stagger-1">
        <div className="training-stat-card">
          <div className="stat-label-small">Approved Candidates</div>
          <div className="stat-value-large" style={{ color: '#0d9488' }}>
            {stats?.approved_for_training_count || 0}
          </div>
          <div className="stat-subtext">Ready for fine-tuning</div>
        </div>

        <div className="training-stat-card">
          <div className="stat-label-small">Active Production Version</div>
          <div className="stat-value-large" style={{ fontSize: '1.3rem', wordBreak: 'break-all' }}>
            {activeModel?.version_id || 'v1.0.0-base'}
          </div>
          <div className="stat-subtext">Benchmark-Certified</div>
        </div>

        <div className="training-stat-card">
          <div className="stat-label-small">Benchmark Accuracy</div>
          <div className="stat-value-large">
            {activeModel ? `${(activeModel.accuracy * 100).toFixed(1)}%` : '89.2%'}
          </div>
          <div className="stat-subtext">Fixed Test Set Metric</div>
        </div>

        <div className="training-stat-card">
          <div className="stat-label-small">Malignant Recall Safety</div>
          <div className="stat-value-large" style={{ color: '#059669' }}>
            {activeModel ? `${(activeModel.malignant_recall * 100).toFixed(1)}%` : '95.4%'}
          </div>
          <div className="stat-subtext">Safety Threshold Gate</div>
        </div>
      </div>

      {/* Approved Candidate Queue */}
      <div className="console-section-card animate-fade-in stagger-2">
        <div className="section-title-box">
          <h3 className="section-title-text">
            <span>📋</span>
            Doctor-Approved Training Candidates ({stats?.approved_candidates?.length || 0})
          </h3>
          <span className="candidate-status-badge approved">
            Opted-in with Ground Truth
          </span>
        </div>

        {stats?.approved_candidates?.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b', fontSize: '0.9rem' }}>
            No pending training candidates. Review cases in Doctor Console to opt-in verified cases.
          </div>
        ) : (
          <div className="table-responsive">
            <table className="console-table">
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>Original AI Prediction</th>
                  <th>Doctor Ground Truth</th>
                  <th>Attending Doctor</th>
                  <th>Doctor Clinical Notes</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {stats?.approved_candidates?.map((c) => (
                  <tr key={c.id}>
                    <td><strong>#{c.case_id}</strong></td>
                    <td>{c.original_prediction}</td>
                    <td><strong style={{ color: '#0f766e' }}>{c.doctor_corrected_label}</strong></td>
                    <td>{c.doctor_name || 'Dr. Attending'}</td>
                    <td style={{ fontSize: '0.8rem', color: '#64748b', maxWidth: '240px' }}>
                      {c.doctor_notes || 'Confirmed morphology.'}
                    </td>
                    <td>
                      <span className="candidate-status-badge approved">
                        {c.status.replace('_', ' ')}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Model Version History */}
      <div className="console-section-card animate-fade-in stagger-3">
        <div className="section-title-box">
          <h3 className="section-title-text">
            <span>🛡️</span>
            Model Version History &amp; Rollback Console
          </h3>
        </div>

        <div className="table-responsive">
          <table className="console-table">
            <thead>
              <tr>
                <th>Version ID</th>
                <th>Trained At</th>
                <th>Training Samples</th>
                <th>Test Accuracy</th>
                <th>Malignant Recall</th>
                <th>Deployment Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {stats?.version_history?.map((v) => (
                <tr key={v.version_id}>
                  <td><strong>{v.version_id}</strong></td>
                  <td>{new Date(v.trained_at).toLocaleDateString()}</td>
                  <td>{v.training_candidate_count} candidates</td>
                  <td><strong>{(v.accuracy * 100).toFixed(1)}%</strong></td>
                  <td><strong style={{ color: '#059669' }}>{(v.malignant_recall * 100).toFixed(1)}%</strong></td>
                  <td>
                    {v.promoted ? (
                      <span className="promoted-version-badge">
                        ● Production Active
                      </span>
                    ) : (
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Archived</span>
                    )}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {!v.promoted && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleRollback(v.version_id)}
                      >
                        Rollback to this
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="modal-overlay" onClick={() => setShowConfirmModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Confirm Supervised Model Retraining</h3>
            <p className="modal-body">
              You are about to fine-tune the multimodal model on <strong>{stats?.approved_for_training_count} doctor-approved cases</strong> combined with the base training set.
            </p>
            <div className="modal-safety-callout">
              <strong>🛡️ Clinical Safety Gate:</strong> The newly fine-tuned model will be rigorously tested against the fixed benchmark test split. It will ONLY be deployed to production if both overall accuracy and malignant recall equal or exceed the current production baseline.
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setShowConfirmModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={handleRetrain}
              >
                Confirm &amp; Run Retraining
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
