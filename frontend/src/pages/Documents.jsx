import React, { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useTask } from '../context/TaskContext';
import { DocumentFilters } from '../components/documents/DocumentFilters';
import { DocumentTable } from '../components/documents/DocumentTable';
import { DocumentUploadModal } from '../components/documents/DocumentUploadModal';
import { DocumentDetailsDrawer } from '../components/documents/DocumentDetailsDrawer';

const PAGE_SIZE = 10;
const MAX_POLL_CYCLES = 25; // Stop polling after ~75 seconds

export const Documents = () => {
  const { user } = useAuth();
  const { processingDocIds: globalProcessingDocIds, dispatchDocumentProcess } = useTask();
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [notification, setNotification] = useState(null);

  // Filters & Pagination
  const [filters, setFilters] = useState({});
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  // Modals & Drawers
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState(null);

  // Set of doc IDs currently undergoing background processing
  const [processingDocIds, setProcessingDocIds] = useState(new Set());
  const pollCountRef = useRef(0);
  const pollTimeoutRef = useRef(null);

  // Extract user role cleanly
  const userRoles = user?.roles
    ? user.roles.map((r) => (typeof r === 'object' ? r.name : r))
    : ['user'];
  const userRole = userRoles[0] || 'user';
  const isAdmin = userRoles.includes('admin');
  const userDept = user?.department || 'Engineering';

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification((curr) => (curr?.message === message ? null : curr));
    }, 4500);
  };

  const loadDocuments = useCallback(
    async (isBackground = false) => {
      if (!isBackground) {
        setIsLoading(true);
        setError('');
      }

      try {
        const skip = (page - 1) * PAGE_SIZE;
        const data = await apiClient.getDocuments({
          skip,
          limit: PAGE_SIZE,
          department: filters.department,
          status: filters.status,
          access_level: filters.access_level,
        });

        const list = Array.isArray(data) ? data : [];
        setDocuments(list);
        setHasMore(list.length === PAGE_SIZE);

        // Update processingDocIds tracking based on retrieved documents
        setProcessingDocIds((prev) => {
          const updated = new Set(prev);
          list.forEach((doc) => {
            if (doc.status === 'PROCESSING') {
              updated.add(doc.id);
            } else if (doc.status === 'READY' || doc.status === 'FAILED') {
              updated.delete(doc.id);
            }
          });
          return updated;
        });
      } catch (err) {
        if (!isBackground) {
          setError(err.message || 'Failed to load documents from backend.');
        }
      } finally {
        if (!isBackground) {
          setIsLoading(false);
        }
      }
    },
    [page, filters]
  );

  // Initial and reactive load on page/filter change
  useEffect(() => {
    loadDocuments(false);
  }, [loadDocuments]);

  // Lightweight polling for asynchronous processing
  useEffect(() => {
    const hasActiveProcessing =
      documents.some((d) => d.status === 'PROCESSING') || processingDocIds.size > 0;

    if (!hasActiveProcessing) {
      pollCountRef.current = 0;
      clearTimeout(pollTimeoutRef.current);
      return;
    }

    if (pollCountRef.current >= MAX_POLL_CYCLES) {
      console.warn('Max polling cycles reached for background document processing.');
      return;
    }

    pollTimeoutRef.current = setTimeout(() => {
      pollCountRef.current += 1;
      loadDocuments(true);
    }, 3000);

    return () => {
      clearTimeout(pollTimeoutRef.current);
    };
  }, [documents, processingDocIds, loadDocuments]);

  // Action: Trigger document processing
  const handleProcessDocument = (documentId, docTitle = null) => {
    const targetDoc = documents.find((d) => d.id === documentId);
    const title = docTitle || targetDoc?.title || targetDoc?.filename || 'Document';
    setDocuments((prev) =>
      prev.map((d) => (d.id === documentId ? { ...d, status: 'PROCESSING' } : d))
    );
    dispatchDocumentProcess(documentId, title);
    showNotification(`Document ingestion dispatched for "${title}". Running in async worker.`, 'info');
  };

  // Action: Delete document
  const handleDeleteDocument = async (documentId) => {
    await apiClient.deleteDocument(documentId);
    showNotification('Document, vector embeddings, and chunks permanently removed from repository.');

    if (selectedDocId === documentId) {
      setSelectedDocId(null);
    }

    if (documents.length === 1 && page > 1) {
      setPage((p) => p - 1);
    } else {
      loadDocuments(false);
    }
  };

  // Action: Upload success with auto-process dispatch
  const handleUploadSuccess = (newDoc, shouldAutoProcess = true) => {
    showNotification(`Document "${newDoc.title || newDoc.filename}" uploaded successfully to repository.`);
    setPage(1);
    loadDocuments(false);

    if (shouldAutoProcess && isAdmin && newDoc?.id) {
      handleProcessDocument(newDoc.id, newDoc.title || newDoc.filename);
    }
  };

  // Action: Batch process all pending documents in single click
  const handleProcessAllPending = () => {
    const effectiveProcessing = new Set([...processingDocIds, ...globalProcessingDocIds]);
    const pendingDocs = documents.filter(
      (d) => d.status === 'UPLOADED' && !effectiveProcessing.has(d.id)
    );

    if (pendingDocs.length === 0) {
      showNotification('No pending uploaded documents to process.', 'info');
      return;
    }

    pendingDocs.forEach((doc) => {
      handleProcessDocument(doc.id, doc.title || doc.filename);
    });
    showNotification(`Dispatched batch vector processing for ${pendingDocs.length} pending document(s).`, 'info');
  };

  // Action: Reset filters
  const handleResetFilters = () => {
    setFilters({});
    setPage(1);
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    setPage(1);
  };

  // Summary Metrics Calculation
  const effectiveProcessingSet = new Set([...processingDocIds, ...globalProcessingDocIds]);
  const pendingDocsCount = documents.filter((d) => d.status === 'UPLOADED' && !effectiveProcessingSet.has(d.id)).length;
  const readyCount = documents.filter((d) => d.status === 'READY').length;
  const processingCount = documents.filter((d) => d.status === 'PROCESSING' || effectiveProcessingSet.has(d.id)).length;
  const totalChunks = documents.reduce((sum, d) => sum + (d.chunk_count || 0), 0);

  return (
    <div className="documents-page-container">
      {/* Top Breadcrumb & RBAC Indicator */}
      <div className="documents-top-bar">
        <div className="breadcrumb">
          <span>Enterprise Knowledge Intelligence</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-active">Document Management</span>
        </div>

        <div className="rbac-session-indicator">
          <span className="rbac-dot"></span>
          <span className="rbac-text">
            Session: <strong>{user?.name || userRole.toUpperCase()}</strong> ({userDept}) &bull;{' '}
            <span className={`role-badge-text ${userRole}`}>{userRole.toUpperCase()}</span>
          </span>
        </div>
      </div>

      {/* Main Page Title Header */}
      <div className="page-header documents-header">
        <div className="header-text-group">
          <div className="title-with-icon">
            <div className="title-icon-box">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
            </div>
            <div>
              <h1 className="page-title">Enterprise Knowledge Repository</h1>
              <p className="page-description">
                Upload, manage, and process corporate unstructured documents with automated chunking, hybrid BM25 + Qdrant vector indexing, and department-level RBAC partitioning.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Repository Metrics Bar */}
      <div className="repo-metrics-grid">
        <div className="repo-metric-card">
          <div className="metric-icon-box blue">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <div className="metric-details">
            <span className="metric-label">Page Documents</span>
            <span className="metric-val">{documents.length}</span>
            <span className="metric-sub">Page {page} view</span>
          </div>
        </div>

        <div className="repo-metric-card">
          <div className="metric-icon-box emerald">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <div className="metric-details">
            <span className="metric-label">Vector Ready</span>
            <span className="metric-val emerald">{readyCount}</span>
            <span className="metric-sub">Searchable in Qdrant</span>
          </div>
        </div>

        <div className="repo-metric-card">
          <div className="metric-icon-box purple">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
          </div>
          <div className="metric-details">
            <span className="metric-label">Indexed Chunks</span>
            <span className="metric-val purple">{totalChunks}</span>
            <span className="metric-sub">384-dim BGE Small</span>
          </div>
        </div>

        <div className="repo-metric-card">
          <div className={`metric-icon-box ${processingCount > 0 ? 'amber spinning-icon' : 'gray'}`}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10" />
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
            </svg>
          </div>
          <div className="metric-details">
            <span className="metric-label">Ingestion Pipeline</span>
            <span className={`metric-val ${processingCount > 0 ? 'amber' : ''}`}>{processingCount} Active</span>
            <span className="metric-sub">{processingCount > 0 ? 'Auto-polling enabled' : 'Pipeline idle'}</span>
          </div>
        </div>
      </div>

      {/* Floating Notification Toast */}
      {notification && (
        <div className={`toast-notification ${notification.type}`} role="status">
          <div className="toast-icon">
            {notification.type === 'error' ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            ) : notification.type === 'info' ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12" y2="8" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            )}
          </div>
          <span className="toast-message">{notification.message}</span>
          <button
            type="button"
            className="toast-close"
            onClick={() => setNotification(null)}
            aria-label="Dismiss notification"
          >
            &times;
          </button>
        </div>
      )}

      {/* Global Error Banner */}
      {error && (
        <div className="auth-alert error" role="alert" style={{ marginBottom: '1.25rem' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {/* Filters & Actions Bar */}
      <DocumentFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onResetFilters={handleResetFilters}
        onRefresh={() => loadDocuments(false)}
        onOpenUpload={() => setIsUploadOpen(true)}
        onProcessAll={handleProcessAllPending}
        pendingCount={pendingDocsCount}
        isLoading={isLoading}
        isAdmin={isAdmin}
      />

      {/* Document Table Panel */}
      <div className="panel document-table-panel">
        <div className="panel-header">
          <div className="panel-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span>Managed Repository Documents</span>
          </div>
          <div className="table-header-meta">
            <span className="table-badge">
              {documents.length} document{documents.length === 1 ? '' : 's'} on page {page}
            </span>
          </div>
        </div>

        <div className="panel-body" style={{ padding: 0 }}>
          <DocumentTable
            documents={documents}
            isLoading={isLoading}
            onSelectDocument={(doc) => setSelectedDocId(doc.id)}
            onProcessDocument={handleProcessDocument}
            onDeleteDocument={handleDeleteDocument}
            processingDocIds={new Set([...processingDocIds, ...globalProcessingDocIds])}
            isAdmin={isAdmin}
          />
        </div>

        {/* Pagination Controls */}
        <div className="pagination-bar">
          <div className="pagination-info">
            Showing page <strong className="page-highlight">{page}</strong> &bull;{' '}
            <span className="pagination-subtext">{hasMore ? 'Additional pages available' : 'End of repository list'}</span>
          </div>

          <div className="pagination-actions">
            <button
              type="button"
              className="btn-pagination"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || isLoading}
              id="btn-pagination-prev"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" />
              </svg>
              <span>Previous</span>
            </button>

            <span className="page-number-pill">{page}</span>

            <button
              type="button"
              className="btn-pagination"
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasMore || isLoading}
              id="btn-pagination-next"
            >
              <span>Next</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Upload Modal (Admin only) */}
      {isAdmin && (
        <DocumentUploadModal
          isOpen={isUploadOpen}
          onClose={() => setIsUploadOpen(false)}
          onUploadSuccess={handleUploadSuccess}
        />
      )}

      {/* Document Details & Chunk Inspection Drawer */}
      <DocumentDetailsDrawer
        isOpen={Boolean(selectedDocId)}
        documentId={selectedDocId}
        onClose={() => setSelectedDocId(null)}
        onProcess={handleProcessDocument}
        onDelete={(doc) => {
          setSelectedDocId(null);
          handleDeleteDocument(doc.id);
        }}
        isAdmin={isAdmin}
      />
    </div>
  );
};

export default Documents;
