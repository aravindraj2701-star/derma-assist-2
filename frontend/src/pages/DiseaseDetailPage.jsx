import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { diseaseAPI } from '../api/api';

export default function DiseaseDetailPage() {
  const { diseaseId } = useParams();
  const [disease, setDisease] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDisease();
  }, [diseaseId]);

  const loadDisease = async () => {
    try {
      const res = await diseaseAPI.getById(diseaseId);
      setDisease(res.data);
    } catch (err) {
      console.error('Failed to load disease:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page container">
        <div className="loading-overlay">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  if (!disease) {
    return (
      <div className="page container">
        <div className="empty-state card">
          <h3>Disease not found</h3>
          <Link to="/dashboard" className="btn btn-primary" style={{ marginTop: '1rem' }}>
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page container">
      <div className="page-header animate-fade-in">
        <span className={`badge badge-${disease.severity_level === 'severe' ? 'danger' : disease.severity_level === 'moderate' ? 'warning' : 'success'}`}>
          {disease.severity_level || 'Unknown'} severity
        </span>
        <h1 className="page-title">{disease.name}</h1>
      </div>

      <div className="card animate-fade-in stagger-1" style={{ marginBottom: 'var(--space-xl)' }}>
        <h3 style={{ marginBottom: '1rem' }}>📖 Description</h3>
        <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>{disease.description || 'No description available.'}</p>
      </div>

      {/* Symptoms */}
      {disease.symptoms?.length > 0 && (
        <div className="card animate-fade-in stagger-2" style={{ marginBottom: 'var(--space-xl)' }}>
          <h3 style={{ marginBottom: '1rem' }}>🔍 Known Symptoms</h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Keyword</th>
                  <th>Description</th>
                  <th>Severity</th>
                </tr>
              </thead>
              <tbody>
                {disease.symptoms.map((s) => (
                  <tr key={s.symptom_id}>
                    <td><strong>{s.symptom_keyword}</strong></td>
                    <td>{s.symptom_description}</td>
                    <td>
                      <span className={`badge badge-${s.severity === 'severe' ? 'danger' : s.severity === 'moderate' ? 'warning' : 'success'}`}>
                        {s.severity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="grid grid-2 animate-fade-in stagger-3">
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>🛡️ Precautions</h3>
          <p style={{ whiteSpace: 'pre-wrap' }}>{disease.precautions || 'No precaution data available.'}</p>
        </div>

        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>👨‍⚕️ When to Consult a Doctor</h3>
          <p style={{ whiteSpace: 'pre-wrap' }}>{disease.consult_doctor_if || 'Consult a doctor for persistent symptoms.'}</p>
        </div>
      </div>
    </div>
  );
}
