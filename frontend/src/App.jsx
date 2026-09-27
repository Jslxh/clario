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
    <>
      <header className="app-header">
        <div className="nav-container">
          <a href="#" className="brand">
            <div className="brand-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <span className="brand-name">Clario</span>
            <span className="brand-tag">Phase 1 Foundation</span>
          </a>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span className="badge ready">System Status: Online</span>
          </div>
        </div>
      </header>

      <main className="main-content">
        <section className="hero-section">
          <h1 className="hero-title">
            Enterprise Knowledge <br />
            <span className="text-gradient">Intelligence Platform</span>
          </h1>
          <p className="hero-subtitle">
            Secure, scalable, high-performance RAG architecture empowering enterprise teams to query authorized enterprise documents with accuracy.
          </p>
        </section>

        {/* System Health Check Panel */}
        <section className="glass-panel status-card" id="system-status">
          <div className="status-header">
            <div className="status-title-group">
              <div className="status-indicator-dot"></div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Backend Verification</h2>
            </div>
            <button className="btn-primary" onClick={checkHealth} id="btn-recheck-health">
              Re-check GET /health
            </button>
          </div>

          <div className="status-grid">
            <div className="status-item">
              <div className="status-label">API Status</div>
              <div className="status-value">
                {healthStatus.loading ? (
                  <span style={{ color: 'var(--text-muted)' }}>Checking...</span>
                ) : healthStatus.error ? (
                  <span style={{ color: 'var(--status-error)' }}>Offline / Pending</span>
                ) : (
                  <span style={{ color: 'var(--status-success)' }}>
                    ● {healthStatus.data?.status || 'healthy'}
                  </span>
                )}
              </div>
            </div>

            <div className="status-item">
              <div className="status-label">Service Identifier</div>
              <div className="status-value">
                {healthStatus.data?.service || 'clario-backend'}
              </div>
            </div>

            <div className="status-item">
              <div className="status-label">Target Infrastructure</div>
              <div className="status-value" style={{ fontSize: '0.9rem' }}>
                FastAPI + PostgreSQL + Qdrant
              </div>
            </div>
          </div>
        </section>

        {/* Platform Architecture & Roadmap */}
        <section>
          <h2 className="section-heading">Platform Architecture</h2>
          <div className="feature-grid">
            <div className="glass-panel feature-card">
              <div className="feature-icon">⚡</div>
              <h3 className="feature-title">FastAPI Backend Core</h3>
              <p className="feature-desc">
                High-throughput Python application framework providing modular RESTful APIs, Pydantic validation, and scalable service architecture.
              </p>
              <span className="badge ready">Phase 1 Configured</span>
            </div>

            <div className="glass-panel feature-card">
              <div className="feature-icon">🗄️</div>
              <h3 className="feature-title">Relational & Vector Data Layer</h3>
              <p className="feature-desc">
                Containerized PostgreSQL for structured metadata & access management alongside Qdrant vector database for high-dimensional embeddings.
              </p>
              <span className="badge ready">Docker Compose Ready</span>
            </div>

            <div className="glass-panel feature-card">
              <div className="feature-icon">🧠</div>
              <h3 className="feature-title">RAG & Retrieval Pipeline</h3>
              <p className="feature-desc">
                LangChain and Sentence Transformers integration for document chunking, embedding generation, and contextual answer synthesis.
              </p>
              <span className="badge roadmap">Phase 2+ Roadmap</span>
            </div>
          </div>
        </section>
      </main>

      <footer className="app-footer">
        Clario Enterprise Knowledge Intelligence Platform &bull; Phase 1 Infrastructure Foundation
      </footer>
    </>
  );
}

export default App;
