import crypto from 'node:crypto'
import cors from 'cors'
import helmet from 'helmet'
import { rateLimit, ipKeyGenerator } from 'express-rate-limit'

export const DEFAULT_ALLOWED_ORIGINS = [
  'https://newfire.app',
  'https://www.newfire.app',
  'http://localhost:3000',
  'http://localhost:5173',
]

export function parseAllowedOrigins(value = process.env.CORS_ALLOWED_ORIGINS || process.env.ALLOWED_ORIGINS) {
  if (!value || !value.trim()) return DEFAULT_ALLOWED_ORIGINS
  return value
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean)
}

export function buildCorsOptions(allowedOrigins = parseAllowedOrigins()) {
  const allowed = new Set(allowedOrigins)
  return {
    origin(origin, callback) {
      // Non-browser clients, Prometheus, curl, and health checks often send no Origin.
      if (!origin) return callback(null, true)
      if (allowed.has(origin)) return callback(null, true)
      return callback(new Error('CORS origin not allowed'), false)
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Authorization', 'Content-Type', 'X-Request-ID'],
    exposedHeaders: ['X-Request-ID'],
    maxAge: 600,
  }
}

export function requestIdMiddleware(req, res, next) {
  const incoming = req.get?.('X-Request-ID') || req.headers?.['x-request-id']
  const requestId = typeof incoming === 'string' && incoming.length <= 128
    ? incoming
    : crypto.randomUUID()
  req.requestId = requestId
  res.setHeader('X-Request-ID', requestId)
  next()
}

export function createRateLimiter({
  windowMs,
  limit,
  message,
  skip,
  standardHeaders = 'draft-8',
  legacyHeaders = false,
}) {
  return rateLimit({
    windowMs,
    limit,
    standardHeaders,
    legacyHeaders,
    message: { error: message },
    skip,
    keyGenerator(req) {
      return ipKeyGenerator(req.ip || req.socket?.remoteAddress || 'unknown')
    },
  })
}

export const authRateLimiter = createRateLimiter({
  windowMs: Number(process.env.AUTH_RATE_LIMIT_WINDOW_MS || 15 * 60 * 1000),
  limit: Number(process.env.AUTH_RATE_LIMIT_MAX || 20),
  message: 'auth_rate_limit_exceeded',
})

export const apiRateLimiter = createRateLimiter({
  windowMs: Number(process.env.API_RATE_LIMIT_WINDOW_MS || 60 * 1000),
  limit: Number(process.env.API_RATE_LIMIT_MAX || 300),
  message: 'api_rate_limit_exceeded',
  skip(req) {
    return req.path === '/health' || req.path === '/metrics'
  },
})

export function applySecurityMiddleware(app) {
  app.disable('x-powered-by')
  app.set('trust proxy', Number(process.env.TRUST_PROXY_HOPS || 1))
  app.use(requestIdMiddleware)
  app.use(helmet({
    crossOriginResourcePolicy: { policy: 'cross-origin' },
  }))
  app.use(cors(buildCorsOptions()))
  app.use(apiRateLimiter)
}
