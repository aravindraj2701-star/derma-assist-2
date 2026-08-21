import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { historyAPI } from '../api/api';
import { safePercent } from '../utils/formatters';
import './HistoryPage.css';

export default function HistoryPage() {
  const [cases, setCases] = useState([]);
  const [total, setTotal] = useState(0);
  const [availableDiseases, setAvailableDiseases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const [viewMode, setViewMode] = useState('table'); // 'table' or 'grid'

  // Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [confidenceFilter, setConfidenceFilter] = useState('all');
  const [diseaseFilter, setDiseaseFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [activePreset, setActivePreset] = useState('all');

  const limit = 15;

  const loadCases = async () => {
    setLoading(true);
    try {
      const filters = {
        q: searchQuery.trim() || undefined,
        disease: diseaseFilter !== 'all' ? diseaseFilter : undefined,
        severity: severityFilter !== 'all' ? severityFilter : undefined,
        sort_by: sortBy,
      };

      if (confidenceFilter === 'high') {
        filters.min_confidence = 0.70;
      } else if (confidenceFilter === 'moderate') {
        filters.min_confidence = 0.50;
        filters.max_confidence = 0.6999;
      } else if (confidenceFilter === 'low') {
        filters.max_confidence = 0.4999;
      } else if (confidenceFilter === 'review_advised') {
        filters.status = 'review_advised';
      }

      const res = await historyAPI.getAll(limit, offset, filters);
      setCases(res.data.cases || []);
      setTotal(res.data.total || 0);
      if (res.data.available_diseases) {
        setAvailableDiseases(res.data.available_diseases);
      }
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      loadCases();
    }, 200);
    return () => clearTimeout(timer);
  }, [offset, searchQuery, confidenceFilter, diseaseFilter, severityFilter, sortBy]);

  const handlePresetSelect = (presetKey) => {
    setActivePreset(presetKey);
    setOffset(0);

    if (presetKey === 'all') {
      setSearchQuery('');
      setConfidenceFilter('all');
      setDiseaseFilter('all');
      setSeverityFilter('all');
    } else if (presetKey === 'review_advised') {
      setConfidenceFilter('review_advised');
      setSeverityFilter('all');
    } else if (presetKey === 'high_confidence') {
      setConfidenceFilter('high');
      setSeverityFilter('all');
    } else if (presetKey === 'malignant') {
      setSeverityFilter('malignant');
      setConfidenceFilter('all');
    }
  };

  const handleResetFilters = () => {
    setSearchQuery('');
    setConfidenceFilter('all');
    setDiseaseFilter('all');
    setSeverityFilter('all');
    setSortBy('newest');
    setActivePreset('all');
    setOffset(0);
  };

  const hasActiveFilters = Boolean(
    searchQuery.trim() ||
    confidenceFilter !== 'all' ||
    diseaseFilter !== 'all' ||
    severityFilter !== 'all' ||
    sortBy !== 'newest'
  );

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="page container">
      {/* Page Header */}
      <div className="history-page-header animate-fade-in">
        <div>
          <h1 className="page-title">Case Consultation History</h1>
          <p className="page-subtitle">
            Archive of past AI-assisted skin screenings, differential diagnoses, and clinical reports
          </p>
        </div>

        <div className="history-header-actions">
          <div className="view-toggle-btns">
            <button
              type="button"
              className={`view-btn ${viewMode === 'table' ? 'active' : ''}`}
              onClick={() => setViewMode('table')}
              title="Table View"
            >
              ☰ Table
            </button>
            <button
              type="button"
              className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title="Card Grid View"
            >
              ☷ Cards
            </button>
          </div>
          <Link to="/analyze" className="btn btn-primary btn-sm">
            + New Analysis
          </Link>
        </div>
      </div>

      {/* Advanced Clinical Search & Filter Toolbar */}
      <div className="history-filter-panel animate-fade-in stagger-1">
        {/* Case Search Input */}
        <div className="case-search-box">
          <span className="case-search-icon">🔍</span>
          <input
            type="text"
            className="case-search-input"
            placeholder="Search by Case #ID, disease name, or symptom keyword (e.g. #25, Melanoma, itching, forearm)..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setOffset(0);
            }}
          />
          {searchQuery && (
            <button
              type="button"
              className="search-clear-btn"
              onClick={() => {
                setSearchQuery('');
                setOffset(0);
              }}
            >
              ✕
            </button>
          )}
        </div>

        {/* Dropdown Filters Row */}
        <div className="filter-controls-row">
          {/* Confidence Filter */}
          <div className="filter-group">
            <label className="filter-label">Confidence Score</label>
            <select
              className="filter-select"
              value={confidenceFilter}
              onChange={(e) => {
                setConfidenceFilter(e.target.value);
                setOffset(0);
                setActivePreset('custom');
              }}
            >
              <option value="all">All Confidences</option>
              <option value="high">High (≥ 70%)</option>
              <option value="moderate">Moderate (50% – 69%)</option>
              <option value="low">Low (&lt; 50%)</option>
              <option value="review_advised">Review Advised Only</option>
            </select>
          </div>

          {/* Condition / Disease Filter */}
          <div className="filter-group">
            <label className="filter-label">Condition / Disease</label>
            <select
              className="filter-select"
              value={diseaseFilter}
              onChange={(e) => {
                setDiseaseFilter(e.target.value);
                setOffset(0);
                setActivePreset('custom');
              }}
            >
              <option value="all">All Conditions</option>
              {availableDiseases.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          {/* Severity Risk Tier */}
          <div className="filter-group">
            <label className="filter-label">Risk Severity Tier</label>
            <select
              className="filter-select"
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setOffset(0);
                setActivePreset('custom');
              }}
            >
              <option value="all">All Severities</option>
              <option value="malignant">Malignant (Melanoma/BCC)</option>
              <option value="precancerous">Pre-cancerous (Actinic Keratosis)</option>
              <option value="benign">Benign Conditions</option>
            </select>
          </div>

          {/* Sorting */}
          <div className="filter-group">
            <label className="filter-label">Sort Cases By</label>
            <select
              className="filter-select"
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setOffset(0);
              }}
            >
              <option value="newest">Date (Newest First)</option>
              <option value="oldest">Date (Oldest First)</option>
              <option value="confidence_desc">Confidence (Highest First)</option>
              <option value="confidence_asc">Confidence (Lowest First)</option>
            </select>
          </div>
        </div>

        {/* Quick Filter Preset Chips */}
        <div className="quick-filter-chips">
          <span className="chips-label">Quick Presets:</span>
          <button
            type="button"
            className={`preset-chip ${activePreset === 'all' && !hasActiveFilters ? 'active' : ''}`}
            onClick={() => handlePresetSelect('all')}
          >
            All Cases
          </button>
          <button
            type="button"
            className={`preset-chip ${activePreset === 'review_advised' || confidenceFilter === 'review_advised' ? 'active' : ''}`}
            onClick={() => handlePresetSelect('review_advised')}
          >
            ⚠️ Review Advised
          </button>
          <button
            type="button"
            className={`preset-chip ${activePreset === 'high_confidence' || confidenceFilter === 'high' ? 'active' : ''}`}
            onClick={() => handlePresetSelect('high_confidence')}
          >
            🎯 High Confidence (≥70%)
          </button>
          <button
            type="button"
            className={`preset-chip ${activePreset === 'malignant' || severityFilter === 'malignant' ? 'active' : ''}`}
            onClick={() => handlePresetSelect('malignant')}
          >
            🛡️ Malignant Cases
          </button>
        </div>

        {/* Match Count & Reset Bar */}
        <div className="filter-status-bar">
          <span>
            Showing <strong>{cases.length}</strong> of <strong>{total}</strong> matching cases
          </span>
          {hasActiveFilters && (
            <button
              type="button"
              className="reset-filters-btn"
              onClick={handleResetFilters}
            >
              ↺ Reset All Filters
            </button>
          )}
        </div>
      </div>

      {/* Case List Content */}
      {loading ? (
        <div className="loading-overlay" style={{ padding: '4rem 1.5rem' }}>
          <div className="spinner"></div>
          <p className="loading-text">Loading matching cases...</p>
        </div>
      ) : cases.length === 0 ? (
        <div className="empty-state card animate-fade-in">
          <div className="empty-icon">🔍</div>
          <h3>No matching cases found</h3>
          <p>
            {hasActiveFilters
              ? 'No clinical records matched your search query or filter criteria.'
              : 'No patient analyses have been recorded yet.'}
          </p>
          {hasActiveFilters ? (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              style={{ marginTop: '1rem' }}
              onClick={handleResetFilters}
            >
              Clear All Filters
            </button>
          ) : (
            <Link to="/analyze" className="btn btn-primary" style={{ marginTop: '1rem' }}>
              Start First Analysis
            </Link>
          )}
        </div>
      ) : (
        <>
          {viewMode === 'table' ? (
            <div className="dashboard-table-card animate-fade-in stagger-2">
              <div className="table-responsive">
                <table className="clinical-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Case ID</th>
                      <th>Predicted Disease</th>
                      <th>Confidence</th>
                      <th>Patient Reported Notes</th>
                      <th>Status</th>
                      <th style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cases.map((c) => (
                      <tr key={c.case_id}>
                        <td className="table-date-cell">
                          {new Date(c.created_at).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                          })}
                        </td>
                        <td className="table-id-cell">
                          <strong>#{c.case_id}</strong>
                        </td>
                        <td className="table-disease-cell">
                          <strong>{c.predicted_disease || 'Unknown'}</strong>
                        </td>
                        <td>
                          <div className="confidence-cell">
                            <div className="confidence-mini-bar">
                              <div
                                className="confidence-mini-fill"
                                style={{ width: `${Math.min((c.confidence || 0) * 100, 100)}%` }}
                              ></div>
                            </div>
                            <span>{safePercent(c.confidence)}</span>
                          </div>
                        </td>
                        <td className="table-notes-cell">
                          {c.symptoms_text ? (
                            <span title={c.symptoms_text}>
                              {c.symptoms_text.length > 50
                                ? c.symptoms_text.substring(0, 50) + '...'
                                : c.symptoms_text}
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)' }}>—</span>
                          )}
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              c.is_low_confidence ? 'badge-warning' : 'badge-success'
                            }`}
                          >
                            {c.is_low_confidence ? 'Review Advised' : 'Complete'}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <Link
                            to={`/history/${c.case_id}`}
                            className="btn btn-secondary btn-sm table-action-btn"
                          >
                            View Report →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            /* Card Grid View */
            <div className="history-grid animate-fade-in stagger-2">
              {cases.map((c) => (
                <Link
                  to={`/history/${c.case_id}`}
                  key={c.case_id}
                  className="history-card"
                >
                  <div className="history-card-header">
                    <span className="badge badge-neutral">Case #{c.case_id}</span>
                    <span className="history-date">
                      {new Date(c.created_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </span>
                  </div>

                  <h3 className="history-disease">{c.predicted_disease}</h3>

                  <div className="history-confidence">
                    <div className="confidence-mini-bar" style={{ flex: 1 }}>
                      <div
                        className="confidence-mini-fill"
                        style={{ width: `${Math.min((c.confidence || 0) * 100, 100)}%` }}
                      ></div>
                    </div>
                    <span className="history-confidence-value">
                      {safePercent(c.confidence)}
                    </span>
                  </div>

                  {c.symptoms_text && (
                    <p className="history-symptoms">
                      {c.symptoms_text.length > 80
                        ? c.symptoms_text.substring(0, 80) + '...'
                        : c.symptoms_text}
                    </p>
                  )}

                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginTop: 'auto',
                    }}
                  >
                    <span
                      className={`badge ${
                        c.is_low_confidence ? 'badge-warning' : 'badge-success'
                      }`}
                    >
                      {c.is_low_confidence ? 'Review Advised' : 'Complete'}
                    </span>
                    <span className="history-view-link">View Full Report →</span>
                  </div>
                </Link>
              ))}
            </div>
          )}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="pagination animate-fade-in">
              <button
                className="btn btn-secondary btn-sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                ← Previous
              </button>
              <span className="page-info">
                Page {currentPage} of {totalPages} ({total} total cases)
              </span>
              <button
                className="btn btn-secondary btn-sm"
                disabled={offset + limit >= total}
                onClick={() => setOffset(offset + limit)}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
