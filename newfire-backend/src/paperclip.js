// Paperclip integration. Called from createCompanyForUser after the local
// company row exists. Always fail-soft: log + record paperclip_error in the
// companies row, but never throw out of provisionPaperclipForCompany so a
// downstream Paperclip outage cannot block signup or onboarding.

import { query } from './db.js'

const PAPERCLIP_API_URL = process.env.PAPERCLIP_API_URL || ''
const PAPERCLIP_BOARD_TOKEN = process.env.PAPERCLIP_BOARD_TOKEN || ''
const PAPERCLIP_TIMEOUT_MS = Number(process.env.PAPERCLIP_TIMEOUT_MS || 8_000)

const TIER_BUDGET_CENTS = {
  free: 0,
  starter: 2900,
  pro: 9900,
  enterprise: 0,
}

const PLATFORM_AGENT_TEMPLATES = [
  {
    name: 'OpenClaw CEO',
    role: 'general',
    title: 'Chief Executive Agent',
    adapterType: 'openclaw_gateway',
    budgetMonthlyCents: 2000,
    adapterConfig: {
      url: 'ws://host.docker.internal:18789/gateway',
      authToken: process.env.OPENCLAW_TOKEN || '',
      // Route the request to OpenClaw's existing "main" worker. Without an
      // agentId the gateway has nothing to dispatch to and the call times
      // out as openclaw_gateway_wait_error. We keep one shared worker for
      // platform-side tasks across all tenants until per-tenant OpenClaw
      // workers are warranted.
      agentId: 'main',
      sessionKeyStrategy: 'run',
      timeoutSec: 120,
      waitTimeoutMs: 120000,
    },
  },
  {
    name: 'OpenCode Developer',
    role: 'engineer',
    title: 'Coding Agent',
    adapterType: 'opencode_local',
    // 2000 cents = $20/mo. At ~$0.50/M output for qwen3.6-plus that's a
    // hard ceiling of roughly 40M output tokens before the agent is paused.
    budgetMonthlyCents: 2000,
    // Inject OPENROUTER_API_KEY into the spawned opencode env directly. The
    // adapter validation also reads the spawn env to discover available
    // models, so this serves both auth and discovery.
    adapterConfig: {
      // Free tier on OpenRouter while the account has no credits. Picked
      // gpt-oss-120b:free because (a) opencode_local validation accepts it
      // (qwen3-coder:free is filtered out of opencode's catalog), (b) it is
      // tool-use tuned, (c) 131k context. Switch to
      // openrouter/qwen/qwen3.6-plus (paid, 1M context, 65k out) once the
      // OpenRouter account is funded.
      model: 'openrouter/openai/gpt-oss-120b:free',
      env: { OPENROUTER_API_KEY: process.env.OPENROUTER_KEY || '' },
    },
  },
  {
    name: 'OpenHands QA',
    role: 'qa',
    title: 'Quality Assurance Agent',
    adapterType: 'http',
    budgetMonthlyCents: 1000,
    // Routes through openhands-shim (newfire_shared docker network) which
    // translates Paperclip's single-shot http POST into OpenHands 0.44.0's
    // multi-step conversation protocol (create + start + poll-events). The
    // shim source is at scripts/openhands-shim/. Field name is `url` (the
    // Paperclip http adapter ignores `endpoint`).
    adapterConfig: { url: 'http://openhands-shim:8080/task', method: 'POST', timeoutMs: 75000, timeoutSec: 120 },
  },
]

function isConfigured() {
  return Boolean(PAPERCLIP_API_URL && PAPERCLIP_BOARD_TOKEN)
}

async function paperclipFetch(path, init = {}) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), PAPERCLIP_TIMEOUT_MS)
  try {
    const res = await fetch(`${PAPERCLIP_API_URL}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${PAPERCLIP_BOARD_TOKEN}`,
        ...(init.headers || {}),
      },
      signal: ctrl.signal,
    })
    const text = await res.text()
    let body
    try { body = text ? JSON.parse(text) : {} } catch { body = { raw: text } }
    if (!res.ok) {
      const message = body?.error || body?.message || `${res.status}`
      const err = new Error(`paperclip ${path} -> ${res.status} ${message}`)
      err.status = res.status
      err.body = body
      throw err
    }
    return body
  } finally {
    clearTimeout(timer)
  }
}

export async function provisionPaperclipForCompany(localCompanyId, { name, description, tier }) {
  if (!isConfigured()) {
    await markStatus(localCompanyId, 'not_configured', 'PAPERCLIP_API_URL or PAPERCLIP_BOARD_TOKEN not set')
    return { ok: false, reason: 'not_configured' }
  }

  const budgetCents = TIER_BUDGET_CENTS[tier] ?? 0

  let paperclipCompanyId = null
  try {
    const company = await paperclipFetch('/companies', {
      method: 'POST',
      body: JSON.stringify({
        name,
        description: description || `NewFire tenant for ${name}`,
        budgetMonthlyCents: budgetCents,
      }),
    })
    paperclipCompanyId = company.id
  } catch (err) {
    console.error(`[paperclip] company create failed for local id=${localCompanyId}: ${err.message}`)
    await markStatus(localCompanyId, 'company_create_failed', err.message)
    return { ok: false, reason: 'company_create_failed', error: err.message }
  }

  // Seed the org chart with the three platform agents. Each failure is logged
  // but does not abort the others; partial provisioning is recorded.
  const agentResults = []
  for (const template of PLATFORM_AGENT_TEMPLATES) {
    try {
      const agent = await paperclipFetch(`/companies/${paperclipCompanyId}/agents`, {
        method: 'POST',
        body: JSON.stringify(template),
      })
      agentResults.push({ name: template.name, id: agent.id, ok: true })
    } catch (err) {
      console.warn(`[paperclip] agent create failed (${template.name}) for local id=${localCompanyId}: ${err.message}`)
      agentResults.push({ name: template.name, ok: false, error: err.message })
    }
  }

  const allAgentsOk = agentResults.every((r) => r.ok)
  const status = allAgentsOk ? 'created' : 'partial'
  const errorSummary = allAgentsOk ? null : agentResults.filter((r) => !r.ok).map((r) => `${r.name}: ${r.error}`).join('; ')

  await query(
    `UPDATE companies
       SET paperclip_company_id = $1,
           paperclip_status = $2,
           paperclip_error = $3,
           paperclip_provisioned_at = NOW()
     WHERE id = $4`,
    [paperclipCompanyId, status, errorSummary, localCompanyId]
  )

  console.log(`[paperclip] provisioned company ${paperclipCompanyId} for local id=${localCompanyId} status=${status}`)
  return { ok: status === 'created', paperclipCompanyId, agents: agentResults, status }
}

// Delegate a coding task to the tenant's OpenCode Developer agent.
//
// The Paperclip API in this release does not expose a synchronous "run an
// agent with arbitrary input" endpoint. The canonical pattern is:
//   1. Find the agent by adapterType in the tenant's Paperclip company
//   2. Create an issue with the task as title/description, assign to agent
//   3. Wake the agent so it processes the assignment immediately
//
// Execution is async. Callers receive the issue id and Paperclip URL and can
// poll /api/issues/:id for status (todo -> in_progress -> done|blocked).
export async function delegateCodingTask(localCompanyId, { title, task }) {
  if (!isConfigured()) {
    return { ok: false, code: 'not_configured', error: 'PAPERCLIP_API_URL or PAPERCLIP_BOARD_TOKEN not set' }
  }
  if (!task || typeof task !== 'string') {
    return { ok: false, code: 'bad_request', error: 'task string required' }
  }

  const r = await query(
    'SELECT paperclip_company_id, paperclip_status FROM companies WHERE id = $1',
    [localCompanyId]
  )
  const row = r.rows[0]
  if (!row) return { ok: false, code: 'company_not_found' }
  if (!row.paperclip_company_id || row.paperclip_status !== 'created') {
    return { ok: false, code: 'paperclip_not_provisioned', status: row.paperclip_status }
  }
  const paperclipCompanyId = row.paperclip_company_id

  let agents
  try {
    agents = await paperclipFetch(`/companies/${paperclipCompanyId}/agents`)
  } catch (err) {
    return { ok: false, code: 'agents_list_failed', error: err.message }
  }
  const dev = (agents || []).find((a) => a.adapterType === 'opencode_local')
  if (!dev) return { ok: false, code: 'opencode_developer_not_found' }

  const issueTitle = title || task.split('\n')[0].slice(0, 120)
  let issue
  try {
    issue = await paperclipFetch(`/companies/${paperclipCompanyId}/issues`, {
      method: 'POST',
      body: JSON.stringify({
        title: issueTitle,
        description: task,
        status: 'todo',
        priority: 'medium',
        assigneeAgentId: dev.id,
      }),
    })
  } catch (err) {
    return { ok: false, code: 'issue_create_failed', error: err.message }
  }

  // Wake the agent so it picks the issue up immediately rather than waiting
  // for the next heartbeat tick.
  try {
    await paperclipFetch(`/agents/${dev.id}/wakeup`, {
      method: 'POST',
      body: JSON.stringify({
        source: 'on_demand',
        triggerDetail: 'manual',
        reason: `delegated coding task ${issue.identifier}`,
      }),
    })
  } catch (err) {
    console.warn(`[paperclip] wakeup failed (issue ${issue.identifier} still queued):`, err.message)
  }

  return {
    ok: true,
    issueId: issue.id,
    issueIdentifier: issue.identifier,
    agentId: dev.id,
    paperclipCompanyId,
    status: issue.status,
    dashboardUrl: `${process.env.PAPERCLIP_PUBLIC_URL || 'https://dash.newfire.app'}/companies/${paperclipCompanyId}/issues/${issue.id}`,
  }
}

// Fetch the latest state of a delegated task from Paperclip. Returns the
// issue's status and any work products (the agent's output). All errors
// surface as { ok: false, error }.
export async function getPaperclipIssue(paperclipIssueId) {
  if (!isConfigured()) return { ok: false, error: 'paperclip not configured' }
  try {
    const issue = await paperclipFetch(`/issues/${paperclipIssueId}`)
    let workProducts = []
    try {
      workProducts = await paperclipFetch(`/issues/${paperclipIssueId}/work-products`)
    } catch (err) {
      // work-products list may 404 until the agent has produced output, ignore.
    }
    return { ok: true, issue, workProducts: Array.isArray(workProducts) ? workProducts : [] }
  } catch (err) {
    return { ok: false, error: err.message }
  }
}

async function markStatus(localCompanyId, status, errorText) {
  try {
    await query(
      `UPDATE companies SET paperclip_status = $1, paperclip_error = $2 WHERE id = $3`,
      [status, errorText || null, localCompanyId]
    )
  } catch (dbErr) {
    console.error('[paperclip] mark-status failed:', dbErr.message)
  }
}
