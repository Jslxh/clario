import React from 'react';
import { useTask } from '../../context/TaskContext';

export const ProcessMonitorDrawer = () => {
  const { tasks, isProcessDrawerOpen, closeProcessDrawer, activeProcessesCount } = useTask();

  if (!isProcessDrawerOpen) return null;

  const formatDuration = (ms) => {
    if (!ms || ms <= 0) return '< 10ms';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '—';
    const d = new Date(timestamp);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const getTaskIcon = (type) => {
    if (type === 'llm_query') {
      return (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      );
    }
    if (type === 'doc_process') {
      return (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      );
    }
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    );
  };

  return (
    <div className="drawer-backdrop" onClick={closeProcessDrawer}>
      <aside
        className="drawer-container process-monitor-drawer"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Async Process & Thread Monitor"
      >
        {/* Drawer Header */}
        <div className="drawer-header">
          <div className="drawer-title-box">
            <div className="process-monitor-icon-box">
              <span className={`pulse-dot ${activeProcessesCount > 0 ? 'active' : ''}`}></span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
                <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
                <line x1="6" y1="6" x2="6.01" y2="6" />
                <line x1="6" y1="18" x2="6.01" y2="18" />
              </svg>
            </div>
            <div>
              <h2 className="drawer-title">Async Process & Thread Monitor</h2>
              <span className="drawer-subtitle">
                {activeProcessesCount} active thread{activeProcessesCount === 1 ? '' : 's'} &bull; Real-time Background Execution
              </span>
            </div>
          </div>
          <button
            type="button"
            className="btn-modal-close"
            onClick={closeProcessDrawer}
            aria-label="Close process monitor"
          >
            &times;
          </button>
        </div>

        {/* System Thread Summary Banner */}
        <div className="process-summary-banner">
          <div className="proc-summary-item">
            <span className="proc-sum-label">Active Threads</span>
            <span className="proc-sum-val cyan">{activeProcessesCount}</span>
          </div>
          <div className="proc-summary-item">
            <span className="proc-sum-label">Total Spanned</span>
            <span className="proc-sum-val">{tasks.length}</span>
          </div>
          <div className="proc-summary-item">
            <span className="proc-sum-label">Worker Mode</span>
            <span className="proc-sum-val emerald">Non-Blocking</span>
          </div>
        </div>

        {/* Task Process List */}
        <div className="drawer-body process-tasks-body">
          {tasks.length === 0 ? (
            <div className="table-empty-state">
              <div className="empty-state-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
                  <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
                </svg>
              </div>
              <h3 className="empty-state-title">No Active Background Tasks</h3>
              <p className="empty-state-desc">
                When you run Knowledge Chat queries or dispatch document vectorization, asynchronous worker threads with unique Process IDs will appear here.
              </p>
            </div>
          ) : (
            <div className="process-list-container">
              {tasks.map((task) => {
                const isRunning = task.status === 'RUNNING';
                const isCompleted = task.status === 'COMPLETED';
                const isFailed = task.status === 'FAILED';

                return (
                  <div
                    key={task.id}
                    className={`process-task-card ${task.status.toLowerCase()}`}
                  >
                    <div className="proc-card-header">
                      <div className="proc-id-group">
                        <span className={`proc-type-icon ${task.type}`}>
                          {getTaskIcon(task.type)}
                        </span>
                        <span className="proc-pid-pill">{task.id}</span>
                        <span className="proc-thread-name">{task.thread}</span>
                      </div>

                      <div className="proc-status-badge">
                        {isRunning && (
                          <span className="status-badge-running">
                            <span className="btn-spinner"></span>
                            <span>EXECUTING</span>
                          </span>
                        )}
                        {isCompleted && (
                          <span className="status-badge-completed">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                              <polyline points="20 6 9 17 4 12" />
                            </svg>
                            <span>DONE ({formatDuration(task.durationMs)})</span>
                          </span>
                        )}
                        {isFailed && (
                          <span className="status-badge-failed">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                              <circle cx="12" cy="12" r="10" />
                              <line x1="12" y1="8" x2="12" y2="12" />
                            </svg>
                            <span>FAILED</span>
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="proc-title-text">{task.title}</div>

                    {task.error && (
                      <div className="proc-error-text">
                        <span>Error:</span> {task.error}
                      </div>
                    )}

                    <div className="proc-card-footer">
                      <span className="proc-time-text">Started {formatTime(task.startTime)}</span>
                      {task.endTime && (
                        <span className="proc-time-text">Completed {formatTime(task.endTime)}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Drawer Footer */}
        <div className="drawer-footer">
          <button
            type="button"
            className="btn-secondary"
            onClick={closeProcessDrawer}
          >
            Close Monitor
          </button>
        </div>
      </aside>
    </div>
  );
};

export default ProcessMonitorDrawer;

