import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import apiClient from '../api/client';

export const Dashboard = () => {
  const { user, token, logout } = useAuth();
  const [healthStatus, setHealthStatus] = useState({
    loading: true,
    data: null,
    error: null,
  });
  const [profileRefresh, setProfileRefresh] = useState({
    loading: false,
    data: null,
    error: null,
  });
  const [activeTab, setActiveTab] = useState('overview');

  const checkHealth = async () => {
    setHealthStatus({ loading: true, data: null, error: null });
    try {
      const data = await apiClient.checkHealth();
      setHealthStatus({ loading: false, data, error: null });
    } catch (err) {
      setHealthStatus({
        loading: false,
        data: null,
        error: err.message || 'Failed to connect to backend',
      });
    }
  };

  const recheckProfile = async () => {
    setProfileRefresh({ loading: true, data: null, error: null });
    try {
      const data = await apiClient.getMe();
      setProfileRefresh({ loading: false, data, error: null });
    } catch (err) {
      setProfileRefresh({
        loading: false,
        data: null,
        error: err.message || 'Failed to verify user session',
      });
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  const userInitials = user?.name
    ? user.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : 'U';

  const userRoles = user?.roles ? user.roles.map((r) => (typeof r === 'object' ? r.name : r)) : ['user'];

  return (
    <div className="app-container">
      {/* Enterprise Top Navigation Bar */}
      <header className="app-header">
        <div className="header-left">
          <a href="#" className="brand-logo">
            <div className="brand-icon-box">C</div>
            <span className="brand-title">Clario</span>
          </a>
          <span className="brand-subtitle">Enterprise Knowledge Platform</span>
        </div>

        <div className="header-right">
          <span className="env-tag">ENV: {import.meta.env.MODE?.toUpperCase() || 'DEVELOPMENT'}</span>

          <div className="user-profile-badge">
            <div className="avatar-circle">{userInitials}</div>
            <div className="user-info-text">
              <span className="user-display-name">{user?.name || 'Authorized User'}</span>
              <span className="user-display-dept">{user?.department || 'Enterprise'}</span>
            </div>
          </div>

          <button
            onClick={logout}
            className="btn-logout"
            id="btn-logout"
            title="Terminate session and sign out"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      {/* Main Enterprise Workspace */}
      <div className="workspace-body">
        {/* Navigation Sidebar */}
        <aside className="workspace-sidebar">
          <div>
            <div className="sidebar-group-title">Authentication & Identity</div>
            <ul className="sidebar-menu">
              <li
                className={`sidebar-item ${activeTab === 'overview' ? 'active' : ''}`}
                onClick={() => setActiveTab('overview')}
              >
                <svg className="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <span>User Session & Token</span>
              </li>
              <li
                className={`sidebar-item ${activeTab === 'system' ? 'active' : ''}`}
                onClick={() => setActiveTab('system')}
              >
                <svg className="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
                <span>Service Health</span>
              </li>
            </ul>
          </div>

          <div>
            <div className="sidebar-group-title">Platform Features</div>
            <ul className="sidebar-menu">
              <li className="sidebar-item disabled" title="Document Management available in next phase">
                <svg className="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <span>Documents (Pending)</span>
              </li>
              <li className="sidebar-item disabled" title="Chat interface available in next phase">
                <svg className="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
                <span>Knowledge Chat (Pending)</span>
              </li>
            </ul>
          </div>
        </aside>

        {/* Content Area */}
        <main className="workspace-content">
          <div className="breadcrumb">Identity & Security / Authenticated Session</div>

          <div className="page-header">
            <div>
              <h1 className="page-title">Identity & Access Management</h1>
              <p className="page-description">
                Active JWT-authenticated session for <strong>{user?.email}</strong>.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button className="btn-action" onClick={recheckProfile} id="btn-recheck-profile">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                {profileRefresh.loading ? 'Validating Token...' : 'Verify Session (GET /auth/me)'}
              </button>
            </div>
          </div>

          {/* User Session Profile Panel */}
          <div className="panel" id="user-profile-panel">
            <div className="panel-header">
              <div className="panel-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <span>Authenticated Identity Credentials</span>
              </div>
              <span className="status-pill success">● Active JWT Session</span>
            </div>

            <div className="panel-body">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Claim / Attribute</th>
                    <th>Value</th>
                    <th>Security Context</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><strong>User ID (Subject)</strong></td>
                    <td><span className="code-badge">{user?.id || '—'}</span></td>
                    <td>Immutable UUIDv4 Identifier</td>
                  </tr>
                  <tr>
                    <td><strong>Full Name</strong></td>
                    <td>{user?.name || '—'}</td>
                    <td>Identity Profile</td>
                  </tr>
                  <tr>
                    <td><strong>Corporate Email</strong></td>
                    <td>{user?.email || '—'}</td>
                    <td>Primary Subject Principal</td>
                  </tr>
                  <tr>
                    <td><strong>Department</strong></td>
                    <td>
                      <span className="dept-tag">{user?.department || 'Unassigned'}</span>
                    </td>
                    <td>Access Boundary Partition</td>
                  </tr>
                  <tr>
                    <td><strong>Assigned Roles</strong></td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                        {userRoles.map((r) => (
                          <span key={r} className="code-badge role-badge">
                            {r.toUpperCase()}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>Role-Based Access Control (RBAC)</td>
                  </tr>
                  <tr>
                    <td><strong>Bearer JWT Token</strong></td>
                    <td>
                      <div className="token-preview">
                        <span className="code-badge token-text">
                          {token ? `${token.slice(0, 24)}...${token.slice(-12)}` : 'None'}
                        </span>
                        <span className="status-pill success">Stored in Client</span>
                      </div>
                    </td>
                    <td>Auto-injected into <code>Authorization: Bearer</code> headers</td>
                  </tr>
                </tbody>
              </table>

              {profileRefresh.data && (
                <div className="auth-alert success" style={{ marginTop: '1rem' }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span>
                    Successfully verified user profile against <code>/api/v1/auth/me</code> at{' '}
                    {new Date().toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Backend Diagnostics Panel */}
          <div className="panel" id="system-status">
            <div className="panel-header">
              <div className="panel-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
                <span>Connected Backend Health</span>
              </div>
              <button
                className="btn-action small"
                onClick={checkHealth}
                id="btn-recheck-health"
              >
                Refresh
              </button>
            </div>

            <div className="panel-body">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Service Component</th>
                    <th>Endpoint</th>
                    <th>Runtime State</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><strong>Clario FastAPI Core</strong></td>
                    <td><span className="code-badge">/health</span></td>
                    <td>
                      {healthStatus.loading ? (
                        <span className="status-pill pending">Checking...</span>
                      ) : healthStatus.error ? (
                        <span className="status-pill error">Offline ({healthStatus.error})</span>
                      ) : (
                        <span className="status-pill success">● Healthy</span>
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td><strong>Authentication Service</strong></td>
                    <td><span className="code-badge">/api/v1/auth</span></td>
                    <td><span className="status-pill success">● Operational</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>

      {/* Footer */}
      <footer className="app-footer">
        <div>Clario Enterprise Platform &bull; Authenticated Identity Foundation</div>
        <div>FastAPI &bull; PostgreSQL &bull; JWT &bull; React + Vite</div>
      </footer>
    </div>
  );
};

export default Dashboard;
