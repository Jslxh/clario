import React, { useState, useEffect } from 'react';
import apiClient from '../../api/client';
import { DocumentStatusBadge } from './DocumentStatusBadge';
import { ChunkViewer } from './ChunkViewer';

export const DocumentDetailsDrawer = ({
  isOpen,
  documentId,
  onClose,
  onProcess,
  onDelete,
}) => {
  const [doc, setDoc] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isProcessingLocal, setIsProcessingLocal] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const fetchDetails = async () => {
      if (!documentId || !isOpen) return;

      setIsLoading(true);
      setError('');
      try {
        const data = await apiClient.getDocument(documentId);
        if (isMounted) {
          setDoc(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'Failed to load document details.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchDetails();

    return () => {
      isMounted = false;
    };
  }, [documentId, isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleProcessClick = async () => {
    if (!doc?.id) return;
    setIsProcessingLocal(true);
    try {
      if (onProcess) {
        await onProcess(doc.id);
        // Refresh local details
        const updated = await apiClient.getDocument(doc.id);
        setDoc(updated);
      }
    } catch (err) {
      setError(err.message || 'Failed to trigger document processing.');
    } finally {
      setIsProcessingLocal(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const formatDate = (isoString) => {
    if (!isoString) return '—';
    try {
      return new Date(isoString).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside
        className="drawer-container"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Document Details"
      >
        {/* Drawer Header */}
        <div className="drawer-header">
          <div className="drawer-title-box">
            <h2 className="drawer-title">{doc?.title || 'Document Details'}</h2>
            <span className="drawer-subtitle">{doc?.filename || 'File details & chunk inspection'}</span>
          </div>
          <button
            type="button"
            className="btn-modal-close"
            onClick={onClose}
            aria-label="Close drawer"
          >
            &times;
          </button>
        </div>

        {/* Drawer Body */}
        <div className="drawer-body">
          {isLoading ? (
            <div className="drawer-loading-state">
              <div className="spinner"></div>
              <p>Retrieving document metadata...</p>
            </div>
          ) : error ? (
            <div className="auth-alert error" role="alert">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
            </div>
          ) : doc ? (
            <>
              {/* Status and Action Banner */}
              <div className="details-status-card">
                <div className="status-indicator-group">
                  <span className="meta-label">Current Lifecycle State</span>
                  <div style={{ marginTop: '0.25rem' }}>
                    <DocumentStatusBadge status={doc.status} />
                  </div>
                </div>

                {doc.status === 'UPLOADED' && (
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={handleProcessClick}
                    disabled={isProcessingLocal}
                    id="btn-drawer-process"
                  >
                    {isProcessingLocal ? (
                      <>
                        <span className="btn-spinner"></span>
                        <span>Dispatching Task...</span>
                      </>
                    ) : (
                      <>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="23 4 23 10 17 10" />
                          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                        </svg>
                        <span>Process Document</span>
                      </>
                    )}
                  </button>
                )}
              </div>

              {/* Document Metadata Table */}
              <div className="drawer-section">
                <h3 className="drawer-section-title">Document Metadata</h3>
                <table className="drawer-meta-table">
                  <tbody>
                    <tr>
                      <th>Document ID</th>
                      <td>
                        <span className="code-badge copyable">{doc.id}</span>
                      </td>
                    </tr>
                    <tr>
                      <th>Filename</th>
                      <td>{doc.filename}</td>
                    </tr>
                    <tr>
                      <th>File Size</th>
                      <td>{formatFileSize(doc.file_size)}</td>
                    </tr>
                    <tr>
                      <th>Format</th>
                      <td><span className="code-badge">{doc.document_type?.toUpperCase() || 'UNKNOWN'}</span></td>
                    </tr>
                    <tr>
                      <th>Department</th>
                      <td>
                        <span className="dept-tag">{doc.department || 'Unassigned'}</span>
                      </td>
                    </tr>
                    <tr>
                      <th>Access Level</th>
                      <td>
                        <span className={`access-pill ${doc.access_level}`}>
                          {doc.access_level ? doc.access_level.toUpperCase() : 'INTERNAL'}
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <th>Uploaded By</th>
                      <td>
                        <span className="code-badge">{doc.uploaded_by || 'System Admin'}</span>
                      </td>
                    </tr>
                    <tr>
                      <th>Upload Date</th>
                      <td>{formatDate(doc.created_at)}</td>
                    </tr>
                    <tr>
                      <th>Last Updated</th>
                      <td>{formatDate(doc.updated_at)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Chunk Inspection Section */}
              <div className="drawer-section">
                <h3 className="drawer-section-title">Vector Chunks & Embeddings</h3>
                <ChunkViewer
                  chunkCount={doc.chunk_count || 0}
                  status={doc.status}
                />
              </div>
            </>
          ) : null}
        </div>

        {/* Drawer Footer Actions */}
        <div className="drawer-footer">
          {doc && (
            <button
              type="button"
              className="btn-danger-outline"
              onClick={() => onDelete(doc)}
              id="btn-drawer-delete"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              <span>Delete Document</span>
            </button>
          )}

          <button
            type="button"
            className="btn-secondary"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </aside>
    </div>
  );
};

export default DocumentDetailsDrawer;
