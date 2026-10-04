/**
 * Clario Enterprise API Client
 * Configured with VITE_API_URL and automatic JWT authorization injection.
 */

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

class ApiClient {
  constructor() {
    this.tokenKey = 'clario_token';
  }

  getToken() {
    try {
      return localStorage.getItem(this.tokenKey);
    } catch {
      return null;
    }
  }

  setToken(token) {
    try {
      if (token) {
        localStorage.setItem(this.tokenKey, token);
      } else {
        localStorage.removeItem(this.tokenKey);
      }
    } catch (e) {
      console.warn('Failed to access localStorage:', e);
    }
  }

  clearToken() {
    try {
      localStorage.removeItem(this.tokenKey);
    } catch (e) {
      console.warn('Failed to remove token from localStorage:', e);
    }
  }

  async request(endpoint, options = {}) {
    const url = `${BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    const token = this.getToken();

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
      ...options,
      headers,
    };

    let response;
    try {
      response = await fetch(url, config);
    } catch (networkErr) {
      throw new Error(`Network error: Unable to reach Clario server at ${BASE_URL}. (${networkErr.message})`);
    }

    if (response.status === 401) {
      // Auto-clear invalid/expired token
      this.clearToken();
    }

    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      try {
        data = await response.json();
      } catch {
        data = null;
      }
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const errorMessage =
        (data && typeof data === 'object' && (data.detail || data.message)) ||
        `Request failed with status code ${response.status}`;
      const error = new Error(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  }

  // Authentication Methods
  async login(email, password) {
    const data = await this.request('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (data && data.access_token) {
      this.setToken(data.access_token);
    }
    return data;
  }

  async register({ email, password, name, department }) {
    const data = await this.request('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name, department }),
    });
    if (data && data.access_token) {
      this.setToken(data.access_token);
    }
    return data;
  }

  async getMe() {
    return this.request('/api/v1/auth/me', {
      method: 'GET',
    });
  }

  async checkHealth() {
    return this.request('/health', {
      method: 'GET',
    });
  }
}

export const apiClient = new ApiClient();
export default apiClient;
