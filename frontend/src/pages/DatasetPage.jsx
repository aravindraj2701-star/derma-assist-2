import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { datasetAPI } from '../api/api';
import Disclaimer from '../components/Disclaimer';
import './DatasetPage.css';

export default function DatasetPage() {
  // Data mode: 'dataset' (Reference Training Archive) or 'history' (Predicted Cases Reports)
  const [dataMode, setDataMode] = useState('dataset');

  // Search & Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedDisease, setSelectedDisease] = useState('all');
  const [selectedSeverity, setSelectedSeverity] = useState('all');
  const [selectedLocation, setSelectedLocation] = useState('all');
  const [selectedSplit, setSelectedSplit] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [minConfidence, setMinConfidence] = useState(0);

  // Pagination & Layout
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'table'

  // Data & Loading
  const [records, setRecords] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [filterOptions, setFilterOptions] = useState({
    diseases: [],
    categories: [],
    severities: ['Benign', 'Pre-cancerous', 'Malignant'],
    body_locations: ['Face', 'Back', 'Trunk', 'Neck', 'Extremities', 'Scalp', 'Hands', 'Shoulders'],
    splits: ['train', 'test', 'validation'],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Selected Record for Detail Modal
  const [selectedRecord, setSelectedRecord] = useState(null);

  // Fetch Dataset Records
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      if (dataMode === 'dataset') {
        const params = {
          search: searchQuery.trim() || undefined,
          category: selectedCategory !== 'all' ? selectedCategory : undefined,
          disease: selectedDisease !== 'all' ? selectedDisease : undefined,
          severity: selectedSeverity !== 'all' ? selectedSeverity : undefined,
          body_location: selectedLocation !== 'all' ? selectedLocation : undefined,
          split: selectedSplit !== 'all' ? selectedSplit : undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          page,
          page_size: pageSize,
        };

        const res = await datasetAPI.getRecords(params);
        setRecords(res.data.records || []);
        setTotalCount(res.data.total || 0);
        setTotalPages(res.data.total_pages || 1);
        if (res.data.filter_options) {
          setFilterOptions(res.data.filter_options);
        }
      } else {
        // History reports mode
        const params = {
          search: searchQuery.trim() || undefined,
          severity: selectedSeverity !== 'all' ? selectedSeverity : undefined,
          min_confidence: minConfidence > 0 ? minConfidence / 100 : undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          page,
          page_size: pageSize,
        };

        const res = await datasetAPI.getHistoryExplorer(params);
        setRecords(res.data.cases || []);
        setTotalCount(res.data.total || 0);
        setTotalPages(res.data.total_pages || 1);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Unable to load records. Please verify server connection.');
    } finally {
      setLoading(false);
    }
  }, [
    dataMode,
    searchQuery,
    selectedCategory,
    selectedDisease,
    selectedSeverity,
    selectedLocation,
    selectedSplit,
    dateFrom,
    dateTo,
    minConfidence,
    page,
    pageSize,
  ]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Reset page when filters change
  const handleFilterChange = (setter, val) => {
    setter(val);
    setPage(1);
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setSelectedCategory('all');
    setSelectedDisease('all');
    setSelectedSeverity('all');
    setSelectedLocation('all');
    setSelectedSplit('all');
    setDateFrom('');
    setDateTo('');
    setMinConfidence(0);
    setPage(1);
  };

  const getSeverityBadgeClass = (sev) => {
    const s = String(sev).toLowerCase();
    if (s.includes('malignant')) return 'badge-severity-malignant';
    if (s.includes('pre-cancerous') || s.includes('actinic')) return 'badge-severity-precancerous';
    return 'badge-severity-benign';
  };

  return (
    <div className="dataset-page page container">
      {/* Header */}
      <div className="dataset-header animate-fade-in">
        <div className="dataset-header-left">
          <div className="header-badge-row">
            <span className="badge badge-accent">🗂️ Database &amp; Imaging Explorer</span>
            <span className="badge badge-secondary">{totalCount.toLocaleString()} Total Records</span>
          </div>
          <h1 className="page-title">Skin Disease Dataset Explorer</h1>
          <p className="page-subtitle">
            Inspect real dermatological imaging data, pathology symptoms descriptions, severity classifications, and screening history reports.
          </p>
        </div>

        {/* Mode Toggle Tabs */}
        <div className="mode-toggle-group">
          <button
            type="button"
            className={`mode-btn ${dataMode === 'dataset' ? 'active' : ''}`}
            onClick={() => {
              setDataMode('dataset');
              setPage(1);
            }}
          >
            📚 Reference Dataset (3,800+ Samples)
          </button>
          <button
            type="button"
            className={`mode-btn ${dataMode === 'history' ? 'active' : ''}`}
            onClick={() => {
              setDataMode('history');
              setPage(1);
            }}
          >
            📋 Predicted Case Reports
          </button>
        </div>
      </div>

      {/* Top Search & Filter Bar */}
      <div className="dataset-controls card animate-fade-in stagger-1">
        <div className="search-row">
          <div className="search-input-wrapper">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              className="form-input search-input"
              placeholder={
                dataMode === 'dataset'
                  ? 'Search by disease name, category, or symptom keywords...'
                  : 'Search by predicted disease, patient symptoms, or findings...'
              }
              value={searchQuery}
              onChange={(e) => handleFilterChange(setSearchQuery, e.target.value)}
            />
            {searchQuery && (
              <button className="clear-search-btn" onClick={() => handleFilterChange(setSearchQuery, '')}>
                ✕
              </button>
            )}
          </div>

          <div className="view-toggle-row">
            <button
              type="button"
              className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title="Grid View"
            >
              ⊞ Grid
            </button>
            <button
              type="button"
              className={`view-btn ${viewMode === 'table' ? 'active' : ''}`}
              onClick={() => setViewMode('table')}
              title="Table View"
            >
              ☰ Table
            </button>
          </div>
        </div>

        {/* Filter Panel */}
        <div className="filters-grid">
          {/* Severity Filter */}
          <div className="filter-group">
            <label className="filter-label">Severity Level</label>
            <select
              className="form-select"
              value={selectedSeverity}
              onChange={(e) => handleFilterChange(setSelectedSeverity, e.target.value)}
            >
              <option value="all">All Severities</option>
              <option value="Malignant">🚨 Malignant</option>
              <option value="Pre-cancerous">⚠️ Pre-cancerous</option>
              <option value="Benign">✅ Benign</option>
            </select>
          </div>

          {/* Disease Filter (Dataset Mode) */}
          {dataMode === 'dataset' && (
            <div className="filter-group">
              <label className="filter-label">Disease Condition</label>
              <select
                className="form-select"
                value={selectedDisease}
                onChange={(e) => handleFilterChange(setSelectedDisease, e.target.value)}
              >
                <option value="all">All Conditions ({filterOptions.diseases.length})</option>
                {filterOptions.diseases.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Body Location Filter (Dataset Mode) */}
          {dataMode === 'dataset' && (
            <div className="filter-group">
              <label className="filter-label">Body Location</label>
              <select
                className="form-select"
                value={selectedLocation}
                onChange={(e) => handleFilterChange(setSelectedLocation, e.target.value)}
              >
                <option value="all">All Body Sites</option>
                {filterOptions.body_locations.map((loc) => (
                  <option key={loc} value={loc}>
                    {loc}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Split Filter (Dataset Mode) */}
          {dataMode === 'dataset' && (
            <div className="filter-group">
              <label className="filter-label">Dataset Split</label>
              <select
                className="form-select"
                value={selectedSplit}
                onChange={(e) => handleFilterChange(setSelectedSplit, e.target.value)}
              >
                <option value="all">All Splits</option>
                <option value="train">Train (Training Set)</option>
                <option value="test">Test (Test Set)</option>
                <option value="validation">Validation Set</option>
              </select>
            </div>
          )}

          {/* Confidence Slider (History / Model Prediction Mode) */}
          {dataMode === 'history' && (
            <div className="filter-group slider-group">
              <div className="slider-label-row">
                <label className="filter-label">Min Model Confidence</label>
                <span className="slider-val">{minConfidence}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={minConfidence}
                onChange={(e) => handleFilterChange(setMinConfidence, Number(e.target.value))}
                className="range-slider"
              />
              <span className="filter-note">Applies to model predicted cases</span>
            </div>
          )}

          {/* Date Range Filters */}
          <div className="filter-group date-group">
            <label className="filter-label">
              {dataMode === 'dataset' ? 'Ingestion Date From' : 'Scan Date From'}
            </label>
            <input
              type="date"
              className="form-input date-input"
              value={dateFrom}
              onChange={(e) => handleFilterChange(setDateFrom, e.target.value)}
            />
          </div>

          <div className="filter-group date-group">
            <label className="filter-label">Date To</label>
            <input
              type="date"
              className="form-input date-input"
              value={dateTo}
              onChange={(e) => handleFilterChange(setDateTo, e.target.value)}
            />
          </div>

          {/* Reset Filters Button */}
          <div className="filter-group filter-actions">
            <button
              type="button"
              className="btn btn-secondary dataset-reset-btn"
              onClick={handleClearFilters}
              title="Reset all search queries and active filters"
            >
              🔄 Reset Filters
            </button>
          </div>
        </div>
      </div>

      {/* Content Area */}
      {loading ? (
        /* Loading Skeletons */
        <div className="dataset-skeleton-grid">
          {Array.from({ length: pageSize }).map((_, i) => (
            <div key={i} className="card skeleton-card">
              <div className="skeleton-thumb"></div>
              <div className="skeleton-line title"></div>
              <div className="skeleton-line meta"></div>
              <div className="skeleton-line desc"></div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="empty-state card">
          <div className="empty-icon">⚠️</div>
          <h3>Error Loading Dataset</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={fetchData} style={{ marginTop: '1rem' }}>
            Retry
          </button>
        </div>
      ) : records.length === 0 ? (
        /* Empty State */
        <div className="empty-state card animate-fade-in">
          <div className="empty-icon">🔎</div>
          <h3>No Records Found</h3>
          <p>
            No matches found for your current search or filter criteria. Try clearing filters or using broader search terms.
          </p>
          <button className="btn btn-primary" onClick={handleClearFilters} style={{ marginTop: '1rem' }}>
            Clear All Filters
          </button>
        </div>
      ) : viewMode === 'grid' ? (
        /* Grid View */
        <div className="dataset-records-grid animate-fade-in">
          {records.map((item, idx) => {
            const isHistory = dataMode === 'history';
            const diseaseName = isHistory ? item.predicted_disease : item.unified_disease_label;
            const severity = item.severity || 'Benign';
            const imageUrl = isHistory
              ? (item.image_ref ? `data:image/png;base64,${item.image_ref}` : '')
              : datasetAPI.getImageUrl(item.image_path);

            return (
              <div
                key={isHistory ? item.case_id : item.id || idx}
                className="dataset-card card"
                onClick={() => setSelectedRecord({ ...item, isHistory })}
              >
                <div className="dataset-card-thumb-wrapper">
                  {imageUrl ? (
                    <img
                      src={imageUrl}
                      alt={diseaseName}
                      className="dataset-card-thumb"
                      loading="lazy"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.nextSibling.style.display = 'flex';
                      }}
                    />
                  ) : null}
                  <div className="thumb-fallback" style={{ display: imageUrl ? 'none' : 'flex' }}>
                    🩺
                  </div>

                  <span className={`card-severity-badge ${getSeverityBadgeClass(severity)}`}>
                    {severity}
                  </span>

                  {!isHistory && (
                    <span className="card-split-badge">
                      {item.split || 'train'}
                    </span>
                  )}

                  {isHistory && (
                    <span className="card-confidence-badge">
                      {Math.round((item.confidence || 0) * 100)}% Conf
                    </span>
                  )}
                </div>

                <div className="dataset-card-body">
                  <h3 className="dataset-card-title">{diseaseName || 'Unspecified Lesion'}</h3>
                  
                  <div className="dataset-card-meta">
                    <span className="meta-item">
                      📍 {item.body_location || (isHistory ? 'Cutaneous Site' : 'General')}
                    </span>
                    <span className="meta-item">
                      📅 {isHistory ? item.created_at?.slice(0, 10) : item.date_added || '2024-2026'}
                    </span>
                  </div>

                  <p className="dataset-card-desc">
                    {item.symptoms_description || item.symptoms_text || 'No symptom description provided.'}
                  </p>

                  <div className="dataset-card-footer">
                    <span className="view-detail-btn">View Symptoms &amp; Details →</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Table View */
        <div className="card dataset-table-card animate-fade-in">
          <div className="table-container">
            <table className="dataset-table">
              <thead>
                <tr>
                  <th>Thumbnail</th>
                  <th>Disease / Condition</th>
                  <th>Severity</th>
                  {dataMode === 'dataset' ? <th>Category</th> : <th>Confidence</th>}
                  <th>Body Location</th>
                  <th>Symptoms &amp; Features</th>
                  <th>Date</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {records.map((item, idx) => {
                  const isHistory = dataMode === 'history';
                  const diseaseName = isHistory ? item.predicted_disease : item.unified_disease_label;
                  const severity = item.severity || 'Benign';
                  const imageUrl = isHistory
                    ? (item.image_ref ? `data:image/png;base64,${item.image_ref}` : '')
                    : datasetAPI.getImageUrl(item.image_path);

                  return (
                    <tr
                      key={isHistory ? item.case_id : item.id || idx}
                      onClick={() => setSelectedRecord({ ...item, isHistory })}
                      className="dataset-table-row"
                    >
                      <td className="table-thumb-cell">
                        <img
                          src={imageUrl}
                          alt={diseaseName}
                          className="table-thumb"
                          loading="lazy"
                          onError={(e) => {
                            e.target.style.display = 'none';
                          }}
                        />
                      </td>
                      <td>
                        <strong>{diseaseName}</strong>
                        {!isHistory && item.source && (
                          <span className="table-source-tag">{item.source}</span>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${getSeverityBadgeClass(severity)}`}>
                          {severity}
                        </span>
                      </td>
                      <td>
                        {isHistory ? (
                          <strong>{Math.round((item.confidence || 0) * 100)}%</strong>
                        ) : (
                          item.category || 'Dermatology Lesion'
                        )}
                      </td>
                      <td>{item.body_location || 'Cutaneous Site'}</td>
                      <td className="table-desc-cell">
                        <p className="table-desc-text">
                          {item.symptoms_description || item.symptoms_text || '—'}
                        </p>
                      </td>
                      <td>{isHistory ? item.created_at?.slice(0, 10) : item.date_added || '2024-2026'}</td>
                      <td>
                        <button className="btn btn-secondary btn-sm" onClick={() => setSelectedRecord({ ...item, isHistory })}>
                          View
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="pagination-bar animate-fade-in stagger-2">
          <div className="pagination-info">
            Showing {(page - 1) * pageSize + 1} – {Math.min(page * pageSize, totalCount)} of {totalCount} records
          </div>

          <div className="pagination-buttons">
            <button
              className="btn btn-secondary btn-sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              ← Previous
            </button>

            <span className="page-indicator">
              Page {page} of {totalPages}
            </span>

            <button
              className="btn btn-secondary btn-sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {/* Record Detail Modal */}
      {selectedRecord && (
        <div className="modal-backdrop animate-fade-in" onClick={() => setSelectedRecord(null)}>
          <div className="modal-content card" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close-btn" onClick={() => setSelectedRecord(null)}>
              ✕
            </button>

            <div className="modal-header">
              <span className={`badge ${getSeverityBadgeClass(selectedRecord.severity)}`}>
                {selectedRecord.severity}
              </span>
              {selectedRecord.split && (
                <span className="badge badge-secondary">Dataset Split: {selectedRecord.split}</span>
              )}
              {selectedRecord.isHistory && (
                <span className="badge badge-accent">
                  Case #{selectedRecord.case_id} • {Math.round((selectedRecord.confidence || 0) * 100)}% Confidence
                </span>
              )}
              <h2 className="modal-title">
                {selectedRecord.unified_disease_label || selectedRecord.predicted_disease}
              </h2>
            </div>

            <div className="modal-body-grid">
              <div className="modal-image-col">
                <img
                  src={
                    selectedRecord.isHistory
                      ? (selectedRecord.image_ref ? `data:image/png;base64,${selectedRecord.image_ref}` : '')
                      : datasetAPI.getImageUrl(selectedRecord.image_path)
                  }
                  alt={selectedRecord.unified_disease_label || selectedRecord.predicted_disease}
                  className="modal-full-image"
                />
                <p className="modal-image-caption">
                  {selectedRecord.isHistory
                    ? 'Patient Uploaded Lesion Image'
                    : `Reference Image from Training Archive (${selectedRecord.source || 'ISIC'})`}
                </p>
              </div>

              <div className="modal-info-col">
                <div className="modal-field">
                  <label className="modal-label">Classification Category</label>
                  <p className="modal-val">{selectedRecord.category || 'Dermatological Pathology'}</p>
                </div>

                <div className="modal-field">
                  <label className="modal-label">Typical / Reported Body Location</label>
                  <p className="modal-val">{selectedRecord.body_location || 'Cutaneous Surface'}</p>
                </div>

                <div className="modal-field">
                  <label className="modal-label">Symptoms &amp; Clinical Features</label>
                  <p className="modal-val modal-desc">
                    {selectedRecord.symptoms_description || selectedRecord.symptoms_text || 'No symptom description available.'}
                  </p>
                </div>

                {selectedRecord.isHistory && (
                  <div className="modal-field">
                    <label className="modal-label">Actions</label>
                    <Link to={`/history/${selectedRecord.case_id}`} className="btn btn-primary btn-sm">
                      View Full Clinical Report →
                    </Link>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="dataset-disclaimer">
        <Disclaimer />
      </div>
    </div>
  );
}
