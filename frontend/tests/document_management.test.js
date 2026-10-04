import { test, describe, beforeEach, mock } from 'node:test';
import assert from 'node:assert';

// Mock localStorage for Node test environment
const mockStorage = new Map();
global.localStorage = {
  getItem: (key) => mockStorage.get(key) || null,
  setItem: (key, val) => mockStorage.set(key, String(val)),
  removeItem: (key) => mockStorage.delete(key),
  clear: () => mockStorage.clear(),
};

// Import ApiClient
import { apiClient } from '../src/api/client.js';

describe('Milestone 11: Document Management API Client & Logic', () => {
  beforeEach(() => {
    mockStorage.clear();
  });

  test('1. Document query parameter construction with pagination and filters', async () => {
    let capturedUrl = '';
    let capturedOptions = {};

    global.fetch = mock.fn(async (url, options) => {
      capturedUrl = url;
      capturedOptions = options;
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => [
          {
            id: '11111111-1111-1111-1111-111111111111',
            title: 'Q1 Policy',
            filename: 'q1.pdf',
            status: 'READY',
          },
        ],
      };
    });

    apiClient.setToken('test-jwt-token-123');
    const docs = await apiClient.getDocuments({
      skip: 20,
      limit: 10,
      department: 'Engineering',
      status: 'READY',
      access_level: 'internal',
    });

    assert.strictEqual(docs.length, 1);
    assert.strictEqual(docs[0].title, 'Q1 Policy');
    assert(capturedUrl.includes('/api/v1/documents?'));
    assert(capturedUrl.includes('skip=20'));
    assert(capturedUrl.includes('limit=10'));
    assert(capturedUrl.includes('department=Engineering'));
    assert(capturedUrl.includes('status=READY'));
    assert(capturedUrl.includes('access_level=internal'));
    assert.strictEqual(capturedOptions.headers['Authorization'], 'Bearer test-jwt-token-123');
  });

  test('2. Upload document sends multipart FormData without application/json Content-Type', async () => {
    let capturedHeaders = {};
    let capturedBody = null;

    global.fetch = mock.fn(async (url, options) => {
      capturedHeaders = options.headers;
      capturedBody = options.body;
      return {
        ok: true,
        status: 201,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: '22222222-2222-2222-2222-222222222222',
          title: 'Uploaded Document',
          status: 'UPLOADED',
        }),
      };
    });

    const fakeFile = new Blob(['sample document content'], { type: 'application/pdf' });
    fakeFile.name = 'sample.pdf';

    const res = await apiClient.uploadDocument({
      file: fakeFile,
      title: 'Manual Title',
      department: 'Finance',
      access_level: 'confidential',
      document_type: 'pdf',
    });

    assert.strictEqual(res.status, 'UPLOADED');
    assert.strictEqual(capturedHeaders['Content-Type'], undefined, 'Content-Type must be undefined so browser sets multipart boundary');
    assert(capturedBody instanceof FormData);
  });

  test('3. Process document calls POST /api/v1/documents/{id}/process', async () => {
    let capturedUrl = '';
    let capturedMethod = '';

    global.fetch = mock.fn(async (url, options) => {
      capturedUrl = url;
      capturedMethod = options.method;
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: '33333333-3333-3333-3333-333333333333',
          status: 'PROCESSING',
        }),
      };
    });

    const res = await apiClient.processDocument('33333333-3333-3333-3333-333333333333');
    assert.strictEqual(res.status, 'PROCESSING');
    assert(capturedUrl.endsWith('/api/v1/documents/33333333-3333-3333-3333-333333333333/process'));
    assert.strictEqual(capturedMethod, 'POST');
  });

  test('4. Delete document handles HTTP 204 No Content cleanly', async () => {
    let capturedUrl = '';
    let capturedMethod = '';

    global.fetch = mock.fn(async (url, options) => {
      capturedUrl = url;
      capturedMethod = options.method;
      return {
        ok: true,
        status: 204,
        headers: new Headers(),
      };
    });

    const res = await apiClient.deleteDocument('44444444-4444-4444-4444-444444444444');
    assert.strictEqual(res, null);
    assert(capturedUrl.endsWith('/api/v1/documents/44444444-4444-4444-4444-444444444444'));
    assert.strictEqual(capturedMethod, 'DELETE');
  });

  test('5. HTTP 401 response auto-clears client authentication token', async () => {
    apiClient.setToken('expired-jwt');
    assert.strictEqual(apiClient.getToken(), 'expired-jwt');

    global.fetch = mock.fn(async () => {
      return {
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Token expired' }),
      };
    });

    await assert.rejects(
      async () => {
        await apiClient.getDocuments();
      },
      (err) => {
        assert.strictEqual(err.status, 401);
        return true;
      }
    );

    assert.strictEqual(apiClient.getToken(), null, 'Token should be cleared on 401');
  });
});
