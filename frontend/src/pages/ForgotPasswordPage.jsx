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
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    setIsLoading(true);
    try {
      await authAPI.forgotPassword(cleanEmail);
      setIsSubmitted(true);
    } catch (err) {
      // Even on network error, keep message enumeration-safe if possible
      const serverMsg = err.response?.data?.detail;
      setErrorMessage(serverMsg || 'An error occurred while requesting password reset. Please try again.');
    } finally {
      setIsLoading(false);
    }
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
            /* Enumeration-safe confirmation state */
            <div className="forgot-success-card animate-fade-in">
              <div className="forgot-success-icon">📬</div>
              <h3 className="forgot-success-title">Check Your Inbox</h3>
              <p className="forgot-success-desc">
                If an account exists for <strong>{email}</strong>, a password reset link has been dispatched to your inbox.
              </p>
              <div className="forgot-instructions-box">
                <p>• The reset link will expire in <strong>60 minutes</strong>.</p>
                <p>• Check your spam or junk folder if you do not see it shortly.</p>
              </div>

              <div className="forgot-actions-group">
                <button
                  type="button"
                  onClick={() => {
                    setIsSubmitted(false);
                    setEmail('');
                  }}
                  className="btn btn-secondary btn-md"
                  style={{ width: '100%' }}
                >
                  Send to Another Email
                </button>
                <Link to="/login" className="btn btn-primary btn-md" style={{ width: '100%', textAlign: 'center' }}>
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
