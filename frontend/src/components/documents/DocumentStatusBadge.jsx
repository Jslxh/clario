import React from 'react';

/**
 * Status badge component for Document Lifecycle
 * Supports: UPLOADED, PROCESSING, READY, FAILED
 */
export const DocumentStatusBadge = ({ status }) => {
  const normalized = (status || '').toUpperCase();

  switch (normalized) {
    case 'READY':
      return (
        <span className="status-pill success" title="Vector indexed and ready for retrieval">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          READY
        </span>
      );

    case 'PROCESSING':
      return (
        <span className="status-pill pending" title="Parsing, chunking, and embedding in background">
          <span className="badge-spinner"></span>
          PROCESSING
        </span>
      );

    case 'FAILED':
      return (
        <span className="status-pill error" title="Processing error occurred">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          FAILED
        </span>
      );

    case 'UPLOADED':
    default:
      return (
        <span className="status-pill uploaded" title="Stored in storage; pending vector processing">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          UPLOADED
        </span>
      );
  }
};

export default DocumentStatusBadge;
