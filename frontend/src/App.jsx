import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TaskProvider } from './context/TaskContext';
import { Login } from './components/Login';
import { Register } from './components/Register';
import { Dashboard } from './components/Dashboard';
import { Documents } from './pages/Documents';
import { Chat } from './pages/Chat';
import { Search } from './pages/Search';
import { Profile } from './pages/Profile';
import { AuditLogs } from './pages/AuditLogs';
import { Users } from './pages/Users';
import { Roles } from './pages/Roles';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';
import { SecurityGatewayLoading } from './components/SecurityGatewayLoading';

function AppContent() {
  const { user, isAuthenticated, isLoading } = useAuth();

  // Auth screen view: 'login' | 'register'
  const [authView, setAuthView] = useState(() =>
    window.location.hash === '#register' ? 'register' : 'login'
  );

  // Authenticated workspace view
  const [workspaceView, setWorkspaceView] = useState(() => {
    const hash = window.location.hash;
    if (hash === '#dashboard') return 'dashboard';
    if (hash === '#documents') return 'documents';
    if (hash === '#search') return 'search';
    if (hash === '#profile') return 'profile';
    if (hash === '#audit-logs') return 'audit-logs';
    if (hash === '#users') return 'users';
    if (hash === '#roles') return 'roles';
    if (hash === '#chat') return 'chat';
    return 'chat';
  });

  // Sync state with URL hash
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash;
      if (hash === '#register') {
        setAuthView('register');
      } else if (hash === '#login') {
        setAuthView('login');
      } else if (hash === '#dashboard') {
        setWorkspaceView('dashboard');
      } else if (hash === '#documents') {
        setWorkspaceView('documents');
      } else if (hash === '#search') {
        setWorkspaceView('search');
      } else if (hash === '#profile') {
        setWorkspaceView('profile');
      } else if (hash === '#audit-logs') {
        setWorkspaceView('audit-logs');
      } else if (hash === '#users') {
        setWorkspaceView('users');
      } else if (hash === '#roles') {
        setWorkspaceView('roles');
      } else if (hash === '#chat') {
        setWorkspaceView('chat');
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const switchToRegister = () => {
    window.location.hash = '#register';
    setAuthView('register');
  };

  const switchToLogin = () => {
    window.location.hash = '#login';
    setAuthView('login');
  };

  const handleWorkspaceViewChange = (view) => {
    window.location.hash = `#${view}`;
    setWorkspaceView(view);
  };

  if (isLoading) {
    return <SecurityGatewayLoading />;
  }

  if (isAuthenticated) {
    const userRoles = user?.roles
      ? user.roles.map((r) => (typeof r === 'object' ? r.name : r))
      : ['user'];
    const isAdmin = userRoles.includes('admin');
    const isAnalyst = userRoles.includes('analyst');
    const isAdminOrAnalyst = isAdmin || isAnalyst;

    const renderForbidden = (message) => (
      <div className="auth-error-screen">
        <div className="panel" style={{ maxWidth: '540px', margin: '4rem auto', textAlign: 'center' }}>
          <div className="panel-header">
            <div className="panel-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>403 — Access Restricted</span>
            </div>
            <span className="code-badge">HTTP 403 FORBIDDEN</span>
          </div>
          <div className="panel-body" style={{ padding: '2rem' }}>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', lineHeight: '1.5' }}>
              {message || `Your account role (${userRoles[0]?.toUpperCase() || 'USER'}) is not authorized to access this section.`}
            </p>
            <button
              type="button"
              className="btn-primary"
              onClick={() => handleWorkspaceViewChange('chat')}
            >
              Return to Knowledge Chat
            </button>
          </div>
        </div>
      </div>
    );

    return (
      <ProtectedRoute>
        <TaskProvider>
          <AppLayout currentView={workspaceView} onViewChange={handleWorkspaceViewChange}>
            {workspaceView === 'dashboard' ? (
              isAdminOrAnalyst ? (
                <Dashboard />
              ) : (
                renderForbidden(`Your account role (${userRoles[0]?.toUpperCase() || 'USER'}) is not authorized to access infrastructure diagnostics.`)
              )
            ) : workspaceView === 'audit-logs' ? (
              isAdminOrAnalyst ? (
                <AuditLogs />
              ) : (
                renderForbidden(`Your account role (${userRoles[0]?.toUpperCase() || 'USER'}) is not authorized to view enterprise audit logs.`)
              )
            ) : workspaceView === 'users' ? (
              isAdmin ? (
                <Users />
              ) : (
                renderForbidden(`Your account role (${userRoles[0]?.toUpperCase() || 'USER'}) is not authorized to manage user accounts.`)
              )
            ) : workspaceView === 'roles' ? (
              isAdmin ? (
                <Roles />
              ) : (
                renderForbidden(`Your account role (${userRoles[0]?.toUpperCase() || 'USER'}) is not authorized to access role configurations.`)
              )
            ) : workspaceView === 'documents' ? (
              <Documents />
            ) : workspaceView === 'search' ? (
              <Search />
            ) : workspaceView === 'profile' ? (
              <Profile />
            ) : (
              <Chat />
            )}
          </AppLayout>
        </TaskProvider>
      </ProtectedRoute>
    );
  }

  return (
    <div className="app-container">
      {authView === 'login' ? (
        <Login onSwitchToRegister={switchToRegister} />
      ) : (
        <Register onSwitchToLogin={switchToLogin} />
      )}
    </div>
  );
}

export function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
