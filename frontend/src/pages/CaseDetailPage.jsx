import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { historyAPI, datasetAPI } from '../api/api';
import Disclaimer from '../components/Disclaimer';
import { formatScore, formatScoreValue } from '../utils/formatters';
import './CaseDetailPage.css';

export default function CaseDetailPage() {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState('');

  useEffect(() => {
    loadCase();
  }, [caseId]);

  const loadCase = async () => {
    try {
      const res = await historyAPI.getById(caseId);
      setCaseData(res.data);
    } catch (err) {
      setError('Case not found');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    setPdfError('');
    try {
      const blob = await historyAPI.downloadPdf(caseId);
      const url = window.URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `DermaAssist_Report_Case_${caseId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('PDF download failed:', err);
      setPdfError('Failed to generate PDF. Please try again.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  if (loading) {
    return (
      <div className="page container">
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p className="loading-text">Loading case...</p>
        </div>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="page container">
        <div className="empty-state card">
          <div className="empty-icon">❌</div>
          <h3>{error || 'Case Not Found'}</h3>
          <Link to="/history" className="btn btn-primary" style={{ marginTop: '1rem' }}>
            Back to History
          </Link>
        </div>
      </div>
    );
  }

  const refExample = caseData.reference_example;
  const disease = caseData.predicted_disease || 'Unknown';
  const isMalignant = disease.toLowerCase().includes('melanoma') || disease.toLowerCase().includes('carcinoma');
  const isPrecancerous = disease.toLowerCase().includes('actinic');
  const severity = isMalignant ? 'Malignant' : (isPrecancerous ? 'Pre-cancerous' : 'Benign');

  // Differentiating Features Clarification Table Data
  const rawPredictions = caseData.predictions || [];
  const primaryName = rawPredictions[0]?.disease_name || caseData.predicted_disease || 'Unknown';
  const symText = (caseData.symptoms_text || '').toLowerCase();

  const differentiatingFeatures = (caseData.differentiating_features && caseData.differentiating_features.length > 0)
    ? caseData.differentiating_features
    : rawPredictions.map((p, idx) => {
        const cond = p.disease_name || p.condition || p.disease || 'Unknown';
        const rank = p.rank || idx + 1;

        return {
          rank,
          disease: cond,
          condition: cond,
          key_distinguishing_feature:
            cond === 'Urticaria'
              ? 'Sudden onset of evanescent, intensely pruritic raised wheals (hives) that typically blanch with pressure and resolve or shift locations within hours.'
              : cond === 'Eczema'
              ? 'Chronic/relapsing, dry and scaly patches, typically in flexural areas with long-standing history.'
              : cond === 'Acute dermatitis, NOS'
              ? 'Non-specific inflammatory reaction, often recent exposure-triggered, flat/dry presentation.'
              : cond === 'Psoriasis'
              ? 'Well-demarcated silvery scaly plaques, typically chronic (months-years), symmetric distribution.'
              : cond === 'Irritant Contact Dermatitis'
              ? 'Localized to site of contact/exposure, dryness and flat texture common, resolves once irritant removed.'
              : cond === 'Allergic Contact Dermatitis'
              ? 'Type IV delayed hypersensitivity eruption with geometric or patterned vesicular erythema and intense pruritus.'
              : cond === 'Insect Bite'
              ? 'Acute grouped or discrete inflammatory papules or wheals with a central punctum on exposed sites with sudden onset.'
              : cond === 'Herpes Zoster'
              ? 'Painful, clustered umbilicated vesicles on an erythematous base strictly along a unilateral dermatomal distribution.'
              : `Characteristic morphological and timeline presentation consistent with ${cond}.`,
          overlaps_with:
            cond === 'Urticaria'
              ? 'Eczema, Acute Dermatitis'
              : cond === 'Eczema'
              ? 'Psoriasis, Irritant Contact Dermatitis'
              : cond === 'Acute dermatitis, NOS'
              ? 'Irritant Contact Dermatitis, Eczema'
              : cond === 'Psoriasis'
              ? 'Eczema'
              : cond === 'Irritant Contact Dermatitis'
              ? 'Acute Dermatitis, Eczema'
              : 'Related eczematous/inflammatory eruptions',
          confidence_vs_case:
            cond === 'Urticaria'
              ? (symText.includes('1 week') || symText.includes('day') || symText.includes('acute')
                  ? 'Short 1-week duration and rapid onset strongly favor Urticaria over chronic conditions.'
                  : 'Reported onset and intensely pruritic raised morphology align closely with urticaria.')
              : cond === 'Eczema'
              ? (symText.includes('1 week') || symText.includes('day') || symText.includes('ear') || symText.includes('scalp')
                  ? 'Scalp/dryness texture matches, but shorter duration argues against typical chronic eczema pattern.'
                  : 'Scaly erythematous morphology matches, but timeline balances with competing differentials.')
              : cond === 'Acute dermatitis, NOS'
              ? 'Flat/dry texture and short duration align, but lacks a clear specific trigger to confirm.'
              : cond === 'Psoriasis'
              ? (symText.includes('1 week') || symText.includes('day')
                  ? 'Duration of only 1 week is too short for typical psoriasis presentation, lowering confidence.'
                  : 'Plaque morphology differs from acute presentation, placing it lower than top match.')
              : cond === 'Irritant Contact Dermatitis'
              ? (symText.includes('ear')
                  ? 'Ear location and dryness/flat texture are consistent, but no reported exposure history reduces confidence.'
                  : 'Localized erythema is consistent, but lack of documented direct contact exposure limits score.')
              : `Clinical timeline and reported morphology provide secondary alignment relative to ${primaryName}.`,
          confidence_pct: p.confidence_pct || (p.combined_score ? Math.round(p.combined_score * 100) : 0),
        };
      });

  return (
    <div className="page container" style={{ paddingTop: 'var(--space-xl)', paddingBottom: 'var(--space-3xl)' }}>
      {/* Header */}
      <div className="page-header animate-fade-in" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <Link to="/history" className="btn btn-secondary btn-sm" style={{ marginBottom: '1rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
            ← Back to History
          </Link>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <span className={`badge ${caseData.is_low_confidence ? 'badge-warning' : 'badge-success'}`}>
              {caseData.is_low_confidence ? '⚠️ Low Confidence' : '✅ Screening Record'}
            </span>
            <span className={`badge ${isMalignant ? 'badge-danger' : isPrecancerous ? 'badge-warning' : 'badge-success'}`}>
              ● {severity.toUpperCase()}
            </span>
          </div>
          <h1 className="page-title">Case #{caseData.case_id}</h1>
          <p className="page-subtitle">
            Recorded on {new Date(caseData.created_at).toLocaleString()}
          </p>
        </div>

        <div>
          <button
            type="button"
            className="btn btn-primary btn-md"
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
          >
            {downloadingPdf ? 'Generating PDF...' : '📄 Download Clinical PDF Report'}
          </button>
        </div>
      </div>

      {pdfError && (
        <div className="error-message animate-fade-in" style={{ marginBottom: '1.5rem' }}>
          <span>⚠️</span> {pdfError}
        </div>
      )}

      {/* Top Prediction */}
      <div className="card animate-fade-in stagger-1" style={{ textAlign: 'center', marginBottom: 'var(--space-xl)', padding: '2rem' }}>
        <p style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: '0.5rem', fontWeight: 600 }}>
          Predicted Condition
        </p>
        <h2 style={{ fontSize: '2.2rem', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
          {caseData.predicted_disease || 'Unknown'}
        </h2>
        <p style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--accent-400)', marginTop: '0.25rem' }}>
          {Math.round((caseData.confidence || 0) * 100)}% Combined Confidence
        </p>
      </div>

      {/* Side-by-Side Lesion Comparison */}
      <div className="card animate-fade-in stagger-2" style={{ marginBottom: 'var(--space-xl)', padding: '2rem' }}>
        <h3 style={{ fontSize: '1.2rem', marginBottom: '1.25rem' }}>🖼️ Lesion Comparison</h3>

        <div className="grid grid-2" style={{ gap: '1.5rem', marginBottom: '1.5rem' }}>
          {/* Patient Image */}
          <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
            <div style={{ padding: '0.75rem 1rem', background: 'rgba(10,14,26,0.6)', borderBottom: '1px solid var(--border-default)', fontSize: '0.78rem', fontWeight: 700, color: 'var(--primary-300)', textTransform: 'uppercase' }}>
              👤 Patient Uploaded Lesion
            </div>
            <div style={{ height: '260px', background: '#0d1322', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {caseData.image_ref ? (
                <img
                  src={`data:image/png;base64,${caseData.image_ref}`}
                  alt="Patient lesion"
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
              ) : (
                <p style={{ color: 'var(--text-muted)' }}>Image Not Available</p>
              )}
            </div>
            <div style={{ padding: '0.75rem', fontSize: '0.8rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              Scan recorded for Case #{caseData.case_id}
            </div>
          </div>

          {/* Reference Image */}
          <div style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(20,184,166,0.3)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
            <div style={{ padding: '0.75rem 1rem', background: 'rgba(10,14,26,0.6)', borderBottom: '1px solid var(--border-default)', fontSize: '0.78rem', fontWeight: 700, color: 'var(--accent-400)', textTransform: 'uppercase' }}>
              📚 Reference example from training data
            </div>
            <div style={{ height: '260px', background: '#0d1322', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {refExample?.image_base64 ? (
                <img
                  src={`data:image/jpeg;base64,${refExample.image_base64}`}
                  alt="Reference lesion"
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
              ) : refExample?.image_path ? (
                <img
                  src={datasetAPI.getImageUrl(refExample.image_path)}
                  alt="Reference lesion"
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
              ) : (
                <p style={{ color: 'var(--text-muted)' }}>Canonical ISIC reference match</p>
              )}
            </div>
            <div style={{ padding: '0.75rem', fontSize: '0.8rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <strong>{refExample?.disease_name || disease}</strong> • {refExample?.source || 'ISIC Archive'}
            </div>
          </div>
        </div>

        {refExample?.symptoms_description && (
          <div style={{ background: 'rgba(20,184,166,0.05)', border: '1px solid rgba(20,184,166,0.2)', borderRadius: 'var(--radius-md)', padding: '1rem' }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--accent-400)', marginBottom: '0.35rem' }}>📖 Pathology Reference Morphology:</h4>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', margin: 0 }}>{refExample.symptoms_description}</p>
          </div>
        )}
      </div>

      {/* Predictions Breakdown Table */}
      {caseData.predictions?.length > 0 && (
        <div className="case-detail-table-card animate-fade-in stagger-2">
          <div className="case-section-header">
            <h3 className="case-card-title">
              <span>📊</span>
              <span>Differential Diagnoses Breakdown</span>
            </h3>
            <span className="primary-pill-tag">
              Symptom-First Triage
            </span>
          </div>
          <p className="case-card-intro">
            Ranked differential diagnoses evaluated against patient clinical findings and dermatoscopic image features:
          </p>

          <div className="case-table-responsive">
            <table className="case-breakdown-table">
              <thead>
                <tr>
                  <th style={{ width: '8%', textAlign: 'center' }}>Rank</th>
                  <th style={{ width: '32%', textAlign: 'left' }}>Disease</th>
                  <th style={{ width: '20%', textAlign: 'center' }}>Image Pattern</th>
                  <th style={{ width: '20%', textAlign: 'center' }}>Symptom Alignment</th>
                  <th style={{ width: '20%', textAlign: 'right' }}>Combined Confidence</th>
                </tr>
              </thead>
              <tbody>
                {caseData.predictions.map((p) => (
                  <tr key={p.prediction_id || p.rank} className={p.rank === 1 ? 'primary-case-row' : ''}>
                    <td style={{ textAlign: 'center' }}>
                      <span className={`diff-rank-badge ${p.rank === 1 ? 'rank-1' : ''}`}>
                        #{p.rank}
                      </span>
                    </td>
                    <td>
                      <div className="condition-cell-wrapper">
                        <strong className="condition-cell-title">{p.disease_name}</strong>
                        {p.rank === 1 && <span className="primary-pill-tag">Primary Match</span>}
                      </div>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span className="score-cell-pill vision-pill">
                        🖼️ {formatScore(p.image_score)}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span className="score-cell-pill symptom-pill">
                        📋 {formatScore(p.symptom_score)}
                      </span>
                    </td>
                    <td>
                      <div className="combined-cell-box">
                        <div className="confidence-mini-bar">
                          <div
                            className="confidence-mini-fill"
                            style={{ width: `${Math.min(formatScoreValue(p.combined_score || p.confidence_pct), 100)}%` }}
                          ></div>
                        </div>
                        <span className="combined-pct-text">
                          {formatScore(p.combined_score || p.confidence_pct)}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Differentiating Features Clarification Table */}
      {caseData.predictions?.length > 0 && (
        <div className="differentiating-case-card animate-fade-in stagger-3">
          <div className="case-section-header">
            <h3 className="case-card-title">
              <span>🔬</span>
              <span>Differentiating Features</span>
            </h3>
            <span className="clarification-badge">
              Clinical Comparison
            </span>
          </div>
          <p className="case-card-intro">
            Clinical distinction matrix explaining what separates these candidate diseases from each other and why they were compared for this specific case:
          </p>

          {/* Desktop Table View */}
          <div className="case-table-responsive desktop-differentiating-table">
            <table className="differentiating-table">
              <thead>
                <tr>
                  <th style={{ width: '22%' }}>Disease</th>
                  <th style={{ width: '30%' }}>Key Distinguishing Feature</th>
                  <th style={{ width: '24%' }}>Overlaps With</th>
                  <th style={{ width: '24%' }}>Confidence vs. This Case</th>
                </tr>
              </thead>
              <tbody>
                {differentiatingFeatures.map((item, index) => (
                  <tr key={index} className={item.rank === 1 ? 'primary-diff-row' : ''}>
                    <td>
                      <div className="diff-disease-header">
                        <span className={`diff-rank-badge ${item.rank === 1 ? 'rank-1' : ''}`}>
                          #{item.rank || index + 1}
                        </span>
                        <strong className="differentiating-disease-name">
                          {item.disease || item.condition}
                        </strong>
                      </div>
                      {item.rank === 1 && (
                        <span className="primary-pill-tag" style={{ marginTop: '0.35rem', display: 'inline-block' }}>
                          Top Match
                        </span>
                      )}
                    </td>
                    <td className="diff-feature-text">
                      {item.key_distinguishing_feature}
                    </td>
                    <td>
                      <span className="overlap-pill-text">{item.overlaps_with}</span>
                    </td>
                    <td>
                      <span className="case-reason-pill">{item.confidence_vs_case}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Stacked Cards */}
          <div className="mobile-differentiating-cards">
            {differentiatingFeatures.map((item, index) => (
              <div key={index} className={`mobile-diff-card ${item.rank === 1 ? 'primary-mobile-card' : ''}`}>
                <div className="mobile-diff-header">
                  <span className={`diff-rank-badge ${item.rank === 1 ? 'rank-1' : ''}`}>
                    #{item.rank || index + 1}
                  </span>
                  <strong className="mobile-diff-title">{item.disease || item.condition}</strong>
                  {item.rank === 1 && <span className="primary-pill-tag">Top Match</span>}
                </div>
                <div className="mobile-diff-row">
                  <span className="mobile-diff-label">Key Distinguishing Feature:</span>
                  <p className="mobile-diff-val">{item.key_distinguishing_feature}</p>
                </div>
                <div className="mobile-diff-row">
                  <span className="mobile-diff-label">Overlaps With:</span>
                  <p className="mobile-diff-val overlap-highlight">{item.overlaps_with}</p>
                </div>
                <div className="mobile-diff-row">
                  <span className="mobile-diff-label">Confidence vs. This Case:</span>
                  <p className="mobile-diff-val case-highlight">{item.confidence_vs_case}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grad-CAM & Symptoms */}
      <div className="grid grid-2 animate-fade-in stagger-3" style={{ marginBottom: 'var(--space-xl)' }}>
        {caseData.gradcam_image && (
          <div className="card">
            <h3 style={{ marginBottom: '1rem' }}>🔥 AI Attention (Grad-CAM)</h3>
            <img
              src={`data:image/png;base64,${caseData.gradcam_image}`}
              alt="Grad-CAM"
              style={{ width: '100%', borderRadius: '0.75rem', maxHeight: '300px', objectFit: 'contain', background: 'var(--bg-secondary)' }}
            />
          </div>
        )}

        {caseData.symptoms_text && (
          <div className="card">
            <h3 style={{ marginBottom: '1rem' }}>📝 Patient Symptoms &amp; Notes</h3>
            <blockquote style={{
              padding: '1rem 1.5rem',
              borderLeft: '3px solid var(--primary-500)',
              background: 'rgba(99, 102, 241, 0.05)',
              borderRadius: '0 0.5rem 0.5rem 0',
              fontStyle: 'italic',
            }}>
              "{caseData.symptoms_text}"
            </blockquote>
          </div>
        )}
      </div>

      {/* AI Explanation & Recommendations */}
      <div className="grid grid-2 animate-fade-in stagger-4" style={{ marginBottom: 'var(--space-xl)' }}>
        {caseData.precautions && (
          <div className="card">
            <h3 style={{ marginBottom: '1rem' }}>🛡️ Precautions</h3>
            <p style={{ whiteSpace: 'pre-wrap' }}>{caseData.precautions}</p>
          </div>
        )}
        {caseData.consult_doctor && (
          <div className="card">
            <h3 style={{ marginBottom: '1rem' }}>👨‍⚕️ When to Consult a Dermatologist</h3>
            <p style={{ whiteSpace: 'pre-wrap' }}>{caseData.consult_doctor}</p>
          </div>
        )}
      </div>

      <Disclaimer />
    </div>
  );
}
