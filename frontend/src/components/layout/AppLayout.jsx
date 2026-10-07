import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useTask } from '../../context/TaskContext';
import { ProcessMonitorDrawer } from '../common/ProcessMonitorDrawer';

export const AppLayout = ({ currentView = 'documents', onViewChange, children }) => {
  const { user, logout } = useAuth();
  const { activeProcessesCount, runningTasks, openProcessDrawer, globalNotification, dismissGlobalNotification } = useTask();

  const userInitials = user?.name
    ? user.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : 'U';

  const navigateTo = (view) => {
    if (onViewChange) {
      onViewChange(view);
    }
  };

  return (
    <div className="app-container">
      {/* Enterprise Top Navigation Bar */}
      <header className="app-header">
        <div className="header-left">
          <a
            href="#documents"
            className="brand-logo"
            onClick={(e) => {
              e.preventDefault();
              navigateTo('documents');
            }}
          >
            <div className="brand-icon-box">C</div>
            <span className="brand-title">Clario</span>
          </a>
          <span className="brand-subtitle">Enterprise Knowledge Platform</span>
        </div>

        <div className="header-right">
          {/* Real-Time Async Process & Thread Indicator */}
          <button
            type="button"
            className={`async-process-indicator-btn ${activeProcessesCount > 0 ? 'running' : 'idle'}`}
            onClick={openProcessDrawer}
            title="Open Async Process & Worker Thread Monitor"
            id="btn-process-monitor"
          >
            <span className={`pulse-dot ${activeProcessesCount > 0 ? 'active' : ''}`}></span>
            <span className="proc-indicator-text">
              {activeProcessesCount > 0 ? (
                <>
                  <strong>{activeProcessesCount} Worker{activeProcessesCount === 1 ? '' : 's'} Active</strong>
                  <span className="proc-pid-hint">({runningTasks[0]?.id})</span>
                </>
              ) : (
                <span>Threads Idle (Ready)</span>
              )}
            </span>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
            </svg>
          </button>

          <div className="system-status-indicator" title="Connected to Enterprise Knowledge Cloud">
            <span className="pulse-dot"></span>
            <span>Cloud Connected</span>
          </div>

          <div
            className="user-profile-badge"
            onClick={() => navigateTo('profile')}
            style={{ cursor: 'pointer' }}
            title="View Account Profile"
            id="header-user-profile-btn"
          >
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

      {/* Global Toast for Async Process Events */}
      {globalNotification && (
        <div className={`toast-notification ${globalNotification.type} global-async-toast`} role="status">
          <div className="toast-icon">
            {globalNotification.pid && (
              <span className="toast-pid-pill">{globalNotification.pid}</span>
            )}
            <span className="pulse-dot active"></span>
          </div>
          <span className="toast-message">{globalNotification.message}</span>
          <button
            type="button"
            className="toast-close"
            onClick={dismissGlobalNotification}
            aria-label="Dismiss notification"
          >
            &times;
          </button>
        </div>
      )}

      {/* Async Process & Worker Thread Drawer */}
      <ProcessMonitorDrawer />

      {/* Main Enterprise Workspace */}
      <div className="workspace-body">
        {/* Navigation Sidebar */}
        <aside className="workspace-sidebar">
          <div>
            <div className="sidebar-group-title">Knowledge Base</div>
            <ul className="sidebar-menu">
              <li
                className={`sidebar-item ${currentView === 'documents' ? 'active' : ''}`}
                onClick={() => navigateTo('documents')}
                id="nav-documents"
              >
                <svg className="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
                <span>Documents</span>
              </li>
            </ul>
          </div>

          <div>
            <div className="sidebar-group-title">System & Security</div>
            <ul className="sidebar-menu">
              <li
                className={`sidebar-item ${currentView === 'dashboard' ? 'active' : ''}`}
                onClick={() => navigateTo('dashboard')}
                id="nav-dashboard"
              >
                <svg className="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <span>Identity & Health</span>
              </li>
            </ul>
          </div>

          <div>
            <div className="sidebar-group-title">Future Capabilities</div>
            <ul className="sidebar-menu">
              <li className="sidebar-item disabled" title="Chat interface scheduled for future phase">
                <svg className="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
                <span>Knowledge Chat (Next)</span>
              </li>
              <li className="sidebar-item disabled" title="Search interface scheduled for future phase">
                <svg className="sidebar-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <span>Semantic Search (Next)</span>
              </li>
            </ul>
          </div>
        </aside>

        {/* Content Area */}
        <main className="workspace-content">{children}</main>
      </div>

      {/* Footer */}
      <footer className="app-footer">
        <div>Clario Enterprise Platform &bull; Knowledge Intelligence &bull; Milestone 11</div>
        <div>FastAPI &bull; PostgreSQL &bull; Qdrant &bull; React + Vite</div>
      </footer>
    </div>
  );
};

export default AppLayout;
