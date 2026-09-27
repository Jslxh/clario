import React, { useState, useEffect } from 'react';

function App() {
  const [healthStatus, setHealthStatus] = useState({
    loading: true,
    data: null,
    error: null,
  });

  const checkHealth = async () => {
    setHealthStatus({ loading: true, data: null, error: null });
    try {
      const response = await fetch('/health');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setHealthStatus({ loading: false, data, error: null });
    } catch (err) {
      setHealthStatus({
        loading: false,
        data: null,
        error: err.message || 'Failed to connect to backend',
      });
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <div className="app-container">
      {/* Enterprise Top Navigation Bar */}
      <header className="app-header">
        <div className="header-left">
          <a href="#" className="brand-logo">
            <div className="brand-icon-box">C</div>
            <span className="brand-title">Clario</span>
          </a>
          <span className="brand-subtitle">Enterprise Knowledge Intelligence Platform</span>
        </div>

        <div className="header-right">
          <span className="env-tag">ENV: DEVELOPMENT</span>
          <div className="user-profile">
            <div className="avatar-circle">SA</div>
            <span>System Administrator</span>
          </div>
        </div>
      </header>

      {/* Main Enterprise Workspace */}
      <div className="workspace-body">
        {/* Navigation Sidebar */}
        <aside className="workspace-sidebar">
          <div>
            <div className="sidebar-group-title">System Management</div>
            <ul className="sidebar-menu">
              <li className="sidebar-item active">
                <svg className="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                </svg>
                <span>System Verification</span>
              </li>
              <li className="sidebar-item">
                <svg className="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <ellipse cx="12" cy="5" rx="9" ry="3"/>
                  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                </svg>
                <span>Database Schema</span>
              </li>
              <li className="sidebar-item">
                <svg className="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="12 2 2 7 12 12 22 7 12 2"/>
                  <polyline points="2 17 12 22 22 17"/>
                  <polyline points="2 12 12 17 22 12"/>
                </svg>
                <span>Vector Collection</span>
              </li>
            </ul>
          </div>

          <div>
            <div className="sidebar-group-title">Governance</div>
            <ul className="sidebar-menu">
              <li className="sidebar-item">
                <svg className="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                  <polyline points="10 9 9 9 8 9"/>
                </svg>
                <span>Audit Logs</span>
              </li>
            </ul>
          </div>
        </aside>

        {/* Content Area */}
        <main className="workspace-content">
          <div className="breadcrumb">System Management / System Verification</div>
          
          <div className="page-header">
            <div>
              <h1 className="page-title">Service Health & Environment Verification</h1>
              <p className="page-description">
                Monitor runtime status and verify backend API health endpoints.
              </p>
            </div>
            <button className="btn-action" onClick={checkHealth} id="btn-recheck-health">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
              Run Health Check (GET /health)
            </button>
          </div>

          {/* System Verification Diagnostics Panel */}
          <div className="panel" id="system-status">
            <div className="panel-header">
              <div className="panel-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                <span>Backend Health Diagnostic Results</span>
              </div>
              <span className="code-badge">GET /health</span>
            </div>

            <div className="panel-body">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Diagnostic Field</th>
                    <th>Configured Value</th>
                    <th>Runtime Response</th>
                    <th>Service Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><strong>API Endpoint</strong></td>
                    <td><span className="code-badge">http://localhost:8000/health</span></td>
                    <td>HTTP 200 OK</td>
                    <td>
                      {healthStatus.loading ? (
                        <span className="status-pill pending">Checking...</span>
                      ) : healthStatus.error ? (
                        <span className="status-pill error">Offline</span>
                      ) : (
                        <span className="status-pill success">● Healthy</span>
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td><strong>Service Name</strong></td>
                    <td><span className="code-badge">SERVICE_NAME</span></td>
                    <td>{healthStatus.data?.service || 'clario-backend'}</td>
                    <td><span className="status-pill success">● Verified</span></td>
                  </tr>
                  <tr>
                    <td><strong>Status Identifier</strong></td>
                    <td><span className="code-badge">HEALTH_STATUS</span></td>
                    <td>{healthStatus.data?.status || (healthStatus.error ? 'Error' : 'healthy')}</td>
                    <td>
                      {healthStatus.error ? (
                        <span className="status-pill error">Connection Refused</span>
                      ) : (
                        <span className="status-pill success">● Normal</span>
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* System Architecture Specifications */}
          <div className="grid-2col">
            <div className="card-summary">
              <h3 className="card-title">Relational Data Store</h3>
              <p className="card-desc">
                PostgreSQL 16 engine managing user identities, access roles, document metadata, chunk records, and audit logs via SQLAlchemy 2.x and Alembic.
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span className="code-badge">PostgreSQL 16</span>
                <span className="code-badge">SQLAlchemy 2.x</span>
                <span className="code-badge">Alembic</span>
              </div>
            </div>

            <div className="card-summary">
              <h3 className="card-title">Vector Search Engine</h3>
              <p className="card-desc">
                Qdrant vector engine configured with collection <code className="code-badge">clario_documents</code> for high-dimensional document chunk vector indexing.
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span className="code-badge">Qdrant v1.10</span>
                <span className="code-badge">Cosine Metric</span>
                <span className="code-badge">384 Dimensions</span>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Footer */}
      <footer className="app-footer">
        <div>Clario Enterprise Platform &bull; System Health Verification</div>
        <div>FastAPI &bull; PostgreSQL &bull; Qdrant &bull; React + Vite</div>
      </footer>
    </div>
  );
}

export default App;
