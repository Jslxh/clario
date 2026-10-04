import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const DEPARTMENTS = [
  'Engineering',
  'Operations',
  'Legal & Compliance',
  'Finance',
  'Human Resources',
  'Product & Design',
  'Security & IT',
  'Research',
];

export const Register = ({ onSwitchToLogin }) => {
  const { register, error: authError, clearError } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [department, setDepartment] = useState('Engineering');
  const [role, setRole] = useState('user');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError('');
    clearError();

    if (!name.trim()) {
      setValidationError('Full name is required.');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setValidationError('A valid corporate email address is required.');
      return;
    }
    if (password.length < 6) {
      setValidationError('Password must be at least 6 characters in length.');
      return;
    }
    if (password !== confirmPassword) {
      setValidationError('Passwords do not match. Please re-enter.');
      return;
    }

    setIsSubmitting(true);
    try {
      await register({
        email: email.trim().toLowerCase(),
        password,
        name: name.trim(),
        department,
        role,
      });
    } catch {
      // Error handled by AuthContext
    } finally {
      setIsSubmitting(false);
    }
  };

  const displayError = validationError || authError;

  return (
    <div className="auth-card-container">
      <div className="auth-card">
        <div className="auth-card-header">
          <div className="brand-logo-large">
            <div className="brand-icon-box large">C</div>
            <div>
              <h2 className="brand-title-large">Clario</h2>
              <span className="brand-subtitle-tag">Identity Provisioning</span>
            </div>
          </div>
          <p className="auth-subtitle">Create a corporate profile to begin collaborating on secured knowledge graphs.</p>
        </div>

        {displayError && (
          <div className="auth-alert error" role="alert">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{displayError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="form-group">
            <label htmlFor="register-name" className="form-label">
              Full Legal Name
            </label>
            <div className="input-with-icon">
              <svg className="field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              <input
                id="register-name"
                type="text"
                className="form-input"
                placeholder="Jane Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                required
                disabled={isSubmitting}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="register-email" className="form-label">
              Corporate Email Address
            </label>
            <div className="input-with-icon">
              <svg className="field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <polyline points="22,6 12,13 2,6" />
              </svg>
              <input
                id="register-email"
                type="email"
                className="form-input"
                placeholder="jane.doe@organization.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
                disabled={isSubmitting}
              />
            </div>
          </div>

          <div className="form-row-2col">
            <div className="form-group">
              <label htmlFor="register-dept" className="form-label">
                Department
              </label>
              <select
                id="register-dept"
                className="form-select"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                disabled={isSubmitting}
              >
                {DEPARTMENTS.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="register-role" className="form-label">
                Initial Role
              </label>
              <select
                id="register-role"
                className="form-select"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                disabled={isSubmitting}
              >
                <option value="user">User (Standard)</option>
                <option value="analyst">Analyst</option>
                <option value="admin">Administrator</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="register-password" className="form-label">
              Password (minimum 6 characters)
            </label>
            <div className="input-with-icon">
              <svg className="field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <input
                id="register-password"
                type={showPassword ? 'text' : 'password'}
                className="form-input"
                placeholder="Choose a strong password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                required
                disabled={isSubmitting}
              />
              <button
                type="button"
                className="btn-toggle-password"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex="-1"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="register-confirm-password" className="form-label">
              Confirm Password
            </label>
            <div className="input-with-icon">
              <svg className="field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <input
                id="register-confirm-password"
                type={showPassword ? 'text' : 'password'}
                className="form-input"
                placeholder="Repeat your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                required
                disabled={isSubmitting}
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn-primary full-width"
            id="btn-register-submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className="btn-spinner"></span>
                <span>Creating Account...</span>
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="8.5" cy="7" r="4" />
                  <line x1="20" y1="8" x2="20" y2="14" />
                  <line x1="23" y1="11" x2="17" y2="11" />
                </svg>
                <span>Create Enterprise Account</span>
              </>
            )}
          </button>
        </form>

        <div className="auth-card-footer">
          <p className="footer-prompt">
            Already have an account?{' '}
            <button
              type="button"
              className="link-button"
              id="link-go-to-login"
              onClick={onSwitchToLogin}
            >
              Sign in
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
