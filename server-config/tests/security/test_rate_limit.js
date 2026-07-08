/**
 * Rate Limiting Middleware Tests
 * 
 * Tests for authentication rate limiting and brute force protection.
 */

const {
  createRateLimiter,
  authRateLimiter,
  loginRateLimiter,
  passwordResetRateLimiter,
  signupRateLimiter,
  recordFailedAuth,
  clearFailedAuth,
  getRateLimitStatus,
  clearRateLimitStore,
  generateKey,
  DEFAULT_CONFIG,
  rateLimitStore,
} = require('../../rate-limit');

describe('Rate Limiting Middleware', () => {
  let mockReq;
  let mockRes;
  let mockNext;

  beforeEach(() => {
    // Clear rate limit store before each test
    clearRateLimitStore();

    mockReq = {
      ip: '192.168.1.100',
      connection: { remoteAddress: '192.168.1.100' },
      headers: {
        'user-agent': 'Mozilla/5.0 Test Browser',
      },
      method: 'POST',
    };
    mockRes = {
      _headers: {},
      setHeader: function(name, value) {
        this._headers[name.toLowerCase()] = value;
      },
      getHeader: function(name) {
        return this._headers[name.toLowerCase()];
      },
      statusCode: 200,
      status: function(code) {
        this.statusCode = code;
        return this;
      },
      json: jest.fn(function(data) { return data; }),
    };
    mockNext = jest.fn();
  });

  describe('DEFAULT_CONFIG', () => {
    test('should have auth config with correct limits', () => {
      expect(DEFAULT_CONFIG.auth.windowMs).toBe(15 * 60 * 1000);
      expect(DEFAULT_CONFIG.auth.maxAttempts).toBe(5);
    });

    test('should have login config with correct limits', () => {
      expect(DEFAULT_CONFIG.login.windowMs).toBe(15 * 60 * 1000);
      expect(DEFAULT_CONFIG.login.maxAttempts).toBe(5);
    });

    test('should have password reset config with stricter limits', () => {
      expect(DEFAULT_CONFIG.passwordReset.maxAttempts).toBe(3);
    });

    test('should have signup config with correct limits', () => {
      expect(DEFAULT_CONFIG.signup.maxAttempts).toBe(5);
    });
  });

  describe('generateKey', () => {
    test('should generate consistent keys for same request', () => {
      const key1 = generateKey(mockReq, 'login');
      const key2 = generateKey(mockReq, 'login');

      expect(key1).toBe(key2);
    });

    test('should generate different keys for different IPs', () => {
      const req1 = { ...mockReq, ip: '192.168.1.1' };
      const req2 = { ...mockReq, ip: '192.168.1.2' };

      const key1 = generateKey(req1, 'login');
      const key2 = generateKey(req2, 'login');

      expect(key1).not.toBe(key2);
    });

    test('should generate different keys for different types', () => {
      const key1 = generateKey(mockReq, 'login');
      const key2 = generateKey(mockReq, 'signup');

      expect(key1).not.toBe(key2);
    });
  });

  describe('createRateLimiter', () => {
    test('should allow requests within limit', () => {
      const middleware = createRateLimiter({ 
        type: 'login',
        recordOnRequest: false
      });

      middleware(mockReq, mockRes, mockNext);

      expect(mockNext).toHaveBeenCalled();
      expect(mockRes.getHeader('x-ratelimit-limit')).toBe(5);
      expect(mockRes.getHeader('x-ratelimit-remaining')).toBe(5);
    });

    test('should set rate limit headers', () => {
      const middleware = createRateLimiter({ 
        type: 'login',
        recordOnRequest: false 
      });

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('x-ratelimit-limit')).toBeDefined();
      expect(mockRes.getHeader('x-ratelimit-remaining')).toBeDefined();
      expect(mockRes.getHeader('x-ratelimit-reset')).toBeDefined();
    });

    test('should track attempts via recordFailedAuth', () => {
      const middleware = createRateLimiter({ 
        type: 'login',
        recordOnRequest: false 
      });

      // Record failed attempts
      recordFailedAuth(mockReq, 'login');
      recordFailedAuth(mockReq, 'login');
      recordFailedAuth(mockReq, 'login');

      // Next request should reflect the recorded attempts
      middleware(mockReq, mockRes, mockNext);
      expect(mockNext).toHaveBeenCalledTimes(1);
      expect(mockRes.getHeader('x-ratelimit-remaining')).toBe(2);
    });

    test('should block requests after max attempts reached via lockout', () => {
      // Simulate lockout directly in the store
      const key = generateKey(mockReq, 'login');
      const lockoutKey = `${key}:lockout`;
      rateLimitStore.set(lockoutKey, Date.now() + 60000);

      const middleware = createRateLimiter({
        type: 'login',
        recordOnRequest: false,
      });

      // Request should be blocked due to lockout
      middleware(mockReq, mockRes, mockNext);
      
      expect(mockNext).not.toHaveBeenCalled();
      expect(mockRes.statusCode).toBe(429);
      expect(mockRes.getHeader('retry-after')).toBeDefined();
    });

    test('should include Retry-After header when locked out', () => {
      // Simulate lockout directly in the store
      const key = generateKey(mockReq, 'login');
      const lockoutKey = `${key}:lockout`;
      rateLimitStore.set(lockoutKey, Date.now() + 60000);

      const middleware = createRateLimiter({
        type: 'login',
        recordOnRequest: false,
      });

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('retry-after')).toBeDefined();
      expect(mockRes.getHeader('x-ratelimit-remaining')).toBe(0);
    });
  });

  describe('Pre-configured rate limiters', () => {
    test('authRateLimiter should have correct config', () => {
      authRateLimiter(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('x-ratelimit-limit')).toBe(5);
    });

    test('loginRateLimiter should have correct config', () => {
      loginRateLimiter(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('x-ratelimit-limit')).toBe(5);
    });

    test('passwordResetRateLimiter should have stricter limits', () => {
      passwordResetRateLimiter(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('x-ratelimit-limit')).toBe(3);
    });

    test('signupRateLimiter should have correct config', () => {
      signupRateLimiter(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('x-ratelimit-limit')).toBe(5);
    });
  });

  describe('recordFailedAuth', () => {
    test('should track failed attempts', () => {
      const result1 = recordFailedAuth(mockReq, 'login');
      expect(result1.attemptCount).toBe(1);
      expect(result1.remainingAttempts).toBe(4);
      expect(result1.isLockedOut).toBe(false);

      const result2 = recordFailedAuth(mockReq, 'login');
      expect(result2.attemptCount).toBe(2);
      expect(result2.remainingAttempts).toBe(3);
    });

    test('should trigger lockout after max attempts', () => {
      for (let i = 0; i < 5; i++) {
        recordFailedAuth(mockReq, 'login');
      }

      const status = getRateLimitStatus(mockReq, 'login');
      expect(status.locked).toBe(true);
      expect(status.attempts).toBe(5);
    });
  });

  describe('clearFailedAuth', () => {
    test('should clear attempts on successful auth', () => {
      // Make some failed attempts
      recordFailedAuth(mockReq, 'login');
      recordFailedAuth(mockReq, 'login');

      // Clear on success
      clearFailedAuth(mockReq, 'login');

      const status = getRateLimitStatus(mockReq, 'login');
      expect(status.attempts).toBe(0);
      expect(status.locked).toBe(false);
    });
  });

  describe('getRateLimitStatus', () => {
    test('should return current status', () => {
      const status = getRateLimitStatus(mockReq, 'login');

      expect(status).toHaveProperty('locked');
      expect(status).toHaveProperty('attempts');
      expect(status).toHaveProperty('maxAttempts');
      expect(status).toHaveProperty('remainingAttempts');
      expect(status).toHaveProperty('windowMs');
      expect(status).toHaveProperty('resetTime');
    });

    test('should reflect recorded attempts', () => {
      recordFailedAuth(mockReq, 'login');
      recordFailedAuth(mockReq, 'login');

      const status = getRateLimitStatus(mockReq, 'login');

      expect(status.attempts).toBe(2);
      expect(status.remainingAttempts).toBe(3);
    });
  });

  describe('clearRateLimitStore', () => {
    test('should clear all rate limit data', () => {
      recordFailedAuth(mockReq, 'login');
      recordFailedAuth(mockReq, 'login');

      clearRateLimitStore();

      const status = getRateLimitStatus(mockReq, 'login');
      expect(status.attempts).toBe(0);
      expect(status.locked).toBe(false);
    });
  });
});

describe('Brute Force Protection - Login Failures', () => {
  let mockReq;
  let mockRes;
  let mockNext;

  beforeEach(() => {
    clearRateLimitStore();
    
    mockReq = {
      ip: '10.0.0.1',
      connection: { remoteAddress: '10.0.0.1' },
      headers: { 'user-agent': 'BruteForceBot/1.0' },
      method: 'POST',
    };
    mockRes = {
      _headers: {},
      setHeader: function(name, value) {
        this._headers[name.toLowerCase()] = value;
      },
      getHeader: function(name) {
        return this._headers[name.toLowerCase()];
      },
      statusCode: 200,
      status: function(code) {
        this.statusCode = code;
        return this;
      },
      json: jest.fn(function(data) { return data; }),
    };
    mockNext = jest.fn();
  });

  test('should block login after 5 failed attempts', () => {
    const loginLimiter = createRateLimiter({ 
      type: 'login',
      recordOnRequest: false
    });

    // Make 5 failed login attempts via recordFailedAuth
    for (let i = 0; i < 5; i++) {
      recordFailedAuth(mockReq, 'login');
    }

    // Next request should be blocked
    loginLimiter(mockReq, mockRes, mockNext);

    expect(mockNext).not.toHaveBeenCalled();
    expect(mockRes.statusCode).toBe(429);
    expect(mockRes.getHeader('x-ratelimit-remaining')).toBe(0);
  });

  test('should reset counter after successful login', () => {
    const loginLimiter = createRateLimiter({ 
      type: 'login',
      recordOnRequest: false
    });

    // Make 3 failed attempts
    for (let i = 0; i < 3; i++) {
      recordFailedAuth(mockReq, 'login');
    }

    // Successful login
    clearFailedAuth(mockReq, 'login');

    // Should have full quota again
    mockRes.statusCode = 200;
    loginLimiter(mockReq, mockRes, mockNext);

    expect(mockNext).toHaveBeenCalled();
    expect(mockRes.getHeader('x-ratelimit-remaining')).toBe(5);
  });

  test('should maintain separate limits per IP', () => {
    const loginLimiter = createRateLimiter({ 
      type: 'login',
      recordOnRequest: false
    });

    const req1 = { ...mockReq, ip: '10.0.0.1' };
    const req2 = { ...mockReq, ip: '10.0.0.2' };

    // Make 5 failed attempts from IP1
    for (let i = 0; i < 5; i++) {
      recordFailedAuth(req1, 'login');
    }

    // IP1 should be blocked
    loginLimiter(req1, mockRes, mockNext);
    expect(mockNext).not.toHaveBeenCalled();

    // IP2 should still be allowed
    mockNext.mockClear();
    loginLimiter(req2, mockRes, mockNext);
    expect(mockNext).toHaveBeenCalled();
  });

  test('should include lockout duration in response', () => {
    // Simulate lockout directly
    const key = generateKey(mockReq, 'login');
    const lockoutKey = `${key}:lockout`;
    rateLimitStore.set(lockoutKey, Date.now() + 60000);

    const loginLimiter = createRateLimiter({
      type: 'login',
      recordOnRequest: false,
    });

    // Request should be blocked
    mockRes.statusCode = 200;
    loginLimiter(mockReq, mockRes, mockNext);

    expect(mockRes.statusCode).toBe(429);
    expect(mockRes.json).toHaveBeenCalled();
    const lastCall = mockRes.json.mock.calls[mockRes.json.mock.calls.length - 1][0];
    expect(lastCall.retryAfter).toBeDefined();
  });
});
