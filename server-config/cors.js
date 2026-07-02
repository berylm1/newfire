/**
 * CORS Allowlist Middleware
 * 
 * Production-safe CORS configuration with explicit allowlist.
 * Replace ALLOWED_ORIGINS with actual production domains.
 */

const ALLOWED_ORIGINS = process.env.CORS_ALLOWED_ORIGINS
  ? process.env.CORS_ALLOWED_ORIGINS.split(',')
  : [
      // Local development
      'http://localhost:3000',
      'http://localhost:4000',
      'http://127.0.0.1:3000',
      'http://127.0.0.1:4000',
    ];

const ALLOWED_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'];

const ALLOWED_HEADERS = [
  'Content-Type',
  'Authorization',
  'X-Requested-With',
  'X-Request-ID',
  'Accept-Language',
];

const EXPOSED_HEADERS = [
  'X-Request-ID',
  'X-RateLimit-Limit',
  'X-RateLimit-Remaining',
  'X-RateLimit-Reset',
];

const MAX_AGE_SECONDS = 86400; // 24 hours

/**
 * Validate origin against allowlist
 * @param {string} origin - The origin from the request header
 * @returns {boolean} - Whether the origin is allowed
 */
function isOriginAllowed(origin) {
  if (!origin) return false;
  
  // Allow null origin for non-browser requests (curl, Postman, etc.)
  if (origin === 'null') return true;
  
  return ALLOWED_ORIGINS.includes(origin);
}

/**
 * CORS middleware factory
 * @param {Object} options - Configuration options
 * @param {string[]} [options.allowedOrigins] - Override allowed origins
 * @param {string[]} [options.allowedMethods] - Override allowed methods
 * @param {string[]} [options.allowedHeaders] - Override allowed headers
 * @param {string[]} [options.exposedHeaders] - Headers to expose to client
 * @param {number} [options.maxAge] - Preflight cache duration
 * @returns {Function} Express middleware
 */
function createCorsMiddleware(options = {}) {
  const origins = options.allowedOrigins || ALLOWED_ORIGINS;
  const methods = options.allowedMethods || ALLOWED_METHODS;
  const headers = options.allowedHeaders || ALLOWED_HEADERS;
  const exposed = options.exposedHeaders || EXPOSED_HEADERS;
  const maxAge = options.maxAge || MAX_AGE_SECONDS;

  return (req, res, next) => {
    const origin = req.headers.origin;
    const isPreflight = req.method === 'OPTIONS';

    // Check if origin is allowed
    if (origin && !origins.includes(origin)) {
      // Log potential CORS violation
      console.warn(`CORS violation attempt from origin: ${origin}`);
      
      // In production, reject the request
      if (process.env.NODE_ENV === 'production') {
        return res.status(403).json({
          error: 'CORS policy violation',
          message: 'Origin not allowed'
        });
      }
    }

    // Set CORS headers
    if (origin && origins.includes(origin)) {
      res.setHeader('Access-Control-Allow-Origin', origin);
    }

    if (exposed.length > 0) {
      res.setHeader('Access-Control-Expose-Headers', exposed.join(', '));
    }

    if (isPreflight) {
      res.setHeader('Access-Control-Allow-Methods', methods.join(', '));
      res.setHeader('Access-Control-Allow-Headers', headers.join(', '));
      res.setHeader('Access-Control-Max-Age', String(maxAge));

      // Add Vary header to indicate origin varies
      res.setHeader('Vary', 'Origin');

      return res.status(204).end();
    }

    // Add Vary header for non-preflight requests
    if (origin) {
      res.setHeader('Vary', 'Origin');
    }

    next();
  };
}

/**
 * Express CORS middleware with default configuration
 */
const corsMiddleware = createCorsMiddleware();

/**
 * Create strict CORS middleware for sensitive endpoints
 */
function createStrictCorsMiddleware(allowedOrigins) {
  return createCorsMiddleware({
    allowedOrigins: allowedOrigins || [
      'https://newfire.app',
      'https://www.newfire.app',
    ],
    maxAge: 3600, // 1 hour for stricter prefetch
  });
}

module.exports = {
  createCorsMiddleware,
  corsMiddleware,
  createStrictCorsMiddleware,
  isOriginAllowed,
  ALLOWED_ORIGINS,
  ALLOWED_METHODS,
  ALLOWED_HEADERS,
  EXPOSED_HEADERS,
  MAX_AGE_SECONDS,
};
