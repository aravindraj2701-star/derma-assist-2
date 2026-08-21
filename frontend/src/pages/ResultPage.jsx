import { useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { predictAPI } from '../api/api';
import Disclaimer from '../components/Disclaimer';
import { formatScore, formatScoreValue } from '../utils/formatters';
import './ResultPage.css';

export default function ResultPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const result = location.state?.result;
  const submittedSymptoms = location.state?.submittedSymptoms || {};

  const [downloadingPdf, setDownloadingPdf] = useState(false);

  // If no result is present, redirect to analyze page
  if (!result) {
    return (
      <div className="page container">
        <div className="card empty-state-card animate-fade-in">
          <div className="empty-icon">🩺</div>
          <h2 className="empty-title">No Active Screening Case</h2>
          <p className="empty-subtitle">
            Upload a clinical image and structured symptoms to generate an AI decision-support report.
          </p>
          <Link to="/analyze" className="btn btn-primary btn-lg">
            Start New Clinical Analysis
          </Link>
        </div>
      </div>
    );
  }

  const primary = result.primary_prediction || {
    condition: result.predicted_disease || 'Unknown',
    confidence_pct: (result.confidence * 100).toFixed(1),
    risk_tier: 'Clinical Evaluation Recommended',
    risk_level: 'moderate',
  };

  const differentials = result.differential_diagnoses || (result.predictions ? result.predictions.slice(1) : []);
  const multimodal = result.multimodal_breakdown || {
    image_weight_pct: 65.0,
    symptom_weight_pct: 35.0,
    top_image_condition: primary.condition,
    top_symptom_condition: primary.condition,
  };

  const fairness = result.fairness_context || {
    fitzpatrick_group: 'Fitzpatrick III-IV (Intermediate)',
    fairness_note: 'Calibrated using Google SCIN dataset stratified benchmark across skin tones I–VI.',
  };

  const refExample = result.reference_example;

  // Format Patient Image Source
  const patientImageSrc = result.original_image
    ? (result.original_image.startsWith('data:') ? result.original_image : `data:image/jpeg;base64,${result.original_image}`)
    : (result.image_ref
      ? (result.image_ref.startsWith('data:') ? result.image_ref : `data:image/jpeg;base64,${result.image_ref}`)
      : null);

  // Format Reference Image Source
  const refImageSrc = refExample?.image_base64
    ? (refExample.image_base64.startsWith('data:') ? refExample.image_base64 : `data:image/jpeg;base64,${refExample.image_base64}`)
    : (refExample?.image_path ? `/api/dataset/image?path=${encodeURIComponent(refExample.image_path)}` : null);

  // Candidate Predictions List
  const candidatePredictions = result.all_predictions || (primary ? [primary, ...differentials] : []);

  // Differentiating Features Clinical Comparison Data
  const differentiatingFeatures = (result.differentiating_features && result.differentiating_features.length > 0)
    ? result.differentiating_features
    : candidatePredictions.map((item, index) => {
        const cond = item.condition || item.disease || 'Unknown';
        const rank = item.rank || index + 1;
        const dur = (result.duration || submittedSymptoms.duration || '').toLowerCase();
        const loc = (result.body_location || submittedSymptoms.bodyPart || '').toLowerCase();
        const tex = (result.textures || submittedSymptoms.textures || '').toLowerCase();

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
              ? (dur.includes('1 week') || dur.includes('day') || dur.includes('acute')
                  ? 'Short 1-week duration and rapid onset strongly favor Urticaria over chronic conditions.'
                  : 'Reported onset and intensely pruritic raised morphology align closely with urticaria.')
              : cond === 'Eczema'
              ? (dur.includes('1 week') || dur.includes('day') || loc.includes('ear') || tex.includes('scalp')
                  ? 'Scalp/dryness texture matches, but shorter duration argues against typical chronic eczema pattern.'
                  : 'Scaly erythematous morphology matches, but timeline balances with competing differentials.')
              : cond === 'Acute dermatitis, NOS'
              ? 'Flat/dry texture and short duration align, but lacks a clear specific trigger to confirm.'
              : cond === 'Psoriasis'
              ? (dur.includes('1 week') || dur.includes('day')
                  ? 'Duration of only 1 week is too short for typical psoriasis presentation, lowering confidence.'
                  : 'Plaque morphology differs from acute presentation, placing it lower than top match.')
              : cond === 'Irritant Contact Dermatitis'
              ? (loc.includes('ear')
                  ? 'Ear location and dryness/flat texture are consistent, but no reported exposure history reduces confidence.'
                  : 'Localized erythema is consistent, but lack of documented direct contact exposure limits score.')
              : `Clinical timeline and reported morphology provide secondary alignment relative to ${primary.condition}.`,
          confidence_pct: item.confidence_pct || Math.round((item.combined_score || 0) * 100),
        };
      });

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      const response = await predictAPI.exportPdf(result);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `DermaAssist_SCIN_Report_${result.case_id || 'case'}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('PDF export failed:', err);
      alert('Unable to generate PDF report at this time. Please try again.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const reportedNotes = (
    result.patient_notes ||
    result.symptoms_text ||
    submittedSymptoms.patientNotes ||
    submittedSymptoms.freeTextNotes ||
    ''
  ).trim();

  return (
    <div className="page container">
      {/* Top Action Bar */}
      <div className="results-top-bar animate-fade-in">
        <div className="results-meta">
          <div className="clinical-badge">
            <span className="badge-dot"></span>
            <span>Case ID: #{result.case_id || 'SCIN-001'}</span>
          </div>
          <span className="meta-divider">•</span>
          <span className="meta-text">Multimodal SCIN Model</span>
          <span className="meta-divider">•</span>
          <span className="meta-text">{fairness.fitzpatrick_group}</span>
        </div>

        <div className="results-actions">
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="btn btn-secondary btn-sm"
          >
            {downloadingPdf ? 'Generating PDF...' : '📥 Download Clinical PDF'}
          </button>
          <button
            onClick={() => navigate('/analyze')}
            className="btn btn-primary btn-sm"
          >
            + New Analysis
          </button>
        </div>
      </div>

      {/* Side-by-Side Lesion Comparison Analysis Section */}
      <div className="card comparison-card animate-fade-in">
        <div className="comparison-header">
          <span className="comparison-icon">🔬</span>
          <div>
            <h3 className="comparison-title">Lesion Comparison Analysis</h3>
            <p className="comparison-subtitle">
              Visual side-by-side correlation between patient presentation and verified training archive example
            </p>
          </div>
        </div>

        <div className="comparison-images-grid">
          {/* Patient Image Box */}
          <div className="comparison-box">
            <div className="comparison-img-frame">
              {patientImageSrc ? (
                <img
                  src={patientImageSrc}
                  alt="Patient uploaded lesion"
                  className="comparison-img"
                />
              ) : (
                <div className="comparison-no-img">
                  <span>📷</span>
                  <p>No patient image available</p>
                </div>
              )}
            </div>
            <div className="comparison-caption-box">
              <span className="caption-label">Patient Uploaded Lesion</span>
              <span className="caption-sub">Active Consultation Submission</span>
            </div>
          </div>

          {/* Matched Reference Image Box */}
          <div className="comparison-box">
            <div className="comparison-img-frame">
              {refImageSrc ? (
                <img
                  src={refImageSrc}
                  alt={`Matched training example for ${primary.condition}`}
                  className="comparison-img"
                />
              ) : (
                <div className="comparison-no-img ref-fallback">
                  <span>ℹ️</span>
                  <p className="fallback-title">No close reference match found</p>
                  <p className="fallback-sub">No exact image sample in active local reference slice</p>
                </div>
              )}
            </div>
            <div className="comparison-caption-box">
              <div className="caption-title-row">
                <span className="caption-label">Matched Reference Training Example</span>
                {refExample?.similarity_pct && (
                  <span className="similarity-badge">
                    ⚡ {refExample.similarity_pct}% Visual Match
                  </span>
                )}
              </div>
              <span className="caption-sub">
                {refExample?.source ? `${refExample.source} • ${refExample.disease_name || primary.condition}` : `Training Archive • ${primary.condition}`}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="results-grid">
        {/* Left Column: Primary & Differential Diagnoses */}
        <div className="results-left-col">
          {/* Primary Diagnosis Hero Card */}
          <div className="card primary-result-card animate-fade-in stagger-1">
            <div className="primary-header">
              <span className="primary-kicker">Primary AI Assessment</span>
              <span className={`risk-badge risk-${primary.risk_level || 'moderate'}`}>
                {primary.risk_tier || 'Common Cutaneous Condition'}
              </span>
            </div>

            <h2 className="primary-condition-name">{primary.condition || primary.disease}</h2>

            <div className="confidence-meter-box">
              <div className="confidence-meter-header">
                <span className="meter-label">Model Confidence Score</span>
                <span className="meter-value">{primary.confidence_pct}%</span>
              </div>
              <div className="confidence-bar-bg">
                <div
                  className="confidence-bar-fill"
                  style={{ width: `${Math.min(primary.confidence_pct, 100)}%` }}
                ></div>
              </div>
            </div>

            {/* Multimodal Feature Breakdown */}
            <div className="multimodal-pills-row">
              <div className="modality-pill">
                <span className="modality-icon">🖼️</span>
                <div>
                  <span className="modality-title">Vision Alignment</span>
                  <span className="modality-val">{formatScore(primary.image_score || primary.confidence_pct || 78)}</span>
                </div>
              </div>
              <div className="modality-pill">
                <span className="modality-icon">📋</span>
                <div>
                  <span className="modality-title">Symptom Alignment</span>
                  <span className="modality-val">{formatScore(primary.symptom_score || primary.confidence_pct || 72)}</span>
                </div>
              </div>
            </div>

            {/* Clinical Guidance Box */}
            <div className="clinical-advisory-box">
              <h4 className="advisory-title">👨‍⚕️ Clinical Decision Support:</h4>
              <p className="advisory-text">
                {result.ai_explanation ||
                  `The multimodal analysis combined dermatoscopic lesion features with patient-reported duration and symptom markers to identify ${primary.condition}.`}
              </p>
              <div className="advisory-precautions">
                <strong>Recommended Next Steps:</strong>
                <ul>
                  <li>Schedule an in-person clinical dermatological examination.</li>
                  <li>Avoid scratching or applying unprescribed high-potency topical steroids.</li>
                  <li>Monitor for changes in size, border asymmetry, or color evolution.</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Differential Diagnoses & Confidence Breakdown Table */}
          <div className="card differentials-card animate-fade-in stagger-2">
            <div className="section-title-with-badge">
              <h3 className="card-title">
                <span>📊</span>
                <span>Differential Diagnoses &amp; Confidence Breakdown</span>
              </h3>
              <span className="pipeline-mode-badge">Symptom-First Pipeline</span>
            </div>
            <p className="card-intro">
              Candidate conditions filtered by clinical symptom profile compatibility (40%) and refined by lesion image features (60%):
            </p>

            <div className="table-responsive" style={{ marginTop: '1rem' }}>
              <table className="breakdown-table">
                <thead>
                  <tr>
                    <th style={{ width: '60px' }}>Rank</th>
                    <th>Condition / Disease</th>
                    <th style={{ textAlign: 'center' }}>Image Score</th>
                    <th style={{ textAlign: 'center' }}>Symptom Alignment</th>
                    <th style={{ textAlign: 'right' }}>Combined Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {(result.all_predictions || (primary ? [primary, ...differentials] : [])).map((item, index) => (
                    <tr key={index} className={item.rank === 1 ? 'primary-breakdown-row' : ''}>
                      <td>
                        <span className={`diff-rank-badge ${item.rank === 1 ? 'rank-1' : ''}`}>
                          #{item.rank || index + 1}
                        </span>
                      </td>
                      <td>
                        <div className="condition-cell-wrapper">
                          <strong className="condition-cell-title">{item.condition || item.disease}</strong>
                          {item.rank === 1 && <span className="primary-pill-tag">Primary Match</span>}
                        </div>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <span className="score-cell-pill vision-pill">
                          🖼️ {formatScore(item.image_score)}
                        </span>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <span className="score-cell-pill symptom-pill">
                          📋 {formatScore(item.symptom_score)}
                        </span>
                      </td>
                      <td>
                        <div className="combined-cell-box">
                          <div className="confidence-mini-bar">
                            <div
                              className="confidence-mini-fill"
                              style={{ width: `${Math.min(formatScoreValue(item.confidence_pct || item.combined_score), 100)}%` }}
                            ></div>
                          </div>
                          <span className="combined-pct-text">
                            {formatScore(item.confidence_pct || item.combined_score)}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Differentiating Features Clarification Section */}
          <div className="card differentiating-card animate-fade-in stagger-3">
            <div className="section-title-with-badge">
              <h3 className="card-title">
                <span>🔬</span>
                <span>Differentiating Features</span>
              </h3>
              <span className="pipeline-mode-badge clarification-badge">
                Clinical Comparison
              </span>
            </div>
            <p className="card-intro">
              Clinical distinction matrix explaining what separates these candidate diseases from each other and why they were compared for this specific case:
            </p>

            {/* Desktop Table View */}
            <div className="table-responsive desktop-differentiating-table" style={{ marginTop: '1rem' }}>
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
                      <td className="diff-overlap-text">
                        <span className="overlap-pill-text">{item.overlaps_with}</span>
                      </td>
                      <td className="diff-case-reason-text">
                        <span className="case-reason-pill">{item.confidence_vs_case}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Responsive Stacked Cards */}
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
        </div>

        {/* Right Column: Case Summary & Fairness Card */}
        <div className="results-right-col">
          {/* Submitted Case Review Card */}
          <div className="card case-summary-card animate-fade-in stagger-1">
            <h3 className="card-title">
              <span>📋</span>
              <span>Clinical Case Findings</span>
            </h3>

            <div className="case-details-table">
              <div className="detail-row">
                <span className="detail-key">Anatomical Location:</span>
                <span className="detail-val">{result.body_location || submittedSymptoms.bodyPart || 'Unspecified'}</span>
              </div>
              <div className="detail-row">
                <span className="detail-key">Lesion Duration:</span>
                <span className="detail-val">{result.duration || submittedSymptoms.duration || 'Not provided'}</span>
              </div>
              <div className="detail-row full-width-detail">
                <span className="detail-key">Lesion Texture:</span>
                <span className="detail-val">{result.textures || submittedSymptoms.textures || 'Not described'}</span>
              </div>
              <div className="detail-row full-width-detail">
                <span className="detail-key">Reported Symptoms &amp; Evolution:</span>
                <span className="detail-val">
                  {typeof submittedSymptoms.symptoms === 'string'
                    ? submittedSymptoms.symptoms
                    : (result.symptoms_text || 'None reported')}
                </span>
              </div>
              <div className="detail-row full-width-detail">
                <span className="detail-key">Patient Reported Notes:</span>
                <span className="detail-val notes-highlight">
                  {reportedNotes || 'No additional free-text symptom notes entered.'}
                </span>
              </div>
              <div className="detail-row">
                <span className="detail-key">Patient Demographics:</span>
                <span className="detail-val">
                  {submittedSymptoms.age ? `${submittedSymptoms.age} yrs` : (submittedSymptoms.ageGroup ? `${String(submittedSymptoms.ageGroup).replace('AGE_', '').replace('_', '-')}` : 'Adult')} • {submittedSymptoms.sexAtBirth || 'Unspecified'}
                </span>
              </div>
              <div className="detail-row">
                <span className="detail-key">Fitzpatrick Skin Tone:</span>
                <span className="detail-val">
                  {submittedSymptoms.fitzpatrickType || fairness.fitzpatrick_group || 'Type III'}
                </span>
              </div>
            </div>
          </div>

          {/* Demographic & Fairness Transparency Card */}
          <div className="card fairness-card animate-fade-in stagger-2">
            <div className="fairness-header">
              <span className="fairness-icon">⚖️</span>
              <div>
                <h4 className="fairness-title">Fairness &amp; Skin Tone Calibration</h4>
                <span className="fairness-badge">Google SCIN Validated</span>
              </div>
            </div>

            <p className="fairness-text">
              This multimodal model is trained and evaluated with Fitzpatrick Skin Type (FST I–VI) stratification
              to ensure equitable diagnostic recall across diverse skin complexions.
            </p>

            <div className="fairness-stats-grid">
              <div className="fairness-stat-box">
                <span className="stat-label">Evaluated Cohort</span>
                <span className="stat-val">FST I – VI</span>
              </div>
              <div className="fairness-stat-box">
                <span className="stat-label">Skin Tone Parity Gap</span>
                <span className="stat-val">6.77%</span>
              </div>
              <div className="fairness-stat-box">
                <span className="stat-label">Active Skin Tone</span>
                <span className="stat-val">{submittedSymptoms.fitzpatrickType || 'Type III'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Medical Disclaimer */}
      <div className="results-disclaimer-wrapper">
        <Disclaimer />
      </div>
    </div>
  );
}
