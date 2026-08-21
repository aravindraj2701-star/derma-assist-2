import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { historyAPI } from '../api/api';
import './GlobalSearchBar.css';

export default function GlobalSearchBar() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  // Keyboard shortcut: Ctrl+K or Cmd+K
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      } else if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Autofocus input when modal opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  }, [isOpen]);

  // Debounced search query
  useEffect(() => {
    if (!query.trim()) {
      setResults(null);
      setLoading(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await historyAPI.globalSearch(query.trim());
        setResults(res.data);
      } catch (err) {
        console.error('Global search error:', err);
      } finally {
        setLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (url) => {
    setIsOpen(false);
    setQuery('');
    navigate(url);
  };

  const totalCount = results?.total_results || 0;

  return (
    <>
      {/* Compact Navbar Search Trigger Button */}
      <button
        type="button"
        className="navbar-search-trigger"
        onClick={() => setIsOpen(true)}
        title="Quick Search (Ctrl + K)"
        aria-label="Open Search Command Palette"
      >
        <span className="search-trigger-icon">🔍</span>
        <span className="search-trigger-text">Search...</span>
        <kbd className="search-trigger-kbd">Ctrl K</kbd>
      </button>

      {/* Spotlight Command Modal Overlay */}
      {isOpen && (
        <div className="spotlight-overlay" onClick={() => setIsOpen(false)}>
          <div className="spotlight-card" onClick={(e) => e.stopPropagation()}>
            {/* Header Search Input */}
            <div className="spotlight-header">
              <span className="spotlight-search-icon">🔍</span>
              <input
                ref={inputRef}
                type="text"
                className="spotlight-input"
                placeholder="Type a case #ID, disease name, symptom, or action..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Universal Search Query"
              />
              <button
                type="button"
                className="spotlight-close-btn"
                onClick={() => setIsOpen(false)}
              >
                ESC
              </button>
            </div>

            {/* Results Body */}
            <div className="spotlight-results">
              {!query.trim() ? (
                <div className="spotlight-empty-state">
                  <div style={{ fontSize: '1.75rem', marginBottom: '8px' }}>💡</div>
                  <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>
                    Quick Spotlight Search
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                    Search across all your screening cases, 20 pathology reference diseases, and navigation actions.
                  </div>
                </div>
              ) : loading ? (
                <div className="spotlight-loading-state">
                  <div className="spinner-small" style={{ width: '18px', height: '18px' }}></div>
                  <span>Searching clinical database...</span>
                </div>
              ) : totalCount === 0 ? (
                <div className="spotlight-empty-state">
                  <div style={{ fontSize: '1.75rem', marginBottom: '8px' }}>🔍</div>
                  <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>
                    No results for &ldquo;{query}&rdquo;
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                    Try searching for a disease (Melanoma, Eczema), case number (#1), or symptom keyword.
                  </div>
                </div>
              ) : (
                <>
                  {/* Clinical Cases */}
                  {results?.cases && results.cases.length > 0 && (
                    <div>
                      <div className="spotlight-section-title">
                        <span>📋</span> Clinical Cases ({results.cases.length})
                      </div>
                      {results.cases.map((c) => (
                        <div
                          key={c.id}
                          className="spotlight-item"
                          onClick={() => handleSelect(c.url)}
                        >
                          <div className="spotlight-item-icon">{c.icon}</div>
                          <div className="spotlight-item-content">
                            <div className="spotlight-item-title">{c.title}</div>
                            <div className="spotlight-item-subtitle">{c.subtitle} • {c.symptoms}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Disease Profiles */}
                  {results?.diseases && results.diseases.length > 0 && (
                    <div>
                      <div className="spotlight-section-title">
                        <span>📖</span> Dermatology Database ({results.diseases.length})
                      </div>
                      {results.diseases.map((d) => (
                        <div
                          key={d.id}
                          className="spotlight-item"
                          onClick={() => handleSelect(d.url)}
                        >
                          <div className="spotlight-item-icon">{d.icon}</div>
                          <div className="spotlight-item-content">
                            <div className="spotlight-item-title">{d.title}</div>
                            <div className="spotlight-item-subtitle">{d.subtitle}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Quick Actions */}
                  {results?.actions && results.actions.length > 0 && (
                    <div>
                      <div className="spotlight-section-title">
                        <span>⚡</span> Quick Actions ({results.actions.length})
                      </div>
                      {results.actions.map((a, idx) => (
                        <div
                          key={idx}
                          className="spotlight-item"
                          onClick={() => handleSelect(a.url)}
                        >
                          <div className="spotlight-item-icon">{a.icon}</div>
                          <div className="spotlight-item-content">
                            <div className="spotlight-item-title">{a.title}</div>
                            <div className="spotlight-item-subtitle">{a.subtitle}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Footer with Shortcuts */}
            <div className="spotlight-footer">
              <div className="spotlight-footer-shortcuts">
                <span className="spotlight-shortcut-badge">
                  <kbd style={{ background: '#e2e8f0', padding: '1px 4px', borderRadius: '3px', fontSize: '0.65rem' }}>↵</kbd> Select
                </span>
                <span className="spotlight-shortcut-badge">
                  <kbd style={{ background: '#e2e8f0', padding: '1px 4px', borderRadius: '3px', fontSize: '0.65rem' }}>ESC</kbd> Close
                </span>
              </div>
              <span>{totalCount > 0 ? `${totalCount} results` : 'Spotlight Search'}</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
