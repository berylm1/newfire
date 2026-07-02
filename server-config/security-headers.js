/**
 * Security Headers Middleware
 * 
 * Comprehensive security headers configuration using helmet patterns.
 * These headers protect against common web vulnerabilities.
 */

const CSP_POLICY = process.env.CSP_POLICY || {
  'default-src': ["'self'"],
  'script-src': ["'self'", "'strict-dynamic'", 'https:'],
  'style-src': ["'self'", "'unsafe-inline'", 'https:'],
  'img-src': ["'self'", 'data:', 'https:'],
  'font-src': ["'self'", 'https:'],
  'connect-src': ["'self'", 'https://api.openrouter.ai', 'https://api.opencl.ai'],
  'frame-ancestors': ["'none'"],
  'form-action': ["'self'"],
  'base-uri': ["'self'"],
  'object-src': ["'none'"],
};

/**
 * Convert CSP object to string
 */
function cspToString(policy) {
  if (typeof policy === 'string') return policy;
  return Object.entries(policy)
    .map(([directive, values]) => {
      if (Array.isArray(values)) {
        return `${directive} ${values.join(' ')}`;
      }
      return `${directive} ${values}`;
    })
    .join('; ');
}

/**
 * Security headers configuration
 */
const SECURITY_HEADERS = {
  // Prevent clickjacking
  'X-Frame-Options': process.env.X_FRAME_OPTIONS || 'DENY',
  
  // XSS Protection (legacy but still useful for older browsers)
  'X-XSS-Protection': '1; mode=block',
  
  // MIME Type Sniffing Protection
  'X-Content-Type-Options': 'nosniff',
  
  // Referrer Policy
  'Referrer-Policy': process.env.REFERRER_POLICY || 'strict-origin-when-cross-origin',
  
  // Permissions Policy (restrict browser features)
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(self)',
  
  // Content Security Policy
  'Content-Security-Policy': cspToString(CSP_POLICY),
};

/**
 * HSTS (HTTP Strict Transport Security) configuration
 * Only enable in production - requires valid HTTPS
 */
const HSTS_CONFIG = {
  maxAge: process.env.HSTS_MAX_AGE || 31536000, // 1 year in seconds
  includeSubDomains: true,
  preload: true,
};

/**
 * Create security headers middleware
 * @param {Object} options - Configuration options
 * @param {Object} [options.customHeaders] - Custom header overrides
 * @param {boolean} [options.includeHSTS] - Include HSTS header
 * @param {boolean} [options.strictMode] - Enable strict security mode
 * @returns {Function} Express middleware
 */
function createSecurityHeadersMiddleware(options = {}) {
  const {
    customHeaders = {},
    includeHSTS = process.env.NODE_ENV === 'production',
    strictMode = process.env.NODE_ENV === 'production',
  } = options;

  const headers = { ...SECURITY_HEADERS, ...customHeaders };

  // Add HSTS header if enabled
  if (includeHSTS) {
    const hstsValue = HSTS_CONFIG.includeSubDomains
      ? `max-age=${HSTS_CONFIG.maxAge}; includeSubDomains; preload`
      : `max-age=${HSTS_CONFIG.maxAge}`;
    headers['Strict-Transport-Security'] = hstsValue;
  }

  return (req, res, next) => {
    // Set all security headers
    Object.entries(headers).forEach(([header, value]) => {
      res.setHeader(header, value);
    });

    // Remove version exposure headers
    res.removeHeader('X-Powered-By');
    res.removeHeader('Server');

    next();
  };
}

/**
 * Standard security headers middleware with defaults
 */
const securityHeadersMiddleware = createSecurityHeadersMiddleware();

/**
 * Strict security headers for API endpoints
 */
function createApiSecurityMiddleware() {
  return createSecurityHeadersMiddleware({
    includeHSTS: true,
    strictMode: true,
    customHeaders: {
      // More restrictive CSP for API
      'Content-Security-Policy': "default-src 'none'; script-src 'none'; style-src 'none'",
      // Don't cache API responses
      'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0',
      'Pragma': 'no-cache',
    },
  });
}

/**
 * Headers to remove for security (information disclosure)
 */
const HEADERS_TO_REMOVE = [
  'X-Powered-By',
  'Server',
  'X-AspNet-Version',
  'X-AspNetMvc-Version',
  'X-Generator',
];

/**
 * Middleware to remove information disclosure headers
 */
function removeVersionHeaders(req, res, next) {
  HEADERS_TO_REMOVE.forEach(header => {
    res.removeHeader(header);
  });
  next();
}

module.exports = {
  createSecurityHeadersMiddleware,
  securityHeadersMiddleware,
  createApiSecurityMiddleware,
  removeVersionHeaders,
  SECURITY_HEADERS,
  CSP_POLICY,
  HSTS_CONFIG,
  HEADERS_TO_REMOVE,
  cspToString,
};
