import test from 'node:test'
import assert from 'node:assert/strict'
import crypto from 'node:crypto'

process.env.DB_PASSWORD ||= 'test-password'

const { handleInboundWebhook } = await import('../src/webhooks.js')

function sign(rawBody, secret) {
  return 'sha256=' + crypto.createHmac('sha256', secret).update(rawBody).digest('hex')
}

function createInboxQuery() {
  const inbox = []
  return {
    inbox,
    async query(sql, params = []) {
      const normalized = sql.replace(/\s+/g, ' ').trim()
      if (normalized.startsWith('INSERT INTO webhooks_inbox')) {
        const [source, eventType, eventId, payload, signature, verified] = params
        const existing = inbox.find((row) => row.source === source && row.event_id === eventId)
        if (existing) return { rows: [{ id: existing.id, duplicate: true, received_at: existing.received_at }] }
        const row = {
          id: inbox.length + 1,
          source,
          event_type: eventType,
          event_id: eventId,
          payload,
          signature,
          verified,
          received_at: new Date().toISOString(),
        }
        inbox.push(row)
        return { rows: [{ id: row.id, duplicate: false, received_at: row.received_at }] }
      }
      throw new Error(`Unhandled query: ${normalized}`)
    },
  }
}

test('invalid signature is rejected without leaking the configured secret', async () => {
  const secret = 'super-sensitive-webhook-secret'
  const rawBody = Buffer.from(JSON.stringify({ id: 'evt-invalid', event: 'tenant.updated' }))
  const store = createInboxQuery()

  const result = await handleInboundWebhook({
    source: 'n8n',
    rawBody,
    signature: 'sha256=not-the-right-signature',
    secret,
  }, { query: store.query })

  assert.equal(result.status, 401)
  assert.deepEqual(result.body, { error: 'invalid signature' })
  assert.equal(JSON.stringify(result).includes(secret), false)
  assert.equal(store.inbox.length, 1)
  assert.equal(store.inbox[0].verified, false)
})

test('malformed verified payload is rejected and not stored', async () => {
  const secret = 'super-sensitive-webhook-secret'
  const rawBody = Buffer.from('{not valid json')
  const store = createInboxQuery()

  const result = await handleInboundWebhook({
    source: 'n8n',
    rawBody,
    signature: sign(rawBody, secret),
    secret,
  }, { query: store.query })

  assert.equal(result.status, 400)
  assert.deepEqual(result.body, { error: 'malformed payload' })
  assert.equal(store.inbox.length, 0)
})

test('duplicate verified event id is idempotent and does not store twice', async () => {
  const secret = 'super-sensitive-webhook-secret'
  const rawBody = Buffer.from(JSON.stringify({ id: 'evt-duplicate', event: 'agent.created', payload: { agent_id: 'sales' } }))
  const store = createInboxQuery()

  const first = await handleInboundWebhook({
    source: 'n8n',
    rawBody,
    signature: sign(rawBody, secret),
    secret,
  }, { query: store.query })
  const second = await handleInboundWebhook({
    source: 'n8n',
    rawBody,
    signature: sign(rawBody, secret),
    secret,
  }, { query: store.query })

  assert.equal(first.status, 200)
  assert.equal(first.body.duplicate, false)
  assert.equal(second.status, 200)
  assert.equal(second.body.duplicate, true)
  assert.equal(second.body.id, first.body.id)
  assert.equal(store.inbox.length, 1)
})
