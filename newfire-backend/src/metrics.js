import client from 'prom-client'

const register = new client.Registry()
register.setDefaultLabels({ service: 'newfire-backend' })
client.collectDefaultMetrics({ register })

const httpRequestsTotal = new client.Counter({
  name: 'http_requests_total',
  help: 'Total HTTP requests handled, labeled by method/route/status_code',
  labelNames: ['method', 'route', 'status_code'],
  registers: [register],
})

const httpRequestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request latency in seconds, labeled by method/route/status_code',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60],
  registers: [register],
})

const chatRequestsTotal = new client.Counter({
  name: 'chat_requests_total',
  help: 'Chat requests by provider and status',
  labelNames: ['provider', 'status'],
  registers: [register],
})

const chatRequestDuration = new client.Histogram({
  name: 'chat_request_duration_seconds',
  help: 'Chat request latency in seconds, labeled by provider',
  labelNames: ['provider'],
  buckets: [0.5, 1, 2, 5, 10, 20, 30, 60, 120],
  registers: [register],
})

// Express middleware. Records duration and count once the response is finished.
// Route normalization uses req.route?.path so :param segments don't explode the
// label cardinality (e.g., /chat/:agentId, not /chat/marketing-head-agent).
export function httpMetricsMiddleware(req, res, next) {
  const start = process.hrtime.bigint()
  res.on('finish', () => {
    const route = req.route?.path
      ? (req.baseUrl || '') + req.route.path
      : (req.path || 'unknown').replace(/\/[0-9]+(?=\/|$)/g, '/:id')
    const seconds = Number(process.hrtime.bigint() - start) / 1e9
    const labels = { method: req.method, route, status_code: String(res.statusCode) }
    httpRequestsTotal.inc(labels)
    httpRequestDuration.observe(labels, seconds)
  })
  next()
}

export function recordChat(provider, status, durationMs) {
  chatRequestsTotal.inc({ provider: provider || 'unknown', status })
  chatRequestDuration.observe({ provider: provider || 'unknown' }, durationMs / 1000)
}

export async function metricsHandler(_req, res) {
  res.set('Content-Type', register.contentType)
  res.send(await register.metrics())
}
