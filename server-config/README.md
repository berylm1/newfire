# Server Security Configuration

Production-ready security middleware for Express.js backend.

## Features

- **CORS Allowlist**: Explicit origin validation with production-safe defaults
- **Security Headers**: Comprehensive security headers (helmet-compatible)
- **Auth Rate Limiting**: Protection against brute force attacks on authentication endpoints

## Installation

```bash
npm install
```

## Usage

### Apply All Security Middleware

```javascript
const express = require('express');
const {
  corsMiddleware,
  securityHeadersMiddleware,
  loginRateLimiter,
  authRateLimiter,
} = require('./server-config');

const app = express();

// Apply security middleware
app.use(corsMiddleware);
app.use(securityHeadersMiddleware);

// Apply rate limiting to auth endpoints
app.post('/login', loginRateLimiter, authController.login);
app.post('/signup', signupRateLimiter, authController.signup);
app.post('/password-reset', passwordResetRateLimiter, authController.resetPassword);
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed origins | localhost dev origins |
| `NODE_ENV` | Environment mode | development |
| `X_FRAME_OPTIONS` | X-Frame-Options header value | DENY |
| `REFERRER_POLICY` | Referrer-Policy header value | strict-origin-when-cross-origin |
| `HSTS_MAX_AGE` | HSTS max-age in seconds | 31536000 (1 year) |
| `CSP_POLICY` | Content-Security-Policy (JSON object) | restrictive defaults |

### Custom Configuration

```javascript
const { createCorsMiddleware, createSecurityHeadersMiddleware, createRateLimiter } = require('./server-config');

// Custom CORS
const customCors = createCorsMiddleware({
  allowedOrigins: ['https://myapp.com', 'https://app.myapp.com'],
  maxAge: 3600,
});

// Custom Security Headers
const customHeaders = createSecurityHeadersMiddleware({
  customHeaders: {
    'X-Frame-Options': 'SAMEORIGIN',
  },
  includeHSTS: true,
});

// Custom Rate Limiter
const customLimiter = createRateLimiter({
  type: 'login',
  config: {
    windowMs: 10 * 60 * 1000, // 10 minutes
    maxAttempts: 3,
    lockoutDurationMs: 30 * 60 * 1000, // 30 minutes
  },
});
```

## Rate Limiting Configuration

```javascript
const { recordFailedAuth, clearFailedAuth, getRateLimitStatus } = require('./server-config');

// In your auth controller
async function login(req, res) {
  try {
    const user = await authenticate(req.body);
    
    // Clear rate limits on success
    clearFailedAuth(req, 'login');
    
    return res.json({ token: user.token });
  } catch (error) {
    // Record failed attempt
    const status = recordFailedAuth(req, 'login');
    
    if (status.isLockedOut) {
      return res.status(429).json({
        error: 'Account locked',
        message: 'Too many failed attempts. Try again later.',
        retryAfter: Math.ceil(status.lockoutExpires - Date.now()) / 1000,
      });
    }
    
    return res.status(401).json({
      error: 'Invalid credentials',
      remainingAttempts: status.remainingAttempts,
    });
  }
}
```

## Testing

```bash
npm test
```

## Security Headers Applied

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Frame-Options` | DENY | Prevent clickjacking |
| `X-XSS-Protection` | 1; mode=block | XSS filtering |
| `X-Content-Type-Options` | nosniff | Prevent MIME sniffing |
| `Referrer-Policy` | strict-origin-when-cross-origin | Control referrer info |
| `Permissions-Policy` | Restricts camera, mic, geolocation | Feature policy |
| `Content-Security-Policy` | Strict defaults | Prevent XSS/injection |
| `Strict-Transport-Security` | max-age=31536000; includeSubDomains; preload | HSTS (production only) |

## License

MIT
