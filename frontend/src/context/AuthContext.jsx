import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => apiClient.getStoredUser());
  const [token, setToken] = useState(() => apiClient.getToken());
  const [isLoading, setIsLoading] = useState(() => {
    const storedToken = apiClient.getToken();
    const storedUser = apiClient.getStoredUser();
    // Only show full loading if we have a token but no hydrated user profile yet
    return Boolean(storedToken && !storedUser);
  });
  const [error, setError] = useState(null);

  // Initialize and verify existing session in background without flashing login
  useEffect(() => {
    let isMounted = true;

    const restoreSession = async () => {
      const storedToken = apiClient.getToken();
      if (!storedToken) {
        if (isMounted) {
          setUser(null);
          setToken(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const userData = await apiClient.getMe();
        if (isMounted) {
          setUser(userData);
          setToken(storedToken);
          apiClient.setStoredUser(userData);
          setError(null);
        }
      } catch (err) {
        // If token is invalid or expired (401), clear it
        if (err.status === 401) {
          console.warn('Session expired or unauthorized. Logging out:', err);
          apiClient.clearToken();
          if (isMounted) {
            setUser(null);
            setToken(null);
          }
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.login(email, password);
      setUser(data.user);
      setToken(data.access_token);
      return data.user;
    } catch (err) {
      const message = err.message || 'Login failed. Please check your credentials.';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async ({ email, password, name, department, role = 'user' }) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.register({ email, password, name, department, role });
      setUser(data.user);
      setToken(data.access_token);
      return data.user;
    } catch (err) {
      const message = err.message || 'Registration failed. Please try again.';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    apiClient.clearToken();
    setUser(null);
    setToken(null);
    setError(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value = {
    user,
    token,
    isAuthenticated: Boolean(token && user),
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
