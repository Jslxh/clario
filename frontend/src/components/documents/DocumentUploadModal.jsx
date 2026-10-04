import React, { useState, useRef, useEffect } from 'react';
import apiClient from '../../api/client';

const MAX_FILE_SIZE_BYTES = 52428800; // 50 MB
const ALLOWED_EXTENSIONS = ['pdf', 'docx', 'txt'];


const DEPARTMENTS = [
  'Engineering',
  'Operations',
  'Legal & Compliance',
  'Finance',
  'Human Resources',
  'Product & Design',
  'Security & IT',
  'Research',
];

export const DocumentUploadModal = ({ isOpen, onClose, onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [department, setDepartment] = useState('Engineering');
  const [accessLevel, setAccessLevel] = useState('internal');
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const fileInputRef = useRef(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen && !isUploading) {
        handleClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isUploading]);

  if (!isOpen) return null;

  const validateFile = (selectedFile) => {
    if (!selectedFile) return 'Please select a file to upload.';

    const ext = selectedFile.name.split('.').pop()?.toLowerCase();
    if (!ext || !ALLOWED_EXTENSIONS.includes(ext)) {
      return `Unsupported file format (.${ext || 'unknown'}). Allowed: PDF, DOCX, TXT.`;
    }

    if (selectedFile.size > MAX_FILE_SIZE_BYTES) {
      const sizeMB = (selectedFile.size / (1024 * 1024)).toFixed(1);
      return `File size (${sizeMB} MB) exceeds maximum allowed limit of 50 MB.`;
    }

    return null;
  };

  const handleFileSelection = (selectedFile) => {
    setErrorMessage('');
    const validationError = validateFile(selectedFile);
    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    setFile(selectedFile);
    // Autofill title if empty
    if (!title.trim()) {
      const nameWithoutExt = selectedFile.name.replace(/\.[^/.]+$/, '');
      setTitle(nameWithoutExt);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleClose = () => {
    if (isUploading) return;
    setFile(null);
    setTitle('');
    setDepartment('Engineering');
    setAccessLevel('internal');
    setErrorMessage('');
    onClose();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    const validationError = validateFile(file);
    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    setIsUploading(true);
    try {
      const newDoc = await apiClient.uploadDocument({
        file,
        title: title.trim() || file.name,
        department,
        access_level: accessLevel,
        document_type: file.name.split('.').pop()?.toLowerCase(),
      });

      handleClose();
      if (onUploadSuccess) {
        onUploadSuccess(newDoc);
      }
    } catch (err) {
      setErrorMessage(err.message || 'Failed to upload document. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  return (
    <div className="modal-backdrop" onClick={handleClose}>
      <div
        className="modal-container upload-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-modal-title"
      >
        <div className="modal-header">
          <div className="modal-title-box">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <h2 id="upload-modal-title" className="modal-title">
              Upload Enterprise Document
            </h2>
          </div>
          <button
            type="button"
            className="btn-modal-close"
            onClick={handleClose}
            disabled={isUploading}
            aria-label="Close dialog"
          >
            &times;
          </button>
        </div>

        {errorMessage && (
          <div className="auth-alert error" role="alert" style={{ margin: '1rem 1.5rem 0' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="modal-body">
          {/* Drag & Drop Zone */}
          <div
            className={`dropzone ${isDragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              style={{ display: 'none' }}
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  handleFileSelection(e.target.files[0]);
                }
              }}
              disabled={isUploading}
            />

            {file ? (
              <div className="dropzone-file-selected">
                <div className="file-icon-box">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                </div>
                <div className="file-selected-details">
                  <span className="file-name">{file.name}</span>
                  <span className="file-size-tag">{formatFileSize(file.size)} &bull; {file.name.split('.').pop()?.toUpperCase()}</span>
                </div>
                <button
                  type="button"
                  className="btn-replace-file"
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                  disabled={isUploading}
                >
                  Change File
                </button>
              </div>
            ) : (
              <div className="dropzone-prompt">
                <svg className="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
                <div className="dropzone-text">
                  <span className="prompt-title">Drag & drop document here, or <span className="browse-link">browse</span></span>
                  <span className="prompt-meta">Supports PDF, DOCX, TXT up to 50 MB</span>
                </div>
              </div>
            )}
          </div>

          {/* Document Title */}
          <div className="form-group" style={{ marginTop: '1.25rem' }}>
            <label htmlFor="upload-title" className="form-label">
              Document Display Title
            </label>
            <input
              id="upload-title"
              type="text"
              className="form-input"
              placeholder="e.g. Annual Travel Reimbursement Policy 2026"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isUploading}
            />
          </div>

          {/* Department & Access Level Grid */}
          <div className="form-row-2col">
            <div className="form-group">
              <label htmlFor="upload-department" className="form-label">
                Department Partition
              </label>
              <select
                id="upload-department"
                className="form-select"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                disabled={isUploading}
              >
                {DEPARTMENTS.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="upload-access-level" className="form-label">
                Security Access Level
              </label>
              <select
                id="upload-access-level"
                className="form-select"
                value={accessLevel}
                onChange={(e) => setAccessLevel(e.target.value)}
                disabled={isUploading}
              >
                <option value="internal">Internal (Default)</option>
                <option value="public">Public (All Users)</option>
                <option value="confidential">Confidential</option>
                <option value="restricted">Restricted (Admin Only)</option>
              </select>
            </div>
          </div>

          <div className="modal-actions-footer">
            <button
              type="button"
              className="btn-secondary"
              onClick={handleClose}
              disabled={isUploading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              id="btn-confirm-upload"
              disabled={!file || isUploading}
            >
              {isUploading ? (
                <>
                  <span className="btn-spinner"></span>
                  <span>Uploading File...</span>
                </>
              ) : (
                <>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  <span>Upload & Store</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default DocumentUploadModal;
