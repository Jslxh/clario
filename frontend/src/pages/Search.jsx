import React, { useState } from 'react';
import apiClient from '../api/client';
import { useAuth } from '../context/AuthContext';

export const Search = () => {
  const { user } = useAuth();
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [enableRerank, setEnableRerank] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  const userRole = (typeof user?.roles?.[0] === 'object' ? user?.roles?.[0]?.name : user?.roles?.[0]) || 'user';
  const userDept = user?.department || 'Engineering';

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setError('');
    try {
      const data = await apiClient.search({
        query: query.trim(),
        top_k: 8,
        mode,
        enable_rerank: enableRerank,
      });
      setResults(data);
    } catch (err) {
      setError(err.message || 'Failed to retrieve search results. Please try again.');
      setResults(null);
    } finally {
      setIsLoading(false);
    }
  };

  const getFormatBadge = (filename, docType) => {
    const ext = (docType || filename?.split('.').pop() || 'txt').toLowerCase();
    let label = ext.toUpperCase();
    let badgeClass = 'format-badge-default';

    if (ext === 'pdf') badgeClass = 'format-badge-pdf';
    else if (ext === 'docx' || ext === 'doc') badgeClass = 'format-badge-docx';
    else if (ext === 'txt') badgeClass = 'format-badge-txt';

    return <span className={`doc-format-badge ${badgeClass}`}>{label}</span>;
  };

  return (
    <div className="search-page-container">
      {/* Top Breadcrumb & User Context */}
      <div className="documents-top-bar">
        <div className="breadcrumb">
          <span>Enterprise Knowledge</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-active">Hybrid Search</span>
        </div>

        <div className="rbac-session-indicator">
          <span className="rbac-dot"></span>
          <span className="rbac-text">
            Search Boundary: <strong>{userDept}</strong> &bull;{' '}
            <span className={`role-badge-text ${userRole}`}>{userRole.toUpperCase()}</span>
          </span>
        </div>
      </div>

      {/* Page Header */}
      <div className="page-header">
        <div className="title-with-icon">
          <div className="title-icon-box" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <div>
            <h1 className="page-title">Enterprise Knowledge Search</h1>
            <p className="page-description">
              Retrieve authorized document chunks across Qdrant vector embeddings and BM25 keyword indices with neural cross-encoder reranking.
            </p>
          </div>
        </div>
      </div>

      {/* Search Input Box Card */}
      <div className="search-box-card">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-wrapper">
            <svg className="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              className="search-input"
              id="search-input-query"
              placeholder="Search policies, technical docs, guides, or specifications..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
            {query && (
              <button
                type="button"
                className="btn-clear-search"
                onClick={() => setQuery('')}
                aria-label="Clear search query"
              >
                &times;
              </button>
            )}
          </div>

          <button
            type="submit"
            className="btn-primary btn-submit-search"
            id="btn-search-submit"
            disabled={!query.trim() || isLoading}
          >
            {isLoading ? (
              <>
                <span className="btn-spinner"></span>
                <span>Searching...</span>
              </>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <span>Search Knowledge</span>
              </>
            )}
          </button>
        </form>

        {/* Search Options Toolbar */}
        <div className="search-toolbar">
          <div className="search-mode-selector">
            <span className="toolbar-label">Retrieval Mode:</span>
            <div className="segmented-control">
              <button
                type="button"
                className={`segment-btn ${mode === 'hybrid' ? 'active' : ''}`}
                onClick={() => setMode('hybrid')}
              >
                Hybrid (Vector + BM25)
              </button>
              <button
                type="button"
                className={`segment-btn ${mode === 'semantic' ? 'active' : ''}`}
                onClick={() => setMode('semantic')}
              >
                Semantic (Vector)
              </button>
              <button
                type="button"
                className={`segment-btn ${mode === 'bm25' ? 'active' : ''}`}
                onClick={() => setMode('bm25')}
              >
                BM25 (Keyword)
              </button>
            </div>
          </div>

          <label className="rerank-toggle-label">
            <input
              type="checkbox"
              id="toggle-rerank"
              checked={enableRerank}
              onChange={(e) => setEnableRerank(e.target.checked)}
            />
            <span>Cross-Encoder Neural Reranking</span>
          </label>
        </div>
      </div>

      {/* Initial Info Card (When no results yet) */}
      {!results && !isLoading && !error && (
        <div className="search-suggestions-card">
          <h3 className="suggestions-title">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            <span>Search Enterprise Documentation</span>
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: '1.5' }}>
            Enter any search terms above to query indexed document vectors in Qdrant Cloud and BM25 keywords in PostgreSQL. Results are filtered by your department ({userDept}) and role permissions.
          </p>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="auth-alert error" role="alert" style={{ marginTop: '1rem' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="search-loading-state">
          <div className="spinner"></div>
          <p className="loading-text">Searching authorized enterprise knowledge...</p>
          <span className="loading-subtext">Querying Qdrant Cloud vectors & BM25 indices</span>
        </div>
      )}

      {/* Results List */}
      {results && !isLoading && (
        <div className="search-results-section">
          {/* Results Summary Header */}
          <div className="results-header">
            <div className="results-count-title">
              Found <strong>{results.results?.length || 0}</strong> authorized chunk{results.results?.length === 1 ? '' : 's'} for{' '}
              <em className="query-highlight">"{results.query}"</em>
            </div>
            <div className="results-meta-tags">
              <span className="code-badge">Mode: {results.mode?.toUpperCase()}</span>
              {results.reranked && <span className="code-badge rerank-badge">Reranked</span>}
            </div>
          </div>

          {results.results?.length === 0 ? (
            <div className="table-empty-state" style={{ padding: '3rem 1rem' }}>
              <div className="empty-state-icon">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </div>
              <h3 className="empty-state-title">No Authorized Results Found</h3>
              <p className="empty-state-desc">
                I couldn't find sufficient authorized information matching your query within your department ({userDept}) security scope.
              </p>
            </div>
          ) : (
            <div className="search-results-list">
              {results.results.map((item, idx) => (
                <div key={item.chunk_id || idx} className="search-result-card">
                  <div className="result-card-header">
                    <div className="result-doc-info">
                      <span className="result-rank-num">#{idx + 1}</span>
                      {getFormatBadge(item.filename, item.document_type)}
                      <span className="result-filename">{item.filename}</span>
                    </div>

                    <div className="result-badges-row">
                      {item.department && (
                        <span className="dept-tag">
                          <span className="dept-tag-dot"></span>
                          <span>{item.department}</span>
                        </span>
                      )}
                      <span className={`access-pill ${item.access_level || 'internal'}`}>
                        <span className="access-dot"></span>
                        <span>{(item.access_level || 'internal').toUpperCase()}</span>
                      </span>
                      <span className="score-badge" title="Relevance ranking score">
                        Score: {item.score ? item.score.toFixed(3) : '—'}
                      </span>
                    </div>
                  </div>

                  {/* Canonical Content Snippet */}
                  <div className="result-content-box">
                    <p className="result-snippet">{item.content}</p>
                  </div>

                  {/* Card Footer Metadata */}
                  <div className="result-card-footer">
                    <div className="result-location-meta">
                      {item.page_number && (
                        <span className="meta-pill">Page {item.page_number}</span>
                      )}
                      {item.section && (
                        <span className="meta-pill">Section: {item.section}</span>
                      )}
                    </div>
                    <span className="chunk-id-tag">Chunk: {item.chunk_id?.slice(0, 8)}...</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Search;

