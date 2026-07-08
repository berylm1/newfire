/**
 * Security Headers Middleware Tests
 * 
 * Tests for security headers configuration and enforcement.
 */

const {
  createSecurityHeadersMiddleware,
  securityHeadersMiddleware,
  createApiSecurityMiddleware,
  removeVersionHeaders,
  SECURITY_HEADERS,
  HEADERS_TO_REMOVE,
  cspToString,
} = require('../../security-headers');

describe('Security Headers Middleware', () => {
  let mockReq;
  let mockRes;
  let mockNext;

  beforeEach(() => {
    mockReq = {
      headers: {},
    };
    mockRes = {
      _headers: {},
      setHeader: function(name, value) {
        this._headers[name.toLowerCase()] = value;
      },
      getHeader: function(name) {
        return this._headers[name.toLowerCase()];
      },
      removeHeader: function(name) {
        delete this._headers[name.toLowerCase()];
      },
    };
    mockNext = jest.fn();
  });

  describe('SECURITY_HEADERS', () => {
    test('should include X-Frame-Options', () => {
      expect(SECURITY_HEADERS['X-Frame-Options']).toBeDefined();
      expect(SECURITY_HEADERS['X-Frame-Options']).toBe('DENY');
    });

    test('should include X-XSS-Protection', () => {
      expect(SECURITY_HEADERS['X-XSS-Protection']).toBe('1; mode=block');
    });

    test('should include X-Content-Type-Options', () => {
      expect(SECURITY_HEADERS['X-Content-Type-Options']).toBe('nosniff');
    });

    test('should include Referrer-Policy', () => {
      expect(SECURITY_HEADERS['Referrer-Policy']).toBeDefined();
    });

    test('should include Permissions-Policy', () => {
      expect(SECURITY_HEADERS['Permissions-Policy']).toBeDefined();
      expect(SECURITY_HEADERS['Permissions-Policy']).toContain('camera=()');
    });

    test('should include Content-Security-Policy', () => {
      expect(SECURITY_HEADERS['Content-Security-Policy']).toBeDefined();
    });
  });

  describe('createSecurityHeadersMiddleware', () => {
    test('should set all security headers', () => {
      const middleware = createSecurityHeadersMiddleware();

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('x-frame-options')).toBe('DENY');
      expect(mockRes.getHeader('x-xss-protection')).toBe('1; mode=block');
      expect(mockRes.getHeader('x-content-type-options')).toBe('nosniff');
      expect(mockRes.getHeader('referrer-policy')).toBeDefined();
      expect(mockRes.getHeader('permissions-policy')).toBeDefined();
      expect(mockRes.getHeader('content-security-policy')).toBeDefined();
      expect(mockNext).toHaveBeenCalled();
    });

    test('should add HSTS header in production', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      const middleware = createSecurityHeadersMiddleware();

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('strict-transport-security')).toContain('max-age=');
      expect(mockRes.getHeader('strict-transport-security')).toContain('includeSubDomains');

      process.env.NODE_ENV = originalEnv;
    });

    test('should not add HSTS header in development', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      const middleware = createSecurityHeadersMiddleware();

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('strict-transport-security')).toBeUndefined();

      process.env.NODE_ENV = originalEnv;
    });

    test('should respect custom headers override', () => {
      const middleware = createSecurityHeadersMiddleware({
        customHeaders: {
          'X-Frame-Options': 'SAMEORIGIN',
        },
      });

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('x-frame-options')).toBe('SAMEORIGIN');
    });

    test('should remove version headers', () => {
      // Set some headers that should be removed
      mockRes.setHeader('X-Powered-By', 'Express');
      mockRes.setHeader('Server', 'Apache');

      const middleware = createSecurityHeadersMiddleware();

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('x-powered-by')).toBeUndefined();
      expect(mockRes.getHeader('server')).toBeUndefined();
    });
  });

  describe('createApiSecurityMiddleware', () => {
    test('should set restrictive CSP for API', () => {
      const middleware = createApiSecurityMiddleware();

      middleware(mockReq, mockRes, mockNext);

      const csp = mockRes.getHeader('content-security-policy');
      expect(csp).toContain("default-src 'none'");
      expect(csp).toContain("script-src 'none'");
    });

    test('should set no-cache headers', () => {
      const middleware = createApiSecurityMiddleware();

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('cache-control')).toContain('no-store');
      expect(mockRes.getHeader('pragma')).toBe('no-cache');
    });
  });

  describe('removeVersionHeaders', () => {
    test('should remove information disclosure headers', () => {
      mockRes.setHeader('X-Powered-By', 'Express/4.18');
      mockRes.setHeader('Server', 'Apache/2.4');
      mockRes.setHeader('X-AspNet-Version', '4.0.30319');

      removeVersionHeaders(mockReq, mockRes, mockNext);

      HEADERS_TO_REMOVE.forEach(header => {
        expect(mockRes.getHeader(header.toLowerCase())).toBeUndefined();
      });
      expect(mockNext).toHaveBeenCalled();
    });
  });

  describe('cspToString', () => {
    test('should convert CSP object to string', () => {
      const policy = {
        'default-src': ["'self'"],
        'script-src': ["'self'", 'https:'],
      };

      const result = cspToString(policy);

      expect(result).toContain("default-src 'self'");
      expect(result).toContain("script-src 'self' https:");
      expect(result).toContain(';');
    });

    test('should return string as-is', () => {
      const policy = "default-src 'self'";

      const result = cspToString(policy);

      expect(result).toBe(policy);
    });

    test('should handle non-array values', () => {
      const policy = {
        'base-uri': "'self'",
      };

      const result = cspToString(policy);

      expect(result).toContain("base-uri 'self'");
    });
  });
});
