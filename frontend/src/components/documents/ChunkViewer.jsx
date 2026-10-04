import React from 'react';

/**
 * ChunkViewer displays either individual chunk items (when provided)
 * or detailed chunk metadata/readiness state when the backend provides chunk_count.
 */
export const ChunkViewer = ({ chunkCount = 0, chunks = null, status = 'UPLOADED' }) => {
  const isReady = status?.toUpperCase() === 'READY';
  const isProcessing = status?.toUpperCase() === 'PROCESSING';
  const isUploaded = status?.toUpperCase() === 'UPLOADED';
  const isFailed = status?.toUpperCase() === 'FAILED';

  // If the backend provides full chunk records (or when future chunk endpoint is added)
  if (chunks && Array.isArray(chunks) && chunks.length > 0) {
    return (
      <div className="chunk-viewer-container">
        <div className="chunk-viewer-header">
          <div className="chunk-count-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
            <span>{chunks.length} Extracted Chunks</span>
          </div>
        </div>

        <div className="chunk-list">
          {chunks.map((chunk, idx) => (
            <div key={chunk.id || idx} className="chunk-card">
              <div className="chunk-card-meta">
                <span className="chunk-index-tag">Chunk #{chunk.chunk_index !== undefined ? chunk.chunk_index + 1 : idx + 1}</span>
                <span className="chunk-page-tag">Page: {chunk.page_number || '1'}</span>
                <span className="chunk-section-tag">Section: {chunk.section || 'General'}</span>
              </div>
              <div className="chunk-content-preview">
                <pre>{chunk.content}</pre>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // When backend provides chunk_count in DocumentDetailRead (current backend state)
  return (
    <div className="chunk-viewer-container">
      <div className="chunk-meta-card">
        <div className="chunk-stat-row">
          <div className="chunk-stat-item">
            <span className="stat-label">Persisted Chunks</span>
            <span className="stat-value">{isReady ? chunkCount : 0}</span>
          </div>
          <div className="chunk-stat-item">
            <span className="stat-label">Vector Collection</span>
            <span className="code-badge">clario_documents</span>
          </div>
          <div className="chunk-stat-item">
            <span className="stat-label">Indexing Engine</span>
            <span className="code-badge">Qdrant + BM25</span>
          </div>
        </div>

        {isReady && chunkCount > 0 && (
          <div className="chunk-notice ready">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <div>
              <strong>{chunkCount} Atomic Chunks Indexed</strong>
              <p>
                Document text was chunked into 500-token segments with 75-token overlap, embedded with BAAI/bge-small-en-v1.5, and indexed into Qdrant for semantic search.
              </p>
              <span className="dependency-note">
                Note: Individual chunk content inspection payload is scheduled for a future backend endpoint.
              </span>
            </div>
          </div>
        )}

        {isProcessing && (
          <div className="chunk-notice processing">
            <span className="badge-spinner"></span>
            <div>
              <strong>Background Ingestion in Progress</strong>
              <p>Extracting text, calculating token boundaries, and generating embeddings...</p>
            </div>
          </div>
        )}

        {isUploaded && (
          <div className="chunk-notice idle">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div>
              <strong>Awaiting Processing</strong>
              <p>Document file is safely stored. Click <strong>[Process Document]</strong> to generate chunks and index vectors into the knowledge base.</p>
            </div>
          </div>
        )}

        {isFailed && (
          <div className="chunk-notice error">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div>
              <strong>Chunk Extraction Failed</strong>
              <p>Processing failed. Please check the document format or re-upload the file.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChunkViewer;
