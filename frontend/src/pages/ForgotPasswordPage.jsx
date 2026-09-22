import { useState } from 'react';
import { Link } from 'react-router-dom';
import { authAPI } from '../api/api';
import Disclaimer from '../components/Disclaimer';
import './LoginPage.css';
import './ForgotPasswordPage.css';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [resetLink, setResetLink] = useState('');
  const [copiedLink, setCopiedLink] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setResetLink('');
    setCopiedLink(false);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await authAPI.forgotPassword(cleanEmail);
      if (res.data?.reset_link) {
        setResetLink(res.data.reset_link);
      }
      setIsSubmitted(true);
    } catch (err) {
      const serverMsg = err.response?.data?.detail;
      setErrorMessage(serverMsg || 'An error occurred while requesting password reset. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyLink = () => {
    if (!resetLink) return;
    navigator.clipboard.writeText(resetLink);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 3000);
  };

  return (
    <div className="login-page-container">
      {/* Background Ambience */}
      <div className="login-bg-glow glow-1"></div>
      <div className="login-bg-glow glow-2"></div>

      <div className="login-content-wrapper">
        <div className="login-card animate-fade-in">
          {/* Back Navigation */}
          <Link to="/login" className="forgot-back-nav">
            ← Back to Sign In
          </Link>

          {/* Header */}
          <div className="login-header">
            <div className="login-logo">🔑</div>
            <h1 className="login-title">
              Reset Your <span className="accent">Password</span>
            </h1>
            <p className="login-subtitle">
              Enter your registered clinical account email to receive a secure password reset link.
            </p>
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <div className="auth-error-alert animate-shake">
              <span className="error-icon">⚠️</span>
              <span className="error-text">{errorMessage}</span>
            </div>
          )}

          {isSubmitted ? (
            /* Confirmation state with direct access link */
            <div className="forgot-success-card animate-fade-in">
              <div className="forgot-success-icon">📬</div>
              <h3 className="forgot-success-title">Password Reset Dispatched</h3>
              <p className="forgot-success-desc">
                A password reset authorization has been generated for <strong>{email}</strong>.
              </p>

              {resetLink && (
                <div style={{
                  background: '#f0fdfa',
                  border: '1px solid #5eead4',
                  borderRadius: '10px',
                  padding: '1rem',
                  margin: '1.25rem 0',
                  textAlign: 'left'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '1.1rem' }}>⚡</span>
                    <strong style={{ fontSize: '0.9rem', color: '#0f766e' }}>Direct Password Reset Access</strong>
                  </div>
                  <p style={{ fontSize: '0.82rem', color: '#134e4a', margin: '0 0 0.75rem' }}>
                    You can reset your password immediately using the generated link below:
                  </p>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <a
                      href={resetLink}
                      className="btn btn-primary btn-sm"
                      style={{ flex: 1, textAlign: 'center', textDecoration: 'none' }}
                    >
                      🚀 Reset Password Now &rarr;
                    </a>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={handleCopyLink}
                    >
                      {copiedLink ? '✓ Copied' : '📋 Copy Link'}
                    </button>
                  </div>
                </div>
              )}

              <div className="forgot-instructions-box">
                <p>• The reset link will expire in <strong>60 minutes</strong>.</p>
                <p>• If SMTP email server is configured, check your inbox or spam folder.</p>
              </div>

              <div className="forgot-actions-group">
                <button
                  type="button"
                  onClick={() => {
                    setIsSubmitted(false);
                    setEmail('');
                    setResetLink('');
                  }}
                  className="btn btn-secondary btn-md"
                  style={{ width: '100%' }}
                >
                  Send to Another Email
                </button>
                <Link to="/login" className="btn btn-outline btn-md" style={{ width: '100%', textAlign: 'center' }}>
                  Return to Sign In &rarr;
                </Link>
              </div>
            </div>
          ) : (
            /* Forgot Password Form */
            <form onSubmit={handleSubmit} className="auth-form" noValidate>
              <div className="form-group">
                <label className="form-label" htmlFor="forgot-email">
                  Registered Account Email
                </label>
                <div className="input-wrapper">
                  <span className="input-icon">✉️</span>
                  <input
                    id="forgot-email"
                    type="email"
                    className="form-input with-icon"
                    placeholder="doctor@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                    disabled={isLoading}
                    autoFocus
                  />
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-lg auth-submit-btn"
                disabled={isLoading}
              >
                {isLoading ? (
                  <span className="spinner-inline"></span>
                ) : (
                  <>
                    <span>📨</span>
                    Send Reset Link
                  </>
                )}
              </button>

              <div className="auth-footer-help">
                Remember your password?{' '}
                <Link to="/login" className="accent-link">
                  Sign In
                </Link>
              </div>
            </form>
          )}
        </div>

        <Disclaimer />
      </div>
    </div>
  );
}
