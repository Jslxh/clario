import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import apiClient from '../api/client';

export const Dashboard = () => {
  const { user, token } = useAuth();
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

  const userRoles = user?.roles
    ? user.roles.map((r) => (typeof r === 'object' ? r.name : r))
    : ['user'];

  return (
    <div className="dashboard-content-container">
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
              <tr>
                <td><strong>Document Management API</strong></td>
                <td><span className="code-badge">/api/v1/documents</span></td>
                <td><span className="status-pill success">● Operational</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
