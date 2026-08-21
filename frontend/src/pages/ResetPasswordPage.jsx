import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { authAPI } from '../api/api';
import Disclaimer from '../components/Disclaimer';
import './LoginPage.css';
import './ResetPasswordPage.css';

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isTokenInvalid, setIsTokenInvalid] = useState(!token);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    if (!token) {
      setIsTokenInvalid(true);
      setErrorMessage('Missing password reset token. Please use the link provided in your email.');
      return;
    }

    if (newPassword.length < 6) {
      setErrorMessage('Password must be at least 6 characters.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage('Passwords do not match. Please ensure both fields match exactly.');
      return;
    }

    setIsLoading(true);
    try {
      await authAPI.resetPassword(token, newPassword);
      // Redirect to Login page with reset success indicator
      navigate('/login?reset=success');
    } catch (err) {
      const serverMsg = err.response?.data?.detail;
      if (err.response?.status === 400 || err.response?.status === 404) {
        setIsTokenInvalid(true);
      }
      setErrorMessage(
        serverMsg || 'Failed to reset password. The link may have expired or already been used.'
      );
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
          {/* Header */}
          <div className="login-header">
            <div className="login-logo">🔒</div>
            <h1 className="login-title">
              Create New <span className="accent">Password</span>
            </h1>
            <p className="login-subtitle">
              Enter and confirm your new secure password to restore access to your clinical account.
            </p>
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <div className="auth-error-alert animate-shake">
              <span className="error-icon">⚠️</span>
              <span className="error-text">{errorMessage}</span>
            </div>
          )}

          {/* Invalid / Expired Token Warning View */}
          {isTokenInvalid && !token ? (
            <div className="token-invalid-box animate-fade-in">
              <div className="token-invalid-icon">🚫</div>
              <h3 className="token-invalid-title">Invalid Reset Link</h3>
              <p className="token-invalid-desc">
                No password reset token was detected in your request URL. Please click the full link received in your email or request a new one below.
              </p>
              <Link to="/forgot-password" className="btn btn-primary btn-md" style={{ width: '100%', textAlign: 'center' }}>
                Request New Reset Link &rarr;
              </Link>
            </div>
          ) : isTokenInvalid && errorMessage ? (
            <div className="token-invalid-box animate-fade-in">
              <div className="token-invalid-icon">⌛</div>
              <h3 className="token-invalid-title">Reset Link Expired or Used</h3>
              <p className="token-invalid-desc">
                This password reset link has expired or has already been used. Password reset tokens are valid for one-time use within 60 minutes.
              </p>
              <Link to="/forgot-password" className="btn btn-primary btn-md" style={{ width: '100%', textAlign: 'center' }}>
                Request Fresh Reset Link &rarr;
              </Link>
            </div>
          ) : (
            /* Reset Password Form */
            <form onSubmit={handleSubmit} className="auth-form" noValidate>
              <div className="form-group">
                <label className="form-label" htmlFor="new-password">
                  New Password
                </label>
                <div className="input-wrapper">
                  <span className="input-icon">🔑</span>
                  <input
                    id="new-password"
                    type={showPassword ? 'text' : 'password'}
                    className="form-input with-icon with-action"
                    placeholder="At least 6 characters"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    autoComplete="new-password"
                    required
                    disabled={isLoading}
                    autoFocus
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    tabIndex={-1}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? '👁️' : '🙈'}
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="confirm-password">
                  Confirm New Password
                </label>
                <div className="input-wrapper">
                  <span className="input-icon">🔒</span>
                  <input
                    id="confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    className="form-input with-icon with-action"
                    placeholder="Re-enter your new password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    autoComplete="new-password"
                    required
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    tabIndex={-1}
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  >
                    {showConfirmPassword ? '👁️' : '🙈'}
                  </button>
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
                    <span>🛡️</span>
                    Save New Password &amp; Sign In
                  </>
                )}
              </button>

              <div className="auth-footer-help">
                <Link to="/login" className="accent-link">
                  ← Return to Sign In
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
