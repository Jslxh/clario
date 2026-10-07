/**
 * Clario Enterprise API Client
 * Configured with VITE_API_URL and automatic JWT authorization injection.
 */

const BASE_URL = (
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) ||
  (typeof process !== 'undefined' && process.env?.VITE_API_URL) ||
  'http://localhost:8000'
).replace(/\/+$/, '');

class ApiClient {
  constructor() {
    this.tokenKey = 'clario_token';
    this.userKey = 'clario_user';
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

  getStoredUser() {
    try {
      const stored = localStorage.getItem(this.userKey);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }

  setStoredUser(user) {
    try {
      if (user) {
        localStorage.setItem(this.userKey, JSON.stringify(user));
      } else {
        localStorage.removeItem(this.userKey);
      }
    } catch (e) {
      console.warn('Failed to access localStorage:', e);
    }
  }

  clearToken() {
    try {
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem(this.userKey);
    } catch (e) {
      console.warn('Failed to remove token and user from localStorage:', e);
    }
  }

  async request(endpoint, options = {}) {
    const url = `${BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    const token = this.getToken();

    const headers = { ...options.headers };

    // Do not set Content-Type for FormData; browser sets multipart/form-data boundary
    if (typeof FormData !== 'undefined' && options.body instanceof FormData) {
      delete headers['Content-Type'];
    } else if (!headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

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

    if (response.status === 204) {
      return null;
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
      if (data.user) {
        this.setStoredUser(data.user);
      }
    }
    return data;
  }

  async register({ email, password, name, department, role = 'user' }) {
    const data = await this.request('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name, department, role }),
    });
    if (data && data.access_token) {
      this.setToken(data.access_token);
      if (data.user) {
        this.setStoredUser(data.user);
      }
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

  // Document Management Methods
  async getDocuments({ skip = 0, limit = 20, department, status, access_level } = {}) {
    const params = new URLSearchParams();
    if (skip !== undefined && skip !== null) params.append('skip', String(skip));
    if (limit !== undefined && limit !== null) params.append('limit', String(limit));
    if (department) params.append('department', department);
    if (status) params.append('status', status);
    if (access_level) params.append('access_level', access_level);

    const queryString = params.toString();
    const endpoint = `/api/v1/documents${queryString ? `?${queryString}` : ''}`;
    return this.request(endpoint, {
      method: 'GET',
    });
  }

  async getDocument(documentId) {
    if (!documentId) throw new Error('Document ID is required');
    return this.request(`/api/v1/documents/${documentId}`, {
      method: 'GET',
    });
  }

  async getDocumentChunks(documentId) {
    if (!documentId) throw new Error('Document ID is required');
    return this.request(`/api/v1/documents/${documentId}/chunks`, {
      method: 'GET',
    });
  }

  async uploadDocument({ file, title, department, access_level = 'internal', document_type }) {
    if (!file) throw new Error('File is required for document upload');

    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    if (department) formData.append('department', department);
    if (access_level) formData.append('access_level', access_level);
    if (document_type) formData.append('document_type', document_type);

    return this.request('/api/v1/documents/upload', {
      method: 'POST',
      body: formData,
    });
  }

  async processDocument(documentId) {
    if (!documentId) throw new Error('Document ID is required');
    return this.request(`/api/v1/documents/${documentId}/process`, {
      method: 'POST',
    });
  }

  async deleteDocument(documentId) {
    if (!documentId) throw new Error('Document ID is required');
    return this.request(`/api/v1/documents/${documentId}`, {
      method: 'DELETE',
    });
  }
}

export const apiClient = new ApiClient();
export default apiClient;

