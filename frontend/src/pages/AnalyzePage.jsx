import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { predictAPI } from '../api/api';
import Disclaimer from '../components/Disclaimer';
import './AnalyzePage.css';

// Fitzpatrick phototype options for selection box
const FITZPATRICK_OPTIONS = [
  { value: '', label: 'Select Fitzpatrick skin phototype (Optional)' },
  { value: 'Type I — Pale white skin (always burns, never tans)', label: 'Type I — Pale white skin (always burns, never tans)' },
  { value: 'Type II — Fair skin (burns easily, tans minimally)', label: 'Type II — Fair skin (burns easily, tans minimally)' },
  { value: 'Type III — Light brown / Medium tone (gradually tans)', label: 'Type III — Light brown / Medium tone (gradually tans)' },
  { value: 'Type IV — Moderate brown / Olive skin (rarely burns, tans easily)', label: 'Type IV — Moderate brown / Olive skin (rarely burns, tans easily)' },
  { value: 'Type V — Dark brown skin (very rarely burns, tans profusely)', label: 'Type V — Dark brown skin (very rarely burns, tans profusely)' },
  { value: 'Type VI — Deeply pigmented / Black skin (never burns)', label: 'Type VI — Deeply pigmented / Black skin (never burns)' },
  { value: 'Unknown / Not Specified', label: 'Unknown / Not Specified' },
];

// Preset sample test cases from Google SCIN dataset with free-text descriptions
const SAMPLE_CASES = [
  {
    id: 'eczema-demo',
    title: 'Eczema / Atopic Dermatitis',
    bodyPart: 'Left forearm and antecubital fossa',
    duration: '3 weeks (subacute flare)',
    textures: 'Rough, flaky, scaly, and slightly raised dry patches',
    symptoms: 'Intense nocturnal itching (pruritus), worsening erythema with dry skin',
    age: '34',
    sex: 'Female',
    fst: 'Type II — Fair skin (burns easily, tans minimally)',
    notes: 'Pruritic, dry erythematous scaly plaques on forearm lasting 3 weeks. Itches intensely at night.',
  },
  {
    id: 'psoriasis-demo',
    title: 'Plaque Psoriasis',
    bodyPart: 'Extensor knees and elbows',
    duration: '3 months',
    textures: 'Thick raised red plaques covered with silvery white scales',
    symptoms: 'Moderate itching, gradually increasing in size with mild peeling',
    age: '46',
    sex: 'Male',
    fst: 'Type III — Light brown / Medium tone (gradually tans)',
    notes: 'Well-demarcated thick erythematous plaques with silvery scales on extensor knees, spreading gradually.',
  },
  {
    id: 'contact-demo',
    title: 'Allergic Contact Dermatitis',
    bodyPart: 'Back of right hand and fingers',
    duration: '4 days',
    textures: 'Raised bumpy rash with small fluid-filled vesicles and oozing',
    symptoms: 'Severe burning sensation and sudden intense itching after solvent exposure',
    age: '28',
    sex: 'Female',
    fst: 'Type IV — Moderate brown / Olive skin (rarely burns, tans easily)',
    notes: 'Acute vesicular eruption with burning and severe itching after handling gardening solvents.',
  },
  {
    id: 'zoster-demo',
    title: 'Herpes Zoster',
    bodyPart: 'Right ribcage / upper torso (unilateral)',
    duration: '5 days',
    textures: 'Clustered fluid-filled blisters on raised red erythematous base',
    symptoms: 'Sharp neuropathic burning pain, localized tenderness, and tingling',
    age: '63',
    sex: 'Male',
    fst: 'Type V — Dark brown skin (very rarely burns, tans profusely)',
    notes: 'Unilateral clustered fluid-filled vesicles on thoracic dermatome with sharp neuropathic pain.',
  }
];

export default function AnalyzePage() {
  const navigate = useNavigate();
  const [imageFile, setImageFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [imageInfo, setImageInfo] = useState(null);

  // Free-Text Clinical Symptom State — starts completely empty for user input
  const [bodyPart, setBodyPart] = useState('');
  const [duration, setDuration] = useState('');
  const [textures, setTextures] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const [patientNotes, setPatientNotes] = useState('');

  // Demographics & Fitzpatrick Type — starts completely empty for user input
  const [age, setAge] = useState('');
  const [sexAtBirth, setSexAtBirth] = useState('');
  const [fitzpatrickType, setFitzpatrickType] = useState('');

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState('');

  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    if (rejectedFiles.length > 0) {
      setError('Please upload a valid image file (JPG, JPEG, or PNG, max 10MB)');
      return;
    }
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setImageFile(file);
      const objUrl = URL.createObjectURL(file);
      setPreview(objUrl);
      setError('');

      const img = new Image();
      img.onload = () => {
        setImageInfo({
          name: file.name,
          size: `${(file.size / 1024).toFixed(1)} KB`,
          dimensions: `${img.width} × ${img.height} px`,
        });
      };
      img.src = objUrl;
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
  });

  const loadSampleCase = (sample) => {
    setBodyPart(sample.bodyPart);
    setDuration(sample.duration);
    setTextures(sample.textures);
    setSymptoms(sample.symptoms);
    setAge(sample.age);
    setSexAtBirth(sample.sex);
    setFitzpatrickType(sample.fst);
    setPatientNotes(sample.notes);

    // Create realistic canvas image placeholder if no file loaded
    const canvas = document.createElement('canvas');
    canvas.width = 400;
    canvas.height = 400;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = sample.fst.includes('I') || sample.fst.includes('II') ? '#ffdfc4' : sample.fst.includes('III') || sample.fst.includes('IV') ? '#dca87a' : '#8d5524';
    ctx.fillRect(0, 0, 400, 400);

    // Lesion pattern
    ctx.fillStyle = '#b91c1c';
    ctx.beginPath();
    ctx.arc(200, 200, 75, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#7f1d1d';
    ctx.beginPath();
    ctx.arc(190, 190, 40, 0, Math.PI * 2);
    ctx.fill();

    canvas.toBlob((blob) => {
      const file = new File([blob], `${sample.id}_reference.png`, { type: 'image/png' });
      setImageFile(file);
      setPreview(URL.createObjectURL(file));
      setImageInfo({
        name: `${sample.title} Demo Sample`,
        size: `${(file.size / 1024).toFixed(1)} KB`,
        dimensions: '400 × 400 px',
      });
      setError('');
    });
  };

  const handleAnalyze = async () => {
    if (!imageFile) {
      setError('Please upload a skin image or select one of the preset sample cases below.');
      return;
    }

    setLoading(true);
    setError('');
    setProgress('Preprocessing image & encoding clinical features from text...');

    try {
      const formData = new FormData();
      formData.append('image', imageFile);
      formData.append('body_part', bodyPart);
      formData.append('body_location', bodyPart);
      formData.append('duration', duration);
      formData.append('textures', textures);
      formData.append('symptoms', symptoms);
      formData.append('age', age);
      formData.append('age_group', age);
      formData.append('sex_at_birth', sexAtBirth);
      formData.append('fitzpatrick_skin_type', fitzpatrickType);
      formData.append('patient_notes', patientNotes.trim());

      setProgress('Running Google SCIN Multimodal Neural Network...');
      const response = await predictAPI.analyzeWithForm(formData);

      navigate('/result', {
        state: {
          result: response.data,
          submittedSymptoms: {
            bodyPart,
            duration,
            textures,
            symptoms,
            age,
            ageGroup: age,
            sexAtBirth,
            fitzpatrickType,
            patientNotes: patientNotes.trim(),
          }
        }
      });
    } catch (err) {
      console.error('Analysis failed:', err);
      setError(
        err.response?.data?.detail ||
        'Analysis failed. Please check network connection and try again.'
      );
    } finally {
      setLoading(false);
      setProgress('');
    }
  };

  const clearImage = () => {
    setImageFile(null);
    setPreview(null);
    setImageInfo(null);
    setError('');
  };

  return (
    <div className="page container">
      {/* Header */}
      <div className="page-header animate-fade-in">
        <div className="clinical-badge">
          <span className="badge-dot"></span>
          <span>Google SCIN Dataset Multimodal Model</span>
        </div>
        <h1 className="page-title">Clinical Skin Condition Analysis</h1>
        <p className="page-subtitle">
          Submit clinical image and structured symptom descriptions for multimodal multi-label AI screening.
        </p>
      </div>

      {/* Preset 1-Click Samples Bar */}
      <div className="card sample-presets-card animate-fade-in">
        <div className="presets-header">
          <span className="presets-icon">🧪</span>
          <div>
            <h4 className="presets-title">Quick Demo Clinical Cases</h4>
            <p className="presets-subtitle">Select a preset case from the SCIN benchmark dataset to auto-populate:</p>
          </div>
        </div>
        <div className="sample-buttons-grid">
          {SAMPLE_CASES.map((sample) => (
            <button
              key={sample.id}
              type="button"
              className="sample-case-btn"
              onClick={() => loadSampleCase(sample)}
            >
              <span className="case-badge">{sample.fst.split(' ')[0]}</span>
              <span className="case-title">{sample.title}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="analyze-layout">
        {/* Left Column: Image Upload Area */}
        <div className="card analyze-upload-card animate-fade-in stagger-1">
          <h3 className="card-title">
            <span>📷</span>
            <span>Clinical Image Upload</span>
          </h3>

          {!preview ? (
            <div
              {...getRootProps()}
              className={`medical-dropzone ${isDragActive ? 'dropzone-active' : ''}`}
            >
              <input {...getInputProps()} />
              <div className="dropzone-inner">
                <div className="dropzone-icon-circle">
                  <span>🩺</span>
                </div>
                <p className="dropzone-main-text">
                  {isDragActive
                    ? 'Drop the dermatological image here...'
                    : 'Drag & drop skin image, or browse local files'}
                </p>
                <p className="dropzone-sub-text">
                  Supports JPG, JPEG, PNG • Up to 10MB
                </p>
                <button type="button" className="btn btn-secondary btn-sm dropzone-btn">
                  Select Image File
                </button>
              </div>
            </div>
          ) : (
            <div className="preview-panel">
              <div className="preview-image-wrapper">
                <img src={preview} alt="Skin lesion preview" className="preview-img" />
                <button onClick={clearImage} className="preview-remove-btn" title="Remove image">
                  ✕ Remove
                </button>
              </div>
              {imageInfo && (
                <div className="image-meta-strip">
                  <span><strong>File:</strong> {imageInfo.name}</span>
                  <span><strong>Size:</strong> {imageInfo.size}</span>
                  <span><strong>Dimensions:</strong> {imageInfo.dimensions}</span>
                </div>
              )}
            </div>
          )}

          {/* Clinical Imaging Guidance */}
          <div className="imaging-tips-box">
            <h4 className="tips-title">💡 Photography Guidelines:</h4>
            <ul className="tips-list">
              <li>Ensure good, non-glare daylight or clinical examination lighting.</li>
              <li>Keep lesion centered in sharp focus with clean margins.</li>
              <li>Avoid heavy post-processing, filtering, or shadows.</li>
            </ul>
          </div>
        </div>

        {/* Right Column: Structured Symptom & Context Form */}
        <div className="card analyze-form-card animate-fade-in stagger-2">
          <h3 className="card-title">
            <span>📋</span>
            <span>Structured Clinical Symptoms</span>
          </h3>

          {/* 1. Anatomical Location & Duration */}
          <div className="form-row-grid">
            <div className="input-group">
              <label className="input-label" htmlFor="body-part-input">
                Anatomical Location
              </label>
              <input
                id="body-part-input"
                type="text"
                className="form-input"
                placeholder="e.g. Left forearm, upper back, behind right ear"
                value={bodyPart}
                onChange={(e) => setBodyPart(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label className="input-label" htmlFor="duration-input">
                Duration of Condition
              </label>
              <input
                id="duration-input"
                type="text"
                className="form-input"
                placeholder="e.g. 3 weeks, since last month, 2 days"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
              />
            </div>
          </div>

          {/* 2. Lesion Texture Characteristics (Free Text) */}
          <div className="input-group">
            <label className="input-label" htmlFor="textures-input">
              Lesion Texture Characteristics
            </label>
            <textarea
              id="textures-input"
              className="form-textarea form-textarea-short"
              rows={2}
              placeholder="Describe how the lesion looks and feels (e.g. rough and scaly, raised bump, flat patch)"
              value={textures}
              onChange={(e) => setTextures(e.target.value)}
            />
          </div>

          {/* 3. Cutaneous Sensations & Evolution (Free Text) */}
          <div className="input-group">
            <label className="input-label" htmlFor="symptoms-input">
              Reported Symptoms &amp; Evolution
            </label>
            <textarea
              id="symptoms-input"
              className="form-textarea form-textarea-short"
              rows={2}
              placeholder="Describe any symptoms and how they've changed over time (e.g. itches at night, started small and has been growing, occasionally bleeds)"
              value={symptoms}
              onChange={(e) => setSymptoms(e.target.value)}
            />
          </div>

          {/* 4. Patient Reported Notes (Multi-Line Free Textarea) */}
          <div className="input-group">
            <label className="input-label" htmlFor="patient-notes-input">
              Patient Reported Notes
              <span className="label-subtext"> — Describe symptoms, onset, or sensations in your own words</span>
            </label>
            <textarea
              id="patient-notes-input"
              className="form-textarea"
              rows={3}
              placeholder="Describe symptoms in your own words (e.g. It started as a small red patch and has been spreading slowly, feels warm to touch, itches more at night...)"
              value={patientNotes}
              onChange={(e) => setPatientNotes(e.target.value)}
            />
            <span className="input-hint">
              This free-text description is passed to the multimodal pipeline and included in your clinical report.
            </span>
          </div>

          {/* 5. Patient Demographics (Age & Sex) */}
          <div className="form-row-grid">
            <div className="input-group">
              <label className="input-label" htmlFor="age-input">Patient Age Range</label>
              <input
                id="age-input"
                type="text"
                className="form-input"
                placeholder="e.g. 34"
                value={age}
                onChange={(e) => setAge(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label className="input-label" htmlFor="sex-input">Sex at Birth</label>
              <input
                id="sex-input"
                type="text"
                className="form-input"
                placeholder="e.g. Female, Male, Intersex"
                value={sexAtBirth}
                onChange={(e) => setSexAtBirth(e.target.value)}
              />
            </div>
          </div>

          {/* 6. Fitzpatrick Skin Type (FST) Selection Box */}
          <div className="input-group">
            <label className="input-label" htmlFor="fst-select">
              Fitzpatrick Skin Type (FST)
              <span className="label-subtext"> — Self-reported skin phototype</span>
            </label>
            <select
              id="fst-select"
              className="form-select"
              value={fitzpatrickType}
              onChange={(e) => setFitzpatrickType(e.target.value)}
            >
              {FITZPATRICK_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <span className="input-hint">
              Used for clinical tone calibration &amp; fairness analysis
            </span>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="error-banner">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {/* Submit Action Button */}
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={!imageFile || loading}
            className="btn btn-primary btn-lg analyze-submit-btn"
          >
            {loading ? (
              <>
                <div className="spinner"></div>
                <span>{progress || 'Processing Multimodal Analysis...'}</span>
              </>
            ) : (
              <>
                <span>🔬</span>
                <span>Analyze Skin Condition (SCIN Multimodal)</span>
              </>
            )}
          </button>

          {/* Medical Research Disclaimer */}
          <Disclaimer />
        </div>
      </div>

      {/* Loading Overlay Modal */}
      {loading && (
        <div className="analysis-loading-overlay">
          <div className="analysis-loading-card">
            <div className="clinical-pulse-box">
              <div className="pulse-circle"></div>
              <div className="pulse-circle delay-1"></div>
              <div className="pulse-circle delay-2"></div>
              <span className="pulse-icon">🩺</span>
            </div>
            <h3 className="loading-title">Analyzing Multimodal Inputs</h3>
            <p className="loading-subtitle">{progress}</p>
            <div className="loading-steps-list">
              <div className="loading-step-item active">
                <span className="step-check">✓</span> Image Feature Extraction (ResNet34 Backbone)
              </div>
              <div className="loading-step-item active">
                <span className="step-check">✓</span> Tabular Symptom Encoding (MLP Branch)
              </div>
              <div className="loading-step-item active">
                <span className="step-check">⟳</span> Multimodal Cross-Attention Fusion
              </div>
              <div className="loading-step-item">
                <span className="step-check">○</span> Fitzpatrick Fairness Stratification
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
