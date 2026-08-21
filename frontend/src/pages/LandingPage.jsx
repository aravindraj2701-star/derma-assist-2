import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Disclaimer from '../components/Disclaimer';
import './LandingPage.css';

export default function LandingPage() {
  const { isAuthenticated } = useAuth();

  // If already authenticated, redirect away from public landing page to dashboard
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="landing-page">
      {/* Top Clinical Header Bar */}
      <header className="landing-nav">
        <div className="container landing-nav-inner">
          <div className="landing-brand">
            <span className="brand-icon">🩺</span>
            <span className="brand-title">Derma<span className="brand-accent">Assist</span></span>
          </div>
          <div className="landing-nav-actions">
            <Link to="/login?mode=signin" className="btn btn-secondary btn-sm">
              Sign In
            </Link>
            <Link to="/login?mode=signup" className="btn btn-primary btn-sm">
              Create Account
            </Link>
          </div>
        </div>
      </header>

      {/* Main Hero Section */}
      <main className="landing-main container">
        <section className="landing-hero animate-fade-in">
          <div className="hero-pill">
            <span className="hero-pill-dot"></span>
            Clinical Decision Support System
          </div>
          <h1 className="hero-headline">
            AI-Assisted Dermatological Lesion Screening &amp; Pathology Mapping
          </h1>
          <p className="hero-mission">
            Empowering healthcare providers and individuals with rapid, evidence-aligned skin condition analysis, 
            explainable AI heatmaps, and canonical reference image comparisons.
          </p>

          <div className="hero-trust-bar">
            <div className="trust-item">
              <span className="trust-icon">🔬</span>
              <div>
                <strong>Trained on Real Dermatology Imaging Data</strong>
                <p>Validated on thousands of clinically verified histopathology records</p>
              </div>
            </div>
            <div className="trust-item">
              <span className="trust-icon">🎯</span>
              <div>
                <strong>Multi-Class Lesion Classification</strong>
                <p>Melanocytic, Carcinomatous, Keratotic, and Benign cutaneous lesions</p>
              </div>
            </div>
            <div className="trust-item">
              <span className="trust-icon">🛡️</span>
              <div>
                <strong>Clinical Guardrails &amp; Grad-CAM</strong>
                <p>Visual attention maps and conflict detection for transparent screening</p>
              </div>
            </div>
          </div>
        </section>

        {/* 3-Step How It Works Section */}
        <section className="landing-steps animate-fade-in stagger-1">
          <div className="section-heading-center">
            <h2 className="section-title">How DermaAssist Operates</h2>
            <p className="section-subtitle">
              A structured, three-step clinical screening workflow designed for precision and clarity.
            </p>
          </div>

          <div className="steps-grid">
            <div className="step-card">
              <div className="step-number">01</div>
              <div className="step-icon">📷</div>
              <h3 className="step-title">Clinical Imaging Upload</h3>
              <p className="step-desc">
                Submit a standardized photograph of the skin lesion along with patient-reported anatomical location, duration, and symptom manifestations.
              </p>
            </div>

            <div className="step-card">
              <div className="step-number">02</div>
              <div className="step-icon">🧠</div>
              <h3 className="step-title">Dual-Pathway AI Matching</h3>
              <p className="step-desc">
                Deep neural network classifies visual dermatoscopic patterns while TF-IDF symptom alignment verifies morphological consistency with disease profiles.
              </p>
            </div>

            <div className="step-card">
              <div className="step-number">03</div>
              <div className="step-icon">📋</div>
              <h3 className="step-title">Evidence &amp; Reference Report</h3>
              <p className="step-desc">
                Review side-by-side matches against real training dataset examples, Grad-CAM attention overlays, differential diagnoses, and download a clinical PDF summary.
              </p>
            </div>
          </div>
        </section>

        {/* Trust & Dataset Verification Section */}
        <section className="landing-trust-section animate-fade-in stagger-2">
          <div className="trust-card">
            <div className="trust-card-header">
              <span className="trust-badge">Database &amp; Dataset Transparency</span>
              <h3 className="trust-card-title">Real Pathology Images with Verified Ground Truth</h3>
            </div>
            <p className="trust-card-body">
              Every prediction is correlated with reference samples from the international ISIC and dermatology archives. 
              Our integrated dataset explorer lets authorized users inspect reference pathology examples, symptom descriptions, 
              and severity classifications directly.
            </p>
            <div className="trust-stats-row">
              <div className="stat-box">
                <span className="stat-num">3,800+</span>
                <span className="stat-label">Reference Images</span>
              </div>
              <div className="stat-box">
                <span className="stat-num">9 Classes</span>
                <span className="stat-label">Covered Conditions</span>
              </div>
              <div className="stat-box">
                <span className="stat-num">100%</span>
                <span className="stat-label">Explainable Outputs</span>
              </div>
            </div>
          </div>
        </section>

        {/* Bottom Authentication Entry Points (Buttons only, No forms) */}
        <section className="landing-cta animate-fade-in stagger-3">
          <div className="cta-box">
            <h2 className="cta-heading">Ready to Begin Screening?</h2>
            <p className="cta-sub">
              Access the clinical decision support console, explore reference dataset imaging, or initiate a new lesion analysis.
            </p>
            <div className="cta-buttons">
              <Link to="/login?mode=signin" className="btn btn-secondary btn-lg cta-btn">
                Sign In to Console
              </Link>
              <Link to="/login?mode=signup" className="btn btn-primary btn-lg cta-btn">
                Create Account
              </Link>
            </div>
          </div>
        </section>

        {/* Disclaimer Footer */}
        <footer className="landing-footer">
          <Disclaimer />
          <p className="footer-copyright">
            © {new Date().getFullYear()} DermaAssist Clinical Systems. Screening support tool for healthcare and educational workflows.
          </p>
        </footer>
      </main>
    </div>
  );
}
