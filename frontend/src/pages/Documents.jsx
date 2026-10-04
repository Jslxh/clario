import React, { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '../api/client';
import { DocumentFilters } from '../components/documents/DocumentFilters';
import { DocumentTable } from '../components/documents/DocumentTable';
import { DocumentUploadModal } from '../components/documents/DocumentUploadModal';
import { DocumentDetailsDrawer } from '../components/documents/DocumentDetailsDrawer';

const PAGE_SIZE = 10;
const MAX_POLL_CYCLES = 25; // Stop polling after ~75 seconds

export const Documents = () => {
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

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification((curr) => (curr?.message === message ? null : curr));
    }, 4000);
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
    // Check if any visible document is in PROCESSING status
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
  const handleProcessDocument = async (documentId) => {
    try {
      // Optimistically update document status to PROCESSING
      setDocuments((prev) =>
        prev.map((d) => (d.id === documentId ? { ...d, status: 'PROCESSING' } : d))
      );
      setProcessingDocIds((prev) => new Set(prev).add(documentId));

      await apiClient.processDocument(documentId);
      showNotification('Document submitted for asynchronous ingestion and vector indexing.', 'info');
      // Reset poll counter so polling triggers immediately
      pollCountRef.current = 0;
    } catch (err) {
      showNotification(`Failed to process document: ${err.message}`, 'error');
      // Revert status on failure
      loadDocuments(true);
    }
  };

  // Action: Delete document
  const handleDeleteDocument = async (documentId) => {
    await apiClient.deleteDocument(documentId);
    showNotification('Document, chunks, and vector index entries permanently deleted.');

    if (selectedDocId === documentId) {
      setSelectedDocId(null);
    }

    // If deleting last item on page > 1, step back
    if (documents.length === 1 && page > 1) {
      setPage((p) => p - 1);
    } else {
      loadDocuments(false);
    }
  };

  // Action: Upload success
  const handleUploadSuccess = (newDoc) => {
    showNotification(`Document "${newDoc.title || newDoc.filename}" uploaded successfully.`);
    setPage(1);
    loadDocuments(false);
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

  return (
    <div className="documents-page-container">
      {/* Page Header */}
      <div className="breadcrumb">Enterprise Knowledge Intelligence / Document Management</div>

      <div className="page-header">
        <div>
          <h1 className="page-title">Enterprise Documents</h1>
          <p className="page-description">
            Upload, inspect, and process corporate unstructured knowledge files for semantic retrieval.
          </p>
        </div>
      </div>

      {/* Notification Toast Banner */}
      {notification && (
        <div className={`auth-alert ${notification.type}`} role="status">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {notification.type === 'error' ? (
              <>
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </>
            ) : (
              <polyline points="20 6 9 17 4 12" />
            )}
          </svg>
          <span>{notification.message}</span>
        </div>
      )}

      {/* Global API Error */}
      {error && (
        <div className="auth-alert error" role="alert">
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
        isLoading={isLoading}
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
          <span className="code-badge">
            {documents.length} visible on page {page}
          </span>
        </div>

        <div className="panel-body" style={{ padding: 0 }}>
          <DocumentTable
            documents={documents}
            isLoading={isLoading}
            onSelectDocument={(doc) => setSelectedDocId(doc.id)}
            onProcessDocument={handleProcessDocument}
            onDeleteDocument={handleDeleteDocument}
            processingDocIds={processingDocIds}
          />
        </div>

        {/* Pagination Controls */}
        <div className="pagination-bar">
          <div className="pagination-info">
            Showing page <strong>{page}</strong> {hasMore ? '(More available)' : '(End of results)'}
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

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />

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
      />
    </div>
  );
};

export default Documents;
