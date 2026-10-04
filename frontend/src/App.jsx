import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Login } from './components/Login';
import { Register } from './components/Register';
import { Dashboard } from './components/Dashboard';
import { Documents } from './pages/Documents';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';

function AppContent() {
  const { isAuthenticated, isLoading } = useAuth();

  // Auth screen view: 'login' | 'register'
  const [authView, setAuthView] = useState(() =>
    window.location.hash === '#register' ? 'register' : 'login'
  );

  // Authenticated workspace view: 'documents' (default) | 'dashboard'
  const [workspaceView, setWorkspaceView] = useState(() =>
    window.location.hash === '#dashboard' ? 'dashboard' : 'documents'
  );

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
    return (
      <div className="auth-loading-screen">
        <div className="auth-loading-card">
          <div className="brand-icon-box large">C</div>
          <div className="spinner"></div>
          <p className="loading-text">Connecting to Clario Security Gateway...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <ProtectedRoute>
        <AppLayout currentView={workspaceView} onViewChange={handleWorkspaceViewChange}>
          {workspaceView === 'dashboard' ? <Dashboard /> : <Documents />}
        </AppLayout>
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
