/**
 * Server Security Configuration
 * 
 * Export all security middleware configurations.
 * Import this module in your Express server to apply security hardening.
 * 
 * Usage in server.js:
 * 
 * const { corsMiddleware, securityHeadersMiddleware, loginRateLimiter } = require('./server-config');
 * 
 * app.use(corsMiddleware);
 * app.use(securityHeadersMiddleware);
 * app.post('/login', loginRateLimiter, authController.login);
 */

const cors = require('./cors');
const securityHeaders = require('./security-headers');
const rateLimit = require('./rate-limit');

module.exports = {
  // CORS
  createCorsMiddleware: cors.createCorsMiddleware,
  corsMiddleware: cors.corsMiddleware,
  createStrictCorsMiddleware: cors.createStrictCorsMiddleware,
  isOriginAllowed: cors.isOriginAllowed,
  ALLOWED_ORIGINS: cors.ALLOWED_ORIGINS,
  
  // Security Headers
  createSecurityHeadersMiddleware: securityHeaders.createSecurityHeadersMiddleware,
  securityHeadersMiddleware: securityHeaders.securityHeadersMiddleware,
  createApiSecurityMiddleware: securityHeaders.createApiSecurityMiddleware,
  removeVersionHeaders: securityHeaders.removeVersionHeaders,
  SECURITY_HEADERS: securityHeaders.SECURITY_HEADERS,
  
  // Rate Limiting
  createRateLimiter: rateLimit.createRateLimiter,
  authRateLimiter: rateLimit.authRateLimiter,
  loginRateLimiter: rateLimit.loginRateLimiter,
  passwordResetRateLimiter: rateLimit.passwordResetRateLimiter,
  signupRateLimiter: rateLimit.signupRateLimiter,
  recordFailedAuth: rateLimit.recordFailedAuth,
  clearFailedAuth: rateLimit.clearFailedAuth,
  getRateLimitStatus: rateLimit.getRateLimitStatus,
  clearRateLimitStore: rateLimit.clearRateLimitStore,
  DEFAULT_CONFIG: rateLimit.DEFAULT_CONFIG,
};
