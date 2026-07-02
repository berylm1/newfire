/**
 * Auth Rate Limiting Middleware
 * 
 * Protection against brute force attacks on authentication endpoints.
 * Implements sliding window rate limiting with memory store (production should use Redis).
 */

const crypto = require('crypto');

// In-memory store for rate limiting (use Redis in production)
const rateLimitStore = new Map();

/**
 * Configuration defaults
 */
const DEFAULT_CONFIG = {
  // Auth endpoint limits (more restrictive)
  auth: {
    windowMs: 15 * 60 * 1000,     // 15 minutes
    maxAttempts: 5,                // 5 attempts per window
    lockoutDurationMs: 15 * 60 * 1000, // 15 minute lockout after max attempts
  },
  
  // Login specific limits
  login: {
    windowMs: 15 * 60 * 1000,     // 15 minutes
    maxAttempts: 5,
    lockoutDurationMs: 30 * 60 * 1000, // 30 minute lockout for login
  },
  
  // Password reset limits
  passwordReset: {
    windowMs: 60 * 60 * 1000,     // 1 hour
    maxAttempts: 3,
    lockoutDurationMs: 60 * 60 * 1000, // 1 hour lockout
  },
  
  // Signup limits
  signup: {
    windowMs: 60 * 60 * 1000,     // 1 hour
    maxAttempts: 5,
    lockoutDurationMs: 24 * 60 * 60 * 1000, // 24 hour lockout
  },
  
  // General API limits (less restrictive)
  general: {
    windowMs: 60 * 1000,          // 1 minute
    maxRequests: 60,
  },
};

/**
 * Generate rate limit key
 */
function generateKey(req, type = 'auth') {
  const identifier = req.ip || req.connection.remoteAddress || 'unknown';
  const userAgent = req.headers['user-agent'] || '';
  const keyBase = `${type}:${identifier}:${userAgent.substring(0, 50)}`;
  return crypto.createHash('sha256').update(keyBase).digest('hex').substring(0, 32);
}

/**
 * Check if IP is locked out
 */
function isLockedOut(key, config) {
  const lockoutKey = `${key}:lockout`;
  const lockoutExpiry = rateLimitStore.get(lockoutKey);
  
  if (lockoutExpiry && lockoutExpiry > Date.now()) {
    return {
      locked: true,
      remainingMs: lockoutExpiry - Date.now(),
    };
  }
  
  // Clean up expired lockout
  if (lockoutExpiry) {
    rateLimitStore.delete(lockoutKey);
  }
  
  return { locked: false };
}

/**
 * Get current attempt count
 */
function getAttemptCount(key, config) {
  const windowStart = Date.now() - config.windowMs;
  const attemptKey = `${key}:attempts`;
  
  const attempts = rateLimitStore.get(attemptKey) || [];
  const validAttempts = attempts.filter(ts => ts > windowStart);
  
  if (validAttempts.length !== attempts.length) {
    rateLimitStore.set(attemptKey, validAttempts);
  }
  
  return validAttempts.length;
}

/**
 * Record an attempt
 */
function recordAttempt(key, config) {
  const attemptKey = `${key}:attempts`;
  const attempts = rateLimitStore.get(attemptKey) || [];
  attempts.push(Date.now());
  rateLimitStore.set(attemptKey, attempts);
  
  // Check if lockout should be triggered
  const count = attempts.length;
  if (count >= config.maxAttempts) {
    const lockoutKey = `${key}:lockout`;
    rateLimitStore.set(lockoutKey, Date.now() + config.lockoutDurationMs);
  }
}

/**
 * Clear attempts (on successful login)
 */
function clearAttempts(key) {
  const attemptKey = `${key}:attempts`;
  rateLimitStore.delete(attemptKey);
  const lockoutKey = `${key}:lockout`;
  rateLimitStore.delete(lockoutKey);
}

/**
 * Create rate limiter middleware
 * @param {Object} options - Configuration options
 * @param {string} [options.type] - Type of rate limit ('auth', 'login', 'passwordReset', 'signup', 'general')
 * @param {Object} [options.config] - Custom config for the rate limiter
 * @param {Function} [options.keyGenerator] - Custom key generator
 * @param {Function} [options.handler] - Custom handler for rate limit exceeded
 * @param {Function} [options.recordOnRequest] - Whether to record each request (default: true for passive check)
 * @returns {Function} Express middleware
 */
function createRateLimiter(options = {}) {
  const {
    type = 'auth',
    config = DEFAULT_CONFIG[type] || DEFAULT_CONFIG.auth,
    keyGenerator = (req) => generateKey(req, type),
    handler,
    recordOnRequest = true,
  } = options;

  return (req, res, next) => {
    const key = keyGenerator(req);
    
    // Check lockout status
    const lockoutStatus = isLockedOut(key, config);
    if (lockoutStatus.locked) {
      const retryAfter = Math.ceil(lockoutStatus.remainingMs / 1000);
      
      // Set rate limit headers
      res.setHeader('X-RateLimit-Limit', config.maxAttempts || config.maxRequests);
      res.setHeader('X-RateLimit-Remaining', 0);
      res.setHeader('X-RateLimit-Reset', Math.ceil((Date.now() + lockoutStatus.remainingMs) / 1000));
      res.setHeader('Retry-After', retryAfter);
      
      if (handler) {
        return handler(req, res, next, {
          locked: true,
          retryAfter,
          message: 'Too many attempts. Please try again later.',
        });
      }
      
      return res.status(429).json({
        error: 'Too Many Requests',
        message: 'Too many attempts. Please try again later.',
        retryAfter,
      });
    }
    
    // Record this request if enabled (for active tracking)
    if (recordOnRequest) {
      recordAttempt(key, config);
    }
    
    // Check current attempt count
    const attemptCount = getAttemptCount(key, config);
    const remaining = Math.max(0, (config.maxAttempts || config.maxRequests) - attemptCount);
    const resetTime = Date.now() + config.windowMs;
    
    // Set rate limit headers
    res.setHeader('X-RateLimit-Limit', config.maxAttempts || config.maxRequests);
    res.setHeader('X-RateLimit-Remaining', remaining);
    res.setHeader('X-RateLimit-Reset', Math.ceil(resetTime / 1000));
    
    next();
  };
}

/**
 * Record failed authentication attempt
 * Call this after failed login/signup
 */
function recordFailedAuth(req, type = 'auth') {
  const key = generateKey(req, type);
  const config = DEFAULT_CONFIG[type] || DEFAULT_CONFIG.auth;
  recordAttempt(key, config);
  
  const attemptCount = getAttemptCount(key, config);
  const isNowLockedOut = attemptCount >= config.maxAttempts;
  
  return {
    attemptCount,
    maxAttempts: config.maxAttempts,
    remainingAttempts: Math.max(0, config.maxAttempts - attemptCount),
    isLockedOut: isNowLockedOut,
    lockoutExpires: isNowLockedOut ? Date.now() + config.lockoutDurationMs : null,
  };
}

/**
 * Clear rate limit on successful authentication
 * Call this after successful login/signup
 */
function clearFailedAuth(req, type = 'auth') {
  const key = generateKey(req, type);
  clearAttempts(key);
}

/**
 * Get current rate limit status
 */
function getRateLimitStatus(req, type = 'auth') {
  const key = generateKey(req, type);
  const config = DEFAULT_CONFIG[type] || DEFAULT_CONFIG.auth;
  const lockoutStatus = isLockedOut(key, config);
  const attemptCount = getAttemptCount(key, config);
  
  return {
    locked: lockoutStatus.locked,
    attempts: attemptCount,
    maxAttempts: config.maxAttempts || config.maxRequests,
    remainingAttempts: Math.max(0, (config.maxAttempts || config.maxRequests) - attemptCount),
    windowMs: config.windowMs,
    resetTime: Date.now() + config.windowMs,
    lockoutRemainingMs: lockoutStatus.remainingMs || 0,
  };
}

/**
 * Pre-configured middleware for auth endpoints
 */
const authRateLimiter = createRateLimiter({ type: 'auth' });

/**
 * Pre-configured middleware for login endpoint
 */
const loginRateLimiter = createRateLimiter({ type: 'login' });

/**
 * Pre-configured middleware for password reset
 */
const passwordResetRateLimiter = createRateLimiter({ type: 'passwordReset' });

/**
 * Pre-configured middleware for signup
 */
const signupRateLimiter = createRateLimiter({ type: 'signup' });

/**
 * Clear rate limit store (for testing)
 */
function clearRateLimitStore() {
  rateLimitStore.clear();
}

module.exports = {
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
  // Export for testing
  rateLimitStore,
};
