import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Login } from './components/Login';
import { Register } from './components/Register';
import { Dashboard } from './components/Dashboard';
import { ProtectedRoute } from './components/ProtectedRoute';

function AppContent() {
  const { isAuthenticated, isLoading } = useAuth();
  const [authView, setAuthView] = useState(() =>
    window.location.hash === '#register' ? 'register' : 'login'
  );

  // Sync state with URL hash
  useEffect(() => {
    const handleHashChange = () => {
      if (window.location.hash === '#register') {
        setAuthView('register');
      } else if (window.location.hash === '#login') {
        setAuthView('login');
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
        <Dashboard />
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
