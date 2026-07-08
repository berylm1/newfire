/**
 * CORS Middleware Tests
 * 
 * Tests for allowed/disallowed origins and CORS policy enforcement.
 */

const {
  createCorsMiddleware,
  corsMiddleware,
  createStrictCorsMiddleware,
  isOriginAllowed,
  ALLOWED_ORIGINS,
} = require('../../cors');

describe('CORS Middleware', () => {
  let mockReq;
  let mockRes;
  let mockNext;

  beforeEach(() => {
    mockReq = {
      headers: {},
      method: 'GET',
    };
    mockRes = {
      statusCode: 200,
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
      status: function(code) {
        this.statusCode = code;
        return this;
      },
      json: jest.fn(function(data) { return data; }),
      end: jest.fn(function() { return this; }),
    };
    mockNext = jest.fn();
  });

  describe('isOriginAllowed', () => {
    test('should allow localhost in development', () => {
      expect(isOriginAllowed('http://localhost:3000')).toBe(true);
      expect(isOriginAllowed('http://localhost:4000')).toBe(true);
      expect(isOriginAllowed('http://127.0.0.1:3000')).toBe(true);
    });

    test('should allow null origin for non-browser requests', () => {
      expect(isOriginAllowed('null')).toBe(true);
    });

    test('should reject unknown origins', () => {
      expect(isOriginAllowed('https://malicious-site.com')).toBe(false);
      expect(isOriginAllowed('https://attacker.io')).toBe(false);
    });

    test('should return false for undefined/null origin', () => {
      expect(isOriginAllowed(undefined)).toBe(false);
      expect(isOriginAllowed(null)).toBe(false);
      expect(isOriginAllowed('')).toBe(false);
    });
  });

  describe('createCorsMiddleware', () => {
    test('should set CORS headers for allowed origin', () => {
      const middleware = createCorsMiddleware();
      mockReq.headers.origin = 'http://localhost:3000';

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('Access-Control-Allow-Origin')).toBe('http://localhost:3000');
      expect(mockNext).toHaveBeenCalled();
    });

    test('should set Vary header for origin', () => {
      const middleware = createCorsMiddleware();
      mockReq.headers.origin = 'http://localhost:3000';

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('Vary')).toBe('Origin');
    });

    test('should set expose headers', () => {
      const middleware = createCorsMiddleware();
      mockReq.headers.origin = 'http://localhost:3000';

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('Access-Control-Expose-Headers')).toContain('X-Request-ID');
      expect(mockRes.getHeader('Access-Control-Expose-Headers')).toContain('X-RateLimit-Limit');
    });

    test('should handle preflight OPTIONS request', () => {
      const middleware = createCorsMiddleware();
      mockReq.method = 'OPTIONS';
      mockReq.headers.origin = 'http://localhost:3000';

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('Access-Control-Allow-Methods')).toBe('GET, POST, PUT, PATCH, DELETE, OPTIONS');
      expect(mockRes.getHeader('Access-Control-Allow-Headers')).toBe('Content-Type, Authorization, X-Requested-With, X-Request-ID, Accept-Language');
      expect(mockRes.getHeader('Access-Control-Max-Age')).toBe('86400');
      expect(mockRes.statusCode).toBe(204);
    });

    test('should reject disallowed origin in production', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';
      
      const middleware = createCorsMiddleware();
      mockReq.headers.origin = 'https://malicious-site.com';

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.statusCode).toBe(403);
      expect(mockRes.json).toHaveBeenCalledWith(expect.objectContaining({
        error: 'CORS policy violation',
      }));

      process.env.NODE_ENV = originalEnv;
    });

    test('should allow disallowed origin in development with warning', () => {
      const originalEnv = process.env.NODE_ENV;
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      process.env.NODE_ENV = 'development';
      
      const middleware = createCorsMiddleware();
      mockReq.headers.origin = 'https://unknown-site.com';

      middleware(mockReq, mockRes, mockNext);

      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('CORS violation attempt'));
      expect(mockNext).toHaveBeenCalled();

      consoleSpy.mockRestore();
      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('Custom configuration', () => {
    test('should respect custom allowed origins', () => {
      const customOrigins = ['https://newfire.app', 'https://app.newfire.com'];
      const middleware = createCorsMiddleware({ allowedOrigins: customOrigins });
      
      mockReq.headers.origin = 'https://newfire.app';
      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('Access-Control-Allow-Origin')).toBe('https://newfire.app');
      expect(mockNext).toHaveBeenCalled();
    });

    test('should reject origin not in custom allowlist', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';
      
      const customOrigins = ['https://newfire.app'];
      const middleware = createCorsMiddleware({ allowedOrigins: customOrigins });
      
      mockReq.headers.origin = 'https://evil.com';
      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.statusCode).toBe(403);

      process.env.NODE_ENV = originalEnv;
    });

    test('should respect custom max age', () => {
      const middleware = createCorsMiddleware({ maxAge: 3600 });
      mockReq.method = 'OPTIONS';
      mockReq.headers.origin = 'http://localhost:3000';

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('Access-Control-Max-Age')).toBe('3600');
    });
  });

  describe('createStrictCorsMiddleware', () => {
    test('should create middleware with strict production origins', () => {
      const middleware = createStrictCorsMiddleware();
      mockReq.headers.origin = 'https://newfire.app';

      middleware(mockReq, mockRes, mockNext);

      expect(mockRes.getHeader('Access-Control-Allow-Origin')).toBe('https://newfire.app');
      expect(mockNext).toHaveBeenCalled();
    });
  });
});
