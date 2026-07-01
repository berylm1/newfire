/**
 * Test Client - HTTP client wrapper for backend API testing
 * Provides typed methods for all API endpoints used in tenant/RBAC tests
 */

import https from 'https';
import http from 'http';

/**
 * Simple HTTP client for API testing
 * Handles JSON serialization, auth headers, and response parsing
 */
export class TestClient {
  constructor(baseUrl = 'http://localhost:3200') {
    this.baseUrl = baseUrl;
    this.baseUrlObj = new URL(baseUrl);
    this.token = null;
    this.userId = null;
    this.companyId = null;
  }

  /**
   * Set JWT token for authenticated requests
   */
  setToken(token) {
    this.token = token;
  }

  /**
   * Set user context after login
   */
  setUserContext(userId, companyId = null) {
    this.userId = userId;
    this.companyId = companyId;
  }

  /**
   * Make HTTP request to the API
   */
  async request(method, path, body = null, options = {}) {
    return new Promise((resolve, reject) => {
      const url = new URL(path, this.baseUrl);
      const isHttps = url.protocol === 'https:';
      const lib = isHttps ? https : http;

      const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
      };

      if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
      }

      const requestOptions = {
        method,
        headers,
        hostname: url.hostname,
        port: url.port || (isHttps ? 443 : 80),
        path: url.pathname + url.search,
      };

      const req = lib.request(requestOptions, (res) => {
        let data = '';

        res.on('data', (chunk) => {
          data += chunk;
        });

        res.on('end', () => {
          let parsed;
          try {
            parsed = data ? JSON.parse(data) : null;
          } catch {
            parsed = data;
          }

          const response = {
            status: res.statusCode,
            headers: res.headers,
            body: parsed,
          };

          if (res.statusCode >= 400) {
            reject(new Error(`HTTP ${res.statusCode}: ${JSON.stringify(parsed)}`));
          } else {
            resolve(response);
          }
        });
      });

      req.on('error', reject);

      if (body) {
        req.write(JSON.stringify(body));
      }

      req.end();
    });
  }

  // ==================== Auth Endpoints ====================

  /**
   * Register a new user
   */
  async signup(email, password, name) {
    const res = await this.request('POST', '/auth/signup', { email, password, name });
    return res.body;
  }

  /**
   * Login user and store token
   */
  async login(email, password) {
    const res = await this.request('POST', '/auth/login', { email, password });
    if (res.body?.token) {
      this.setToken(res.body.token);
      if (res.body.user) {
        this.setUserContext(res.body.user.id, res.body.user.company_id);
      }
    }
    return res.body;
  }

  /**
   * Get current user info
   */
  async getMe() {
    const res = await this.request('GET', '/auth/me');
    return res.body;
  }

  /**
   * Refresh access token
   */
  async refreshToken(refreshToken) {
    const res = await this.request('POST', '/auth/refresh', { refreshToken });
    if (res.body?.token) {
      this.setToken(res.body.token);
    }
    return res.body;
  }

  // ==================== Company Endpoints ====================

  /**
   * Create a new company (tenant)
   */
  async createCompany(name, description = '') {
    const res = await this.request('POST', '/companies', { name, description });
    if (res.body?.id) {
      this.companyId = res.body.id;
    }
    return res.body;
  }

  /**
   * Get company by ID
   */
  async getCompany(companyId) {
    const res = await this.request('GET', `/companies/${companyId}`);
    return res.body;
  }

  /**
   * List companies (admin only)
   */
  async listCompanies() {
    const res = await this.request('GET', '/companies');
    return res.body;
  }

  /**
   * Update company
   */
  async updateCompany(companyId, data) {
    const res = await this.request('PUT', `/companies/${companyId}`, data);
    return res.body;
  }

  /**
   * Delete company (admin only)
   */
  async deleteCompany(companyId) {
    const res = await this.request('DELETE', `/companies/${companyId}`);
    return res.body;
  }

  // ==================== Agent Endpoints ====================

  /**
   * Create a new agent for the company
   */
  async createAgent(agentData) {
    const res = await this.request('POST', '/agents', agentData);
    return res.body;
  }

  /**
   * Get agent by ID
   */
  async getAgent(agentId) {
    const res = await this.request('GET', `/agents/${agentId}`);
    return res.body;
  }

  /**
   * List agents for current company
   */
  async listAgents() {
    const res = await this.request('GET', '/agents');
    return res.body;
  }

  /**
   * Update agent
   */
  async updateAgent(agentId, data) {
    const res = await this.request('PUT', `/agents/${agentId}`, data);
    return res.body;
  }

  /**
   * Delete agent
   */
  async deleteAgent(agentId) {
    const res = await this.request('DELETE', `/agents/${agentId}`);
    return res.body;
  }

  // ==================== Chat/Conversation Endpoints ====================

  /**
   * Send a chat message
   */
  async chat(agentId, message) {
    const res = await this.request('POST', '/chat', { agentId, message });
    return res.body;
  }

  /**
   * Get conversation history
   */
  async getConversation(agentId) {
    const res = await this.request('GET', `/conversations/${agentId}`);
    return res.body;
  }

  // ==================== Health Check ====================

  /**
   * Check if backend is healthy
   */
  async healthCheck() {
    try {
      const res = await this.request('GET', '/health');
      return res.status === 200;
    } catch {
      return false;
    }
  }

  /**
   * Clear authentication state
   */
  clearAuth() {
    this.token = null;
    this.userId = null;
    this.companyId = null;
  }
}

/**
 * Create a new authenticated test client
 */
export function createTestClient(baseUrl = 'http://localhost:3200') {
  return new TestClient(baseUrl);
}

export default TestClient;