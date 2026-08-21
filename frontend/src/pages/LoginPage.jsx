import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { GoogleLogin, GoogleOAuthProvider } from '@react-oauth/google';
import { useAuth } from '../context/AuthContext';
import Disclaimer from '../components/Disclaimer';
import './LoginPage.css';

export default function LoginPage() {
  const { login, register, googleLogin, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Mode: 'signin' or 'signup'
  const initialMode = searchParams.get('mode') === 'signup' ? 'signup' : 'signin';
  const [mode, setMode] = useState(initialMode);

  useEffect(() => {
    const urlMode = searchParams.get('mode');
    if (urlMode === 'signup' || urlMode === 'signin') {
      setMode(urlMode);
    }
  }, [searchParams]);

  // Form states
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [selectedRole, setSelectedRole] = useState('patient');
  const [showPassword, setShowPassword] = useState(false);

  // Status states
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // If already logged in, redirect
  if (isAuthenticated) {
    navigate('/dashboard', { replace: true });
    return null;
  }

  const switchMode = (newMode) => {
    setMode(newMode);
    setErrorMessage('');
  };

  const handleSignIn = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    if (!email.trim() || !password) {
      setErrorMessage('Please enter both email and password.');
      return;
    }

    setIsLoading(true);
    const result = await login(email.trim(), password);
    setIsLoading(false);

    if (result.success) {
      if (result.user?.role === 'admin') {
        navigate('/admin');
      } else {
        navigate('/dashboard');
      }
    } else {
      setErrorMessage(result.error || 'Failed to sign in. Please check your credentials.');
    }
  };

  const handleQuickAdminLogin = async () => {
    setEmail('testadmin@dermaassist.local');
    setPassword('adminPass123');
    setErrorMessage('');
    setIsLoading(true);

    let result = await login('testadmin@dermaassist.local', 'adminPass123');
    if (!result.success) {
      // Auto-register test admin if not created yet
      result = await register('System Administrator', 'testadmin@dermaassist.local', 'adminPass123', 'admin');
    }
    setIsLoading(false);

    if (result.success) {
      navigate('/admin');
    } else {
      setErrorMessage(result.error || 'Failed to sign in as Administrator.');
    }
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    if (!name.trim()) {
      setErrorMessage('Please enter your full name.');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }
    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    const result = await register(name.trim(), email.trim(), password, selectedRole);
    setIsLoading(false);

    if (result.success) {
      if (result.user?.role === 'admin' || selectedRole === 'admin') {
        navigate('/admin');
      } else {
        navigate('/dashboard');
      }
    } else {
      setErrorMessage(result.error || 'Failed to create account. Please try again.');
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    setErrorMessage('');
    setIsLoading(true);
    const result = await googleLogin(credentialResponse.credential);
    setIsLoading(false);

    if (result.success) {
      if (result.user?.role === 'admin') {
        navigate('/admin');
      } else {
        navigate('/dashboard');
      }
    } else {
      setErrorMessage(result.error || 'Google sign-in failed.');
    }
  };

  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  return (
    <div className="login-page">
      <div className="login-bg-shapes">
        <div className="shape shape-1"></div>
        <div className="shape shape-2"></div>
        <div className="shape shape-3"></div>
      </div>

      <div className="login-container animate-fade-in">
        <div className="login-card">
          <Link to="/" className="login-back-link" style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.4rem',
            fontSize: '0.85rem',
            color: 'var(--text-muted)',
            textDecoration: 'none',
            marginBottom: '1rem',
            fontWeight: 500
          }}>
            ← Back to Overview
          </Link>

          {/* Header */}
          <div className="login-header">
            <div className="login-logo">🩺</div>
            <h1 className="login-title">
              Derma<span className="accent">Assist</span>
            </h1>
            <p className="login-subtitle">
              AI-Powered Skin Disease Detection &amp;<br />
              Clinical Decision Support System
            </p>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="auth-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'signin'}
              className={`auth-tab ${mode === 'signin' ? 'active' : ''}`}
              onClick={() => switchMode('signin')}
            >
              Sign In
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'signup'}
              className={`auth-tab ${mode === 'signup' ? 'active' : ''}`}
              onClick={() => switchMode('signup')}
            >
              Create Account
            </button>
          </div>

          {/* Reset Password Success Alert */}
          {searchParams.get('reset') === 'success' && (
            <div className="auth-success-alert animate-fade-in">
              <span>✅</span>
              <span>Your password has been successfully reset! You may now sign in with your new password.</span>
            </div>
          )}

          {/* Error Alert */}
          {errorMessage && (
            <div className="auth-error-alert animate-shake">
              <span className="error-icon">⚠️</span>
              <span className="error-text">{errorMessage}</span>
            </div>
          )}

          {/* Quick Admin Demo Button */}
          {mode === 'signin' && (
            <div style={{ marginBottom: '1.25rem' }}>
              <button
                type="button"
                className="btn-quick-admin"
                onClick={handleQuickAdminLogin}
                disabled={isLoading}
                title="Log in directly as Administrator to test Admin Console"
              >
                <span>🛡️</span> Sign In as System Admin (1-Click)
              </button>
            </div>
          )}

          {/* Sign In Form */}
          {mode === 'signin' ? (
            <form onSubmit={handleSignIn} className="auth-form" noValidate>
              <div className="form-group">
                <label className="form-label" htmlFor="signin-email">
                  Email Address
                </label>
                <div className="input-wrapper">
                  <span className="input-icon">✉️</span>
                  <input
                    id="signin-email"
                    type="email"
                    className="form-input with-icon"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="form-group">
                <div className="label-with-link">
                  <label className="form-label" htmlFor="signin-password">
                    Password
                  </label>
                  <Link to="/forgot-password" className="forgot-password-link">
                    Forgot Password?
                  </Link>
                </div>
                <div className="input-wrapper">
                  <span className="input-icon">🔒</span>
                  <input
                    id="signin-password"
                    type={showPassword ? 'text' : 'password'}
                    className="form-input with-icon with-action"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    required
                    disabled={isLoading}
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

              <button
                type="submit"
                className="btn btn-primary btn-lg auth-submit-btn"
                disabled={isLoading}
              >
                {isLoading ? (
                  <span className="spinner-inline"></span>
                ) : (
                  <>
                    <span>🚀</span>
                    Sign In
                  </>
                )}
              </button>
            </form>
          ) : (
            /* Sign Up / Create Account Form */
            <form onSubmit={handleSignUp} className="auth-form" noValidate>
              {/* Account Role Selector */}
              <div className="form-group">
                <label className="form-label">
                  Select Account Role
                </label>
                <div className="role-chips-group">
                  <button
                    type="button"
                    className={`role-chip-btn ${selectedRole === 'patient' ? 'active' : ''}`}
                    onClick={() => setSelectedRole('patient')}
                  >
                    <span className="chip-icon">👤</span>
                    <span className="chip-label">Patient</span>
                  </button>
                  <button
                    type="button"
                    className={`role-chip-btn ${selectedRole === 'doctor' ? 'active' : ''}`}
                    onClick={() => setSelectedRole('doctor')}
                  >
                    <span className="chip-icon">🩺</span>
                    <span className="chip-label">Doctor</span>
                  </button>
                  <button
                    type="button"
                    className={`role-chip-btn ${selectedRole === 'admin' ? 'active' : ''}`}
                    onClick={() => setSelectedRole('admin')}
                  >
                    <span className="chip-icon">🛡️</span>
                    <span className="chip-label">Admin</span>
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="signup-name">
                  Full Name
                </label>
                <div className="input-wrapper">
                  <span className="input-icon">👤</span>
                  <input
                    id="signup-name"
                    type="text"
                    className="form-input with-icon"
                    placeholder="Dr. Jane Doe / John Smith"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="name"
                    required
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="signup-email">
                  Email Address
                </label>
                <div className="input-wrapper">
                  <span className="input-icon">✉️</span>
                  <input
                    id="signup-email"
                    type="email"
                    className="form-input with-icon"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="signup-password">
                  Create Password
                </label>
                <div className="input-wrapper">
                  <span className="input-icon">🔒</span>
                  <input
                    id="signup-password"
                    type={showPassword ? 'text' : 'password'}
                    className="form-input with-icon with-action"
                    placeholder="At least 6 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                    required
                    disabled={isLoading}
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
                <label className="form-label" htmlFor="signup-confirm-password">
                  Confirm Password
                </label>
                <div className="input-wrapper">
                  <span className="input-icon">🔒</span>
                  <input
                    id="signup-confirm-password"
                    type={showPassword ? 'text' : 'password'}
                    className="form-input with-icon"
                    placeholder="Re-enter your password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    autoComplete="new-password"
                    required
                    disabled={isLoading}
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
                    <span>✨</span>
                    Create Account ({selectedRole.charAt(0).toUpperCase() + selectedRole.slice(1)})
                  </>
                )}
              </button>
            </form>
          )}

          {/* Optional Google Login (if configured) */}
          {googleClientId && (
            <div className="google-auth-section">
              <div className="auth-divider">
                <span>OR</span>
              </div>
              <GoogleOAuthProvider clientId={googleClientId}>
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => setErrorMessage('Google sign-in failed.')}
                  theme="filled_black"
                  size="large"
                  width="100%"
                  text="continue_with"
                />
              </GoogleOAuthProvider>
            </div>
          )}

          {/* Features highlight */}
          <div className="login-features">
            <div className="feature-item">
              <span className="feature-icon">🔬</span>
              <span>AI Image Analysis</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">📋</span>
              <span>Symptom Matching</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">🧠</span>
              <span>Smart Explanations</span>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="login-disclaimer">
            <Disclaimer />
          </div>
        </div>
      </div>
    </div>
  );
}
