import test from 'node:test'
import assert from 'node:assert/strict'
import {
  DEFAULT_ALLOWED_ORIGINS,
  buildCorsOptions,
  parseAllowedOrigins,
  requestIdMiddleware,
} from '../src/security.js'

test('parseAllowedOrigins uses explicit comma-separated allowlist', () => {
  assert.deepEqual(
    parseAllowedOrigins('https://app.example.com, http://localhost:3000 ,'),
    ['https://app.example.com', 'http://localhost:3000']
  )
})

test('parseAllowedOrigins falls back to explicit NewFire/dev defaults', () => {
  assert.deepEqual(parseAllowedOrigins(''), DEFAULT_ALLOWED_ORIGINS)
})

test('CORS allows configured browser origins and rejects others', async () => {
  const options = buildCorsOptions(['https://newfire.app'])

  await new Promise((resolve, reject) => {
    options.origin('https://newfire.app', (err, allowed) => {
      try {
        assert.equal(err, null)
        assert.equal(allowed, true)
        resolve()
      } catch (e) {
        reject(e)
      }
    })
  })

  await new Promise((resolve, reject) => {
    options.origin('https://evil.example', (err, allowed) => {
      try {
        assert.match(err.message, /not allowed/)
        assert.equal(allowed, false)
        resolve()
      } catch (e) {
        reject(e)
      }
    })
  })
})

test('requestIdMiddleware preserves safe incoming request IDs', () => {
  const req = {
    headers: { 'x-request-id': 'req-123' },
    get(name) { return this.headers[name.toLowerCase()] },
  }
  const headers = {}
  const res = { setHeader(name, value) { headers[name] = value } }
  requestIdMiddleware(req, res, () => {})
  assert.equal(req.requestId, 'req-123')
  assert.equal(headers['X-Request-ID'], 'req-123')
})

test('requestIdMiddleware generates a request ID when missing', () => {
  const req = { headers: {}, get() { return undefined } }
  const headers = {}
  const res = { setHeader(name, value) { headers[name] = value } }
  requestIdMiddleware(req, res, () => {})
  assert.match(req.requestId, /^[0-9a-f-]{36}$/)
  assert.equal(headers['X-Request-ID'], req.requestId)
})
