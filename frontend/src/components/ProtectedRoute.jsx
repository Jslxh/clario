import React from 'react';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute = ({ children, fallback = null, requiredRole = null }) => {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="auth-loading-screen">
        <div className="auth-loading-card">
          <div className="brand-icon-box large">C</div>
          <div className="spinner"></div>
          <p className="loading-text">Authenticating secure session...</p>
          <span className="code-badge">Clario Security Gateway</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return fallback;
  }

  if (requiredRole && user?.roles) {
    const hasRole = user.roles.some((r) => r.name === requiredRole || r === requiredRole);
    if (!hasRole) {
      return (
        <div className="auth-error-screen">
          <div className="panel" style={{ maxWidth: '500px', margin: '4rem auto', textAlign: 'center' }}>
            <div className="panel-header">
              <span className="panel-title">Access Restricted</span>
              <span className="code-badge">HTTP 403</span>
            </div>
            <div className="panel-body" style={{ padding: '2rem' }}>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                Your account does not possess the <strong>{requiredRole}</strong> role required to access this resource.
              </p>
              <span className="status-pill error">Insufficient Permissions</span>
            </div>
          </div>
        </div>
      );
    }
  }

  return children;
};

export default ProtectedRoute;
