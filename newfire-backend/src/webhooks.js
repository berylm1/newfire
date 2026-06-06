import crypto from 'crypto'
import express from 'express'
import { query } from './db.js'

const EVENT_ENV_FALLBACKS = {
  'user.signup': 'N8N_HOOK_USER_SIGNUP',
  'user.onboarded': 'N8N_HOOK_USER_ONBOARDED',
  'subscription.upgraded': 'N8N_HOOK_SUBSCRIPTION_UPGRADED',
  'agent.created': 'N8N_HOOK_AGENT_CREATED',
  'agent.task.completed': 'N8N_HOOK_AGENT_TASK_COMPLETED',
}

// Exponential retry schedule for transient webhook failures. Final entry is
// the maximum total wait (sum) before we give up and log.
const RETRY_DELAYS_MS = [5_000, 10_000, 20_000, 40_000, 80_000]

async function resolveCompanyHookUrl(eventType, opts, payload) {
  let companyId = opts.companyId ?? payload?.company_id
  if (!companyId && payload?.user_id) {
    const r = await query('SELECT id FROM companies WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1', [payload.user_id])
    companyId = r.rows[0]?.id
  }
  if (!companyId) return null
  const r = await query('SELECT n8n_hooks FROM companies WHERE id = $1', [companyId])
  const hooks = r.rows[0]?.n8n_hooks || {}
  return hooks[eventType] || null
}

async function postWebhookOnce(url, body, headers) {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), 5_000)
  try {
    const r = await fetch(url, { method: 'POST', headers, body, signal: ctrl.signal })
    return { ok: r.ok, status: r.status }
  } finally {
    clearTimeout(t)
  }
}

// Fire-and-forget background retry. Each call gets its own loop so failures
// don't block other webhooks. Idempotency is the caller's contract via the
// X-Event-Id header (the receiving workflow should dedupe).
function scheduleRetries(url, body, headers, eventType) {
  let attempt = 0
  const tryNext = async () => {
    if (attempt >= RETRY_DELAYS_MS.length) {
      console.warn(`[webhooks] emit ${eventType} -> ${url} exhausted ${RETRY_DELAYS_MS.length} retries, giving up`)
      return
    }
    const delay = RETRY_DELAYS_MS[attempt]
    attempt += 1
    setTimeout(async () => {
      try {
        const r = await postWebhookOnce(url, body, headers)
        if (r.ok) {
          console.log(`[webhooks] emit ${eventType} retry ${attempt} succeeded (${r.status})`)
          return
        }
        console.warn(`[webhooks] emit ${eventType} retry ${attempt} got ${r.status}, scheduling next`)
        tryNext()
      } catch (err) {
        console.warn(`[webhooks] emit ${eventType} retry ${attempt} threw: ${err.message}`)
        tryNext()
      }
    }, delay).unref()
  }
  tryNext()
}

export async function emitExternalEvent(eventType, payload, opts = {}) {
  let url = null
  try {
    url = await resolveCompanyHookUrl(eventType, opts, payload)
  } catch (err) {
    console.warn(`[webhooks] hook lookup failed for ${eventType}:`, err.message)
  }
  if (!url) {
    const envName = EVENT_ENV_FALLBACKS[eventType]
    url = envName ? process.env[envName] : null
  }
  if (!url) return { skipped: true, reason: 'no target url configured' }

  const eventId = crypto.randomUUID()
  const body = JSON.stringify({ id: eventId, event: eventType, payload, emitted_at: new Date().toISOString() })
  const secret = process.env.N8N_HOOK_SECRET || ''
  const headers = {
    'Content-Type': 'application/json',
    'X-Event-Type': eventType,
    'X-Event-Id': eventId,
  }
  if (secret) {
    headers['X-Signature'] = 'sha256=' + crypto.createHmac('sha256', secret).update(body).digest('hex')
  }
  try {
    const r = await postWebhookOnce(url, body, headers)
    if (!r.ok) {
      console.warn(`[webhooks] emit ${eventType} -> ${r.status}, will retry`)
      scheduleRetries(url, body, headers, eventType)
    }
    return { ok: r.ok, status: r.status, url, eventId }
  } catch (err) {
    console.warn(`[webhooks] emit ${eventType} immediate failed: ${err.message}; scheduling retries`)
    scheduleRetries(url, body, headers, eventType)
    return { ok: false, error: err.message, eventId }
  }
}

export async function initWebhooksTable() {
  await query(`
    CREATE TABLE IF NOT EXISTS webhooks_inbox (
      id BIGSERIAL PRIMARY KEY,
      source VARCHAR(64) NOT NULL,
      event_type VARCHAR(128),
      payload JSONB NOT NULL,
      event_id VARCHAR(128),
      signature VARCHAR(256),
      verified BOOLEAN DEFAULT FALSE,
      processed BOOLEAN DEFAULT FALSE,
      processed_at TIMESTAMPTZ,
      error TEXT,
      received_at TIMESTAMPTZ DEFAULT NOW()
    )
  `)
  await query('ALTER TABLE webhooks_inbox ADD COLUMN IF NOT EXISTS event_id VARCHAR(128)')
  await query('CREATE INDEX IF NOT EXISTS idx_webhooks_source ON webhooks_inbox(source, received_at DESC)')
  await query('CREATE INDEX IF NOT EXISTS idx_webhooks_unprocessed ON webhooks_inbox(processed, received_at) WHERE processed = FALSE')
  await query('CREATE UNIQUE INDEX IF NOT EXISTS idx_webhooks_source_event_id ON webhooks_inbox(source, event_id) WHERE event_id IS NOT NULL')
  console.log('[webhooks] webhooks_inbox table ready')
}

function timingSafeEqualHex(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false
  const ab = Buffer.from(a, 'hex')
  const bb = Buffer.from(b, 'hex')
  if (ab.length === 0 || ab.length !== bb.length) return false
  return crypto.timingSafeEqual(ab, bb)
}

function verifySignature(rawBody, headerSig, secret) {
  if (!secret || !headerSig) return false
  const cleaned = String(headerSig).replace(/^sha256=/, '').trim()
  const expected = crypto.createHmac('sha256', secret).update(rawBody).digest('hex')
  return timingSafeEqualHex(cleaned, expected)
}

const rateWindow = new Map()
function rateLimit(source, limit = 120) {
  const now = Date.now()
  const windowStart = now - 60_000
  const arr = (rateWindow.get(source) || []).filter(t => t > windowStart)
  if (arr.length >= limit) {
    rateWindow.set(source, arr)
    return false
  }
  arr.push(now)
  rateWindow.set(source, arr)
  return true
}

const sseClients = new Set()
function broadcast(event) {
  const payload = `data: ${JSON.stringify(event)}\n\n`
  for (const res of sseClients) {
    try { res.write(payload) } catch { /* client gone */ }
  }
}

function parseWebhookPayload(rawBody) {
  if (!rawBody?.length) return {}
  return JSON.parse(rawBody.toString('utf8'))
}

function eventIdFrom(parsed, explicitEventId) {
  return explicitEventId || parsed?.id || parsed?.event_id || null
}

export async function handleInboundWebhook({ source, rawBody, signature, secret, eventTypeHeader, eventIdHeader }, deps = {}) {
  const runQuery = deps.query || query
  const safeSource = String(source || '').slice(0, 64)
  if (!/^[a-z0-9_-]+$/i.test(safeSource)) {
    return { status: 400, body: { error: 'invalid source' } }
  }

  const bodyBuffer = Buffer.isBuffer(rawBody) ? rawBody : Buffer.from(rawBody || '')
  const verified = verifySignature(bodyBuffer, signature, secret)
  let parsed = {}
  try {
    parsed = parseWebhookPayload(bodyBuffer)
  } catch {
    if (verified) return { status: 400, body: { error: 'malformed payload' } }
    parsed = { _malformed: true }
  }

  const eventType = eventTypeHeader || parsed?.event || null
  const eventId = eventIdFrom(parsed, eventIdHeader)

  if (!verified) {
    await runQuery(
      `INSERT INTO webhooks_inbox (source, event_type, event_id, payload, signature, verified)
       VALUES ($1,$2,$3,$4,$5,$6)
       ON CONFLICT (source, event_id) WHERE event_id IS NOT NULL DO NOTHING
       RETURNING id, received_at`,
      [safeSource, eventType, eventId, parsed, signature || null, false]
    )
    return { status: 401, body: { error: 'invalid signature' } }
  }

  const { rows } = await runQuery(
    `INSERT INTO webhooks_inbox (source, event_type, event_id, payload, signature, verified)
     VALUES ($1,$2,$3,$4,$5,$6)
     ON CONFLICT (source, event_id) WHERE event_id IS NOT NULL DO UPDATE SET event_id = EXCLUDED.event_id
     RETURNING id, received_at, (xmax <> 0) AS duplicate`,
    [safeSource, eventType, eventId, parsed, signature, true]
  )
  const stored = rows[0]
  return {
    status: 200,
    body: { ok: true, id: stored.id, duplicate: Boolean(stored.duplicate) },
    broadcastEvent: Boolean(stored.duplicate) ? null : { id: stored.id, source: safeSource, event_type: eventType, event_id: eventId, received_at: stored.received_at },
  }
}

export function registerWebhookRoutes(app, { authenticate } = {}) {
  const secret = process.env.WEBHOOK_SECRET || ''
  if (!secret) {
    console.warn('[webhooks] WEBHOOK_SECRET not set; inbound webhooks will be rejected')
  }

  // Raw body parser only for this route (avoids conflict with global express.json).
  const rawParser = express.raw({ type: '*/*', limit: '512kb' })

  app.post('/webhooks/:source', rawParser, async (req, res) => {
    try {
      const source = String(req.params.source || '').slice(0, 64)
      if (!/^[a-z0-9_-]+$/i.test(source)) {
        return res.status(400).json({ error: 'invalid source' })
      }
      if (!rateLimit(source)) {
        return res.status(429).json({ error: 'rate limit exceeded' })
      }

      const rawBody = Buffer.isBuffer(req.body) ? req.body : Buffer.from('')
      const sigHeader = req.get('X-Signature') || req.get('X-Hub-Signature-256') || ''
      const result = await handleInboundWebhook({
        source,
        rawBody,
        signature: sigHeader,
        secret,
        eventTypeHeader: req.get('X-Event-Type') || null,
        eventIdHeader: req.get('X-Event-Id') || null,
      })
      if (result.broadcastEvent) broadcast(result.broadcastEvent)
      return res.status(result.status).json(result.body)
    } catch (err) {
      console.error('[webhooks] handler error:', err)
      res.status(500).json({ error: 'internal error' })
    }
  })

  const streamHandler = (req, res) => {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    })
    res.write(': connected\n\n')
    sseClients.add(res)
    const ping = setInterval(() => { try { res.write(': ping\n\n') } catch {} }, 25_000)
    req.on('close', () => {
      clearInterval(ping)
      sseClients.delete(res)
    })
  }

  if (authenticate) {
    app.get('/webhooks/stream', authenticate, streamHandler)
  } else {
    app.get('/webhooks/stream', streamHandler)
  }
}
