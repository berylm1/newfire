import express from 'express'
import cors from 'cors'
import { initDatabase, query } from './db.js'
import { signup, login, authenticate, getUser, setOnboarded } from './auth.js'
import { tenantContext, invalidateTenant } from './tenant.js'
import {
  createCompanyForUser,
  getUserAgents,
  getUserCompany,
  chatWithAgent,
  getConversation,
  buildSystemPrompt,
  proxyChat,
} from './orchestrator.js'
import { delegateCodingTask, getPaperclipIssue } from './paperclip.js'
import { ceoChat, ceoHistory, ceoReset } from './ceo.js'
import { runOpenHandsTask, listSessions as listDevSessions, getSession as getDevSession, requireDeveloper } from './dev.js'
import { TIERS, getTier, listTiers } from './tiers.js'
import { initWebhooksTable, registerWebhookRoutes, emitExternalEvent } from './webhooks.js'
import { httpMetricsMiddleware, metricsHandler } from './metrics.js'

const app = express()
const PORT = process.env.PORT || 3200

app.use(cors())
// Stripe webhook MUST receive the raw body for signature verification.
// This mount runs BEFORE express.json() so req.body arrives as a Buffer on this path only.
app.use('/webhooks/stripe', express.raw({ type: 'application/json' }))
app.use(express.json({ limit: '1mb' }))
app.use(httpMetricsMiddleware)

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'newfire-backend', version: '1.0.0' })
})

// Prometheus scrape target. Not auth-gated by design (Prometheus needs to
// scrape) but only reachable from the docker network in production.
app.get('/metrics', metricsHandler)

// Auth routes
app.post('/auth/signup', async (req, res) => {
  try {
    const { email, password, name } = req.body
    if (!email || !password || !name) {
      return res.status(400).json({ error: 'Email, password, and name are required' })
    }
    const result = await signup(email, password, name)
    emitExternalEvent('user.signup', {
      user_id: result.user?.id,
      email: result.user?.email,
      name: result.user?.name,
    }).catch(() => {})
    res.json(result)
  } catch (err) {
    res.status(400).json({ error: err.message })
  }
})

app.post('/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' })
    }
    const result = await login(email, password)
    res.json(result)
  } catch (err) {
    res.status(401).json({ error: err.message })
  }
})

app.get('/auth/me', authenticate, async (req, res) => {
  const user = await getUser(req.userId)
  if (!user) return res.status(404).json({ error: 'User not found' })
  res.json({ user })
})

// Company and agent routes
app.get('/company', authenticate, async (req, res) => {
  const company = await getUserCompany(req.userId)
  if (!company) return res.json({ company: null })
  const agents = await getUserAgents(req.userId)
  res.json({ company, agents })
})

app.get('/company/usage', authenticate, async (req, res) => {
  const companyRes = await query(
    `SELECT id, name, tier, monthly_budget_usd, allow_cloud_models, qdrant_collection
     FROM companies WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1`,
    [req.userId]
  )
  const company = companyRes.rows[0]
  if (!company) return res.json({ company: null, usage: null })

  const m = await query(
    `SELECT
       COUNT(*)::int AS calls,
       COALESCE(SUM(total_tokens),0)::bigint AS tokens,
       COALESCE(SUM(input_tokens),0)::bigint AS input_tokens,
       COALESCE(SUM(output_tokens),0)::bigint AS output_tokens,
       ROUND(COALESCE(AVG(duration_ms),0)) AS avg_latency_ms,
       COALESCE(MAX(context_used_pct),0)::int AS max_ctx_pct,
       SUM(CASE WHEN context_used_pct >= 80 THEN 1 ELSE 0 END)::int AS high_ctx_calls,
       array_agg(DISTINCT model) AS models,
       MAX(created_at) AS last_activity
     FROM chat_metrics
     WHERE user_id = $1 AND created_at >= date_trunc('month', NOW())`,
    [req.userId]
  )

  // Model pricing table (USD per 1k tokens, rough averages)
  const pricing = {
    'glm4:9b': 0, 'gemma4:26b': 0, 'deepseek-r1:32b': 0, 'deepseek-r1:32b-8k': 0,
    'deepseek-r1:70b': 0, 'openclaw': 0,
    'minimax/minimax-m2.7': 0.40, 'z-ai/glm-5.1': 0.50,
    'moonshotai/kimi-k2.6': 0.60, 'moonshotai/kimi-k2.5': 0.60, 'moonshotai/kimi-k2': 0.50,
    'claude-sonnet-4.5': 3.00, 'claude-haiku-4.5': 0.80,
    'nvidia/nemotron-3-nano-30b-a3b:free': 0,
  }

  const models = (m.rows[0].models || []).filter(Boolean)
  const tokens = Number(m.rows[0].tokens || 0)
  const avgPrice = models.length ? models.reduce((s, mm) => s + (pricing[mm] ?? 1.0), 0) / models.length : 0
  const costUsd = Math.round((tokens / 1000) * avgPrice * 100) / 100

  const budget = Number(company.monthly_budget_usd || 0)
  const budgetPct = budget > 0 ? Math.min(100, Math.round((costUsd / budget) * 100)) : 0

  res.json({
    company: {
      id: company.id, name: company.name,
      tier: company.tier || 'free',
      budget_usd: budget,
      allow_cloud_models: company.allow_cloud_models !== false,
      has_rag: !!company.qdrant_collection,
    },
    usage: {
      month_to_date: {
        calls: Number(m.rows[0].calls || 0),
        tokens: tokens,
        input_tokens: Number(m.rows[0].input_tokens || 0),
        output_tokens: Number(m.rows[0].output_tokens || 0),
        avg_latency_ms: Number(m.rows[0].avg_latency_ms || 0),
        max_ctx_pct: Number(m.rows[0].max_ctx_pct || 0),
        high_ctx_calls: Number(m.rows[0].high_ctx_calls || 0),
        models,
        last_activity: m.rows[0].last_activity,
        estimated_cost_usd: costUsd,
      },
      budget_used_pct: budgetPct,
      budget_remaining_usd: Math.max(0, Math.round((budget - costUsd) * 100) / 100),
      over_budget: budget > 0 && costUsd >= budget,
    },
  })
})

app.post('/company/create', authenticate, async (req, res) => {
  try {
    const { name, description, agents } = req.body
    if (!name || !agents || agents.length === 0) {
      return res.status(400).json({ error: 'Company name and at least one agent are required' })
    }
    const result = await createCompanyForUser(req.userId, name, description || '', agents)
    invalidateTenant(req.userId)
    res.json(result)
  } catch (err) {
    if (err.code === 'COMPANY_EXISTS') return res.status(409).json({ error: err.message, code: 'COMPANY_EXISTS' })
    if (err.code === 'TIER_AGENT_CAP') return res.status(400).json({ error: err.message, code: 'TIER_AGENT_CAP' })
    res.status(500).json({ error: err.message })
  }
})

app.get('/agents', authenticate, async (req, res) => {
  const agents = await getUserAgents(req.userId)
  res.json({ agents })
})

app.put('/agents/:agentId', authenticate, tenantContext, async (req, res) => {
  try {
    const { agentId } = req.params
    const { name, description, role } = req.body
    const result = await query(
      `UPDATE agents SET
        name = COALESCE($3, name),
        description = COALESCE($4, description),
        role = COALESCE($5, role),
        system_prompt = CASE WHEN $3 IS NOT NULL OR $5 IS NOT NULL
          THEN 'You are ' || COALESCE($3, name) || ', an AI agent. ' || COALESCE($5, role) || ' ' || COALESCE($4, description) || ' Be helpful, professional, and proactive. Format your responses with clear structure.'
          ELSE system_prompt END
      FROM companies c
      WHERE agents.company_id = c.id AND c.user_id = $1 AND agents.agent_id = $2
      RETURNING agents.*`,
      [req.userId, agentId, name || null, description || null, role || null]
    )
    if (result.rows.length === 0) return res.status(404).json({ error: 'Agent not found' })
    res.json({ agent: result.rows[0] })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

app.delete('/agents/:agentId', authenticate, tenantContext, async (req, res) => {
  try {
    const result = await query(
      `DELETE FROM agents
       USING companies c
       WHERE agents.company_id = c.id AND c.user_id = $1 AND agents.agent_id = $2
       RETURNING agents.id`,
      [req.userId, req.params.agentId]
    )
    if (result.rows.length === 0) return res.status(404).json({ error: 'Agent not found' })
    res.json({ deleted: true })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// Admin routes
app.get('/admin/stats', authenticate, async (req, res) => {
  const user = await getUser(req.userId)
  if (user.role !== 'admin') return res.status(403).json({ error: 'Admin access required' })

  const users = await query('SELECT id, email, name, role, onboarded, created_at FROM users ORDER BY created_at DESC')
  const companies = await query(`
    SELECT c.*, u.email as owner_email, u.name as owner_name,
      (SELECT COUNT(*) FROM agents WHERE company_id = c.id) as agent_count
    FROM companies c JOIN users u ON c.user_id = u.id ORDER BY c.created_at DESC
  `)
  const agents = await query(`
    SELECT a.*, c.name as company_name FROM agents a
    JOIN companies c ON a.company_id = c.id ORDER BY a.created_at DESC
  `)
  const conversations = await query('SELECT COUNT(*) as total, COUNT(DISTINCT user_id) as active_users FROM conversations')
  const totalMessages = await query(`SELECT COALESCE(SUM(jsonb_array_length(messages)), 0) as total FROM conversations`)

  res.json({
    users: users.rows,
    companies: companies.rows,
    agents: agents.rows,
    stats: {
      totalUsers: users.rows.length,
      onboardedUsers: users.rows.filter(u => u.onboarded).length,
      totalCompanies: companies.rows.length,
      totalAgents: agents.rows.length,
      totalConversations: parseInt(conversations.rows[0].total),
      activeUsers: parseInt(conversations.rows[0].active_users),
      totalMessages: parseInt(totalMessages.rows[0].total),
    }
  })
})

app.get('/admin/crm', authenticate, async (req, res) => {
  const user = await getUser(req.userId)
  if (user.role !== 'admin') return res.status(403).json({ error: 'Admin access required' })

  const clients = await query(`
    SELECT u.id, u.email, u.name, u.role, u.onboarded, u.created_at,
      c.name as company_name, c.id as company_id,
      (SELECT COUNT(*) FROM agents WHERE company_id = c.id) as agent_count,
      (SELECT COUNT(*) FROM conversations WHERE user_id = u.id) as conversation_count,
      (SELECT COALESCE(SUM(jsonb_array_length(messages)), 0) FROM conversations WHERE user_id = u.id) as message_count,
      (SELECT MAX(updated_at) FROM conversations WHERE user_id = u.id) as last_active,
      COALESCE(
        (SELECT value FROM client_notes WHERE user_id = u.id AND key = 'stage'),
        CASE
          WHEN (SELECT MAX(updated_at) FROM conversations WHERE user_id = u.id) > NOW() - INTERVAL '3 days' THEN 'active'
          WHEN u.onboarded AND (SELECT MAX(updated_at) FROM conversations WHERE user_id = u.id) < NOW() - INTERVAL '7 days' THEN 'at-risk'
          WHEN u.onboarded THEN 'active'
          ELSE 'signed-up'
        END
      ) as pipeline_stage
    FROM users u
    LEFT JOIN companies c ON c.user_id = u.id
    WHERE u.role != 'admin'
    ORDER BY u.created_at DESC
  `)

  res.json({ clients: clients.rows })
})

app.post('/admin/crm/note', authenticate, async (req, res) => {
  const user = await getUser(req.userId)
  if (user.role !== 'admin') return res.status(403).json({ error: 'Admin access required' })

  const { userId, key, value } = req.body
  await query(
    `INSERT INTO client_notes (user_id, key, value, updated_by, updated_at)
     VALUES ($1, $2, $3, $4, NOW())
     ON CONFLICT (user_id, key) DO UPDATE SET value = $3, updated_by = $4, updated_at = NOW()`,
    [userId, key, value, req.userId]
  )
  res.json({ success: true })
})

app.get('/admin/roi', authenticate, async (req, res) => {
  const user = await getUser(req.userId)
  if (user.role !== 'admin') return res.status(403).json({ error: 'Admin access required' })

  const rows = await query(`
    SELECT c.id AS company_id,
      c.name AS company_name,
      c.description,
      c.qdrant_collection,
      c.tier,
      c.monthly_budget_usd,
      c.allow_cloud_models,
      u.email AS owner_email,
      u.name AS owner_name,
      (SELECT COUNT(*) FROM agents WHERE company_id = c.id) AS agent_count,
      (SELECT string_agg(DISTINCT model, ', ') FROM agents WHERE company_id = c.id) AS models,
      (SELECT COUNT(*) FROM conversations WHERE user_id = c.user_id) AS conversation_count,
      (SELECT COALESCE(SUM(jsonb_array_length(messages)), 0) FROM conversations WHERE user_id = c.user_id) AS message_count,
      (SELECT COALESCE(SUM((SELECT COUNT(*) FROM jsonb_array_elements(messages) m WHERE m->>'role' = 'assistant')), 0)
        FROM conversations WHERE user_id = c.user_id) AS assistant_messages,
      (SELECT COALESCE(SUM((SELECT COALESCE(SUM(LENGTH(m->>'content')), 0) FROM jsonb_array_elements(messages) m)), 0)
        FROM conversations WHERE user_id = c.user_id) AS total_chars,
      (SELECT MAX(updated_at) FROM conversations WHERE user_id = c.user_id) AS last_active,
      c.created_at
    FROM companies c
    JOIN users u ON c.user_id = u.id
    ORDER BY last_active DESC NULLS LAST
  `)

  const companies = rows.rows.map((r) => {
    const chars = Number(r.total_chars || 0)
    const tokens = Math.round(chars / 4)
    const assistantMsgs = Number(r.assistant_messages || 0)
    const timeSavedMin = assistantMsgs * 3
    const models = r.models || ''
    const hasCloud = /openrouter|claude|gpt|minimax|gemini/i.test(models)
    const estCostUsd = hasCloud ? Math.round(tokens * 0.00015 * 100) / 100 : 0
    const lastActive = r.last_active ? new Date(r.last_active) : null
    const daysSince = lastActive ? Math.floor((Date.now() - lastActive.getTime()) / (1000 * 60 * 60 * 24)) : null
    let stage = 'idle'
    if (!lastActive) stage = 'never-used'
    else if (daysSince <= 3) stage = 'active'
    else if (daysSince <= 14) stage = 'warm'
    else stage = 'at-risk'
    return {
      company_id: r.company_id,
      company_name: r.company_name,
      description: r.description,
      tier: r.tier || 'free',
      budget_usd: Number(r.monthly_budget_usd || 0),
      budget_used_pct: Number(r.monthly_budget_usd || 0) > 0 ? Math.min(100, Math.round((estCostUsd / Number(r.monthly_budget_usd || 0)) * 100)) : 0,
      allow_cloud_models: r.allow_cloud_models !== false,
      owner_email: r.owner_email,
      owner_name: r.owner_name,
      agent_count: Number(r.agent_count),
      models,
      has_collection: !!r.qdrant_collection,
      conversation_count: Number(r.conversation_count),
      message_count: Number(r.message_count),
      assistant_messages: assistantMsgs,
      estimated_tokens: tokens,
      estimated_cost_usd: estCostUsd,
      time_saved_minutes: timeSavedMin,
      last_active: r.last_active,
      days_since_last_active: daysSince,
      stage,
    }
  })

  const totals = companies.reduce(
    (acc, c) => ({
      conversations: acc.conversations + c.conversation_count,
      messages: acc.messages + c.message_count,
      tokens: acc.tokens + c.estimated_tokens,
      costUsd: Math.round((acc.costUsd + c.estimated_cost_usd) * 100) / 100,
      timeSavedMinutes: acc.timeSavedMinutes + c.time_saved_minutes,
    }),
    { conversations: 0, messages: 0, tokens: 0, costUsd: 0, timeSavedMinutes: 0 }
  )

  res.json({ companies, totals })
})

app.get('/admin/metrics', authenticate, async (req, res) => {
  const user = await getUser(req.userId)
  if (user.role !== 'admin') return res.status(403).json({ error: 'Admin access required' })

  const window = (req.query.window === '7d') ? '7 days' : '24 hours'
  const windowLabel = (req.query.window === '7d') ? '7d' : '24h'

  const byModel = await query(`
    SELECT model, provider,
      COUNT(*)::int AS calls,
      COALESCE(SUM(input_tokens),0)::bigint AS input_tokens,
      COALESCE(SUM(output_tokens),0)::bigint AS output_tokens,
      COALESCE(SUM(total_tokens),0)::bigint AS total_tokens,
      ROUND(COALESCE(AVG(duration_ms),0)) AS avg_latency_ms,
      ROUND(COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms),0)) AS p95_latency_ms,
      ROUND(COALESCE(AVG(context_used_pct),0)) AS avg_ctx_pct,
      COALESCE(MAX(context_used_pct),0)::int AS max_ctx_pct,
      SUM(CASE WHEN context_used_pct >= 80 THEN 1 ELSE 0 END)::int AS high_ctx_calls,
      ROUND(COALESCE(AVG(temperature)::numeric,0), 2) AS avg_temperature,
      SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END)::int AS failures
    FROM chat_metrics
    WHERE created_at >= NOW() - INTERVAL '${window}'
    GROUP BY model, provider
    ORDER BY total_tokens DESC
  `)

  const totals = await query(`
    SELECT
      COUNT(*)::int AS calls,
      COALESCE(SUM(total_tokens),0)::bigint AS total_tokens,
      ROUND(COALESCE(AVG(duration_ms),0)) AS avg_latency_ms,
      SUM(CASE WHEN context_used_pct >= 80 THEN 1 ELSE 0 END)::int AS high_ctx_calls,
      SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END)::int AS failures
    FROM chat_metrics
    WHERE created_at >= NOW() - INTERVAL '${window}'
  `)

  const highContext = await query(`
    SELECT cm.id, cm.agent_id, cm.user_id, u.email, cm.model,
      cm.context_used_tokens, cm.context_window, cm.context_used_pct,
      cm.duration_ms, cm.created_at
    FROM chat_metrics cm
    JOIN users u ON u.id = cm.user_id
    WHERE cm.context_used_pct >= 80
      AND cm.created_at >= NOW() - INTERVAL '${window}'
    ORDER BY cm.context_used_pct DESC, cm.created_at DESC
    LIMIT 15
  `)

  res.json({
    window: windowLabel,
    totals: totals.rows[0] || { calls: 0, total_tokens: 0, avg_latency_ms: 0, high_ctx_calls: 0, failures: 0 },
    by_model: byModel.rows.map((r) => ({
      ...r,
      input_tokens: Number(r.input_tokens || 0),
      output_tokens: Number(r.output_tokens || 0),
      total_tokens: Number(r.total_tokens || 0),
      avg_latency_ms: Number(r.avg_latency_ms || 0),
      p95_latency_ms: Number(r.p95_latency_ms || 0),
      avg_ctx_pct: Number(r.avg_ctx_pct || 0),
      avg_temperature: Number(r.avg_temperature || 0),
    })),
    high_context_recent: highContext.rows,
  })
})

app.post('/admin/regenerate-prompts', authenticate, async (req, res) => {
  const user = await getUser(req.userId)
  if (user.role !== 'admin') return res.status(403).json({ error: 'Admin access required' })

  const agents = await query(
    `SELECT a.id, a.agent_id, a.name, a.role, a.description, c.name AS company_name
     FROM agents a JOIN companies c ON a.company_id = c.id`
  )
  let updated = 0
  for (const a of agents.rows) {
    const newPrompt = buildSystemPrompt({
      name: a.name, role: a.role, description: a.description, company_name: a.company_name,
    })
    await query('UPDATE agents SET system_prompt = $1 WHERE id = $2', [newPrompt, a.id])
    updated++
  }
  res.json({ updated, agent_count: agents.rows.length })
})

const ALLOWED_USER_ROLES = new Set(['client', 'developer', 'admin'])

app.post('/admin/set-role', authenticate, async (req, res) => {
  const user = await getUser(req.userId)
  if (user.role !== 'admin') return res.status(403).json({ error: 'Admin access required' })

  const { userId, role } = req.body || {}
  if (!Number.isInteger(userId) && !(typeof userId === 'string' && /^\d+$/.test(userId))) {
    return res.status(400).json({ error: 'userId required (integer)' })
  }
  if (!ALLOWED_USER_ROLES.has(role)) {
    return res.status(400).json({ error: `role must be one of: ${[...ALLOWED_USER_ROLES].join(', ')}` })
  }
  await query('UPDATE users SET role = $1 WHERE id = $2', [role, Number(userId)])
  invalidateTenant(Number(userId))
  res.json({ success: true, userId: Number(userId), role })
})

// Admin: create user (optionally with role)
app.post('/admin/users', authenticate, async (req, res) => {
  const actor = await getUser(req.userId)
  if (actor.role !== 'admin') return res.status(403).json({ error: 'Admin access required' })

  const { email, password, name, role } = req.body || {}
  if (!email || !password || !name) {
    return res.status(400).json({ error: 'email, password, name required' })
  }
  const allowedRoles = ['user', 'client', 'Developer', 'admin']
  const chosenRole = role && allowedRoles.includes(role) ? role : 'user'
  try {
    const result = await signup(email, password, name)
    if (chosenRole !== 'user') {
      await query('UPDATE users SET role = $1 WHERE id = $2', [chosenRole, result.user.id])
      result.user.role = chosenRole
    }
    console.log(`[admin] user ${actor.id} created user ${result.user.id} (${email}) role=${chosenRole}`)
    res.json({ user: result.user })
  } catch (err) {
    res.status(400).json({ error: err.message })
  }
})

// Admin: delete user. Optionally cancels their Stripe subscription.
app.delete('/admin/users/:id', authenticate, async (req, res) => {
  const actor = await getUser(req.userId)
  if (actor.role !== 'admin') return res.status(403).json({ error: 'Admin access required' })

  const targetId = Number(req.params.id)
  if (!targetId) return res.status(400).json({ error: 'invalid user id' })
  if (targetId === actor.id) return res.status(400).json({ error: 'cannot delete your own account' })

  const target = await query('SELECT id, email, stripe_subscription_id FROM users WHERE id = $1', [targetId])
  if (!target.rows[0]) return res.status(404).json({ error: 'user not found' })

  const cancelStripe = req.body?.cancel_stripe !== false
  const stripeSubId = target.rows[0].stripe_subscription_id
  const warnings = []

  if (cancelStripe && stripeSubId && process.env.STRIPE_SECRET_KEY) {
    try {
      const stripeMod = await import('stripe')
      const Stripe = stripeMod.default || stripeMod.Stripe
      const stripe = new Stripe(process.env.STRIPE_SECRET_KEY)
      await stripe.subscriptions.cancel(stripeSubId)
      console.log(`[admin] cancelled stripe sub ${stripeSubId} for user ${targetId}`)
    } catch (err) {
      warnings.push(`stripe cancel failed: ${err.message}`)
      console.warn(`[admin] stripe cancel failed for ${stripeSubId}: ${err.message}`)
    }
  }

  // CASCADE on companies/agents/conversations etc. is defined in schema
  await query('DELETE FROM users WHERE id = $1', [targetId])
  invalidateTenant(targetId)
  console.log(`[admin] user ${actor.id} deleted user ${targetId} (${target.rows[0].email})`)
  res.json({ success: true, deleted_id: targetId, warnings })
})

// Chat routes
// /chat/proxy is registered before /chat/:agentId so the param route does not shadow it.
app.post('/chat/proxy', authenticate, tenantContext, async (req, res) => {
  try {
    const { messages, model, temperature, max_tokens } = req.body || {}
    const result = await proxyChat({
      userId: req.userId,
      companyId: req.companyId,
      isAdmin: req.isAdmin,
      messages,
      model,
      temperature,
      maxTokens: max_tokens,
    })
    res.json(result)
  } catch (err) {
    if (err.code === 'BAD_REQUEST') return res.status(400).json({ error: err.message })
    if (err.code === 'TIER_CAP') return res.status(402).json({ error: err.message, code: 'TIER_CAP' })
    if (err.code === 'UPSTREAM_FAILED') return res.status(502).json({ error: err.message })
    console.error('[chat/proxy] error:', err.message)
    res.status(500).json({ error: 'proxy failed' })
  }
})

app.post('/chat/:agentId', authenticate, tenantContext, async (req, res) => {
  try {
    const { agentId } = req.params
    const { messages } = req.body
    if (!messages || messages.length === 0) {
      return res.status(400).json({ error: 'Messages are required' })
    }
    const response = await chatWithAgent(req.userId, agentId, messages, { companyId: req.companyId })
    res.json({ response })
  } catch (err) {
    console.error('[chat] Error:', err.message)
    if (err.code === 'TIER_CAP') {
      return res.status(402).json({ error: err.message, code: 'TIER_CAP' })
    }
    res.status(500).json({ error: err.message })
  }
})

app.get('/chat/:agentId/history', authenticate, tenantContext, async (req, res) => {
  const messages = await getConversation(req.userId, req.params.agentId)
  res.json({ messages })
})

// Public tier catalog
app.get('/tiers', (req, res) => {
  res.json({ tiers: listTiers() })
})

// Stripe checkout stub: returns 503 until keys land, wired end-to-end otherwise
app.post('/billing/checkout', authenticate, async (req, res) => {
  const { tier_id } = req.body || {}
  const tier = getTier(tier_id)
  if (!tier || tier.id === 'free' || tier.id === 'enterprise') {
    return res.status(400).json({ error: 'select_paid_tier' })
  }
  if (!process.env.STRIPE_SECRET_KEY || !tier.stripe_price_id) {
    return res.status(503).json({
      error: 'stripe_not_configured',
      message: 'Stripe keys not yet provisioned. Check back shortly.',
    })
  }
  try {
    const stripeMod = await import('stripe')
    const Stripe = stripeMod.default || stripeMod.Stripe
    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY)
    const user = await getUser(req.userId)
    const company = await getUserCompany(req.userId)
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      line_items: [{ price: tier.stripe_price_id, quantity: 1 }],
      customer_email: user.email,
      client_reference_id: String(req.userId),
      metadata: {
        user_id: String(req.userId),
        company_id: company ? String(company.id) : '',
        tier_id: tier.id,
      },
      success_url: (process.env.PUBLIC_URL || 'https://newfire.app') + '/dashboard?billing=success',
      cancel_url: (process.env.PUBLIC_URL || 'https://newfire.app') + '/pricing?billing=cancelled',
    })
    res.json({ url: session.url })
  } catch (err) {
    console.error('[billing] checkout error:', err.message)
    res.status(500).json({ error: err.message })
  }
})

// Delegate a coding task to the tenant's OpenCode Developer agent in
// Paperclip. Issue-based (no synchronous /runs endpoint exists). Returns
// the issue id + dashboard URL so the caller can track progress.
app.post('/agent/delegate', authenticate, tenantContext, async (req, res) => {
  try {
    const { task, title } = req.body || {}
    if (!task || typeof task !== 'string' || task.trim().length < 4) {
      return res.status(400).json({ error: 'task string (>=4 chars) required' })
    }
    if (req.companyId == null) {
      return res.status(403).json({ error: 'no tenant for this user' })
    }
    const result = await delegateCodingTask(req.companyId, { title, task })
    if (!result.ok) {
      const status = result.code === 'paperclip_not_provisioned' ? 409
        : result.code === 'opencode_developer_not_found' ? 404
        : result.code === 'company_not_found' ? 404
        : result.code === 'bad_request' ? 400
        : result.code === 'not_configured' ? 503
        : 502
      return res.status(status).json(result)
    }
    // Persist a local row so the customer can list their delegated tasks,
    // poll status without needing direct Paperclip access, and attach
    // accept/changes feedback.
    const ins = await query(
      `INSERT INTO agent_tasks
         (user_id, company_id, paperclip_issue_id, paperclip_issue_identifier,
          paperclip_agent_id, paperclip_company_id, title, task)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
       RETURNING id, created_at`,
      [
        req.userId, req.companyId, result.issueId, result.issueIdentifier,
        result.agentId, result.paperclipCompanyId, title || task.slice(0, 120), task,
      ]
    )
    res.json({ ...result, taskId: ins.rows[0].id, created_at: ins.rows[0].created_at })
  } catch (err) {
    console.error('[agent/delegate] error:', err.message)
    res.status(500).json({ error: 'delegate failed' })
  }
})

// CEO conversation: the chat-first dashboard's only backend. Customer talks
// here, LLM acts as a "company consultant" and can invoke tools server-side.
app.post('/ceo/chat', authenticate, tenantContext, ceoChat)

// Developer platform: OpenHands-powered task execution.
app.post('/dev/openhands', authenticate, requireDeveloper, runOpenHandsTask)
app.get('/dev/openhands/sessions', authenticate, requireDeveloper, listDevSessions)
app.get('/dev/openhands/sessions/:id', authenticate, requireDeveloper, getDevSession)
app.get('/ceo/history', authenticate, tenantContext, ceoHistory)
app.post('/ceo/reset', authenticate, tenantContext, ceoReset)

app.get('/agent/tasks', authenticate, tenantContext, async (req, res) => {
  // List the caller's tenant tasks, newest first. Capped at 50 for the
  // SPA list view; pagination can come later when a tenant actually has
  // that many tasks.
  if (req.companyId == null && !req.isAdmin) return res.json({ tasks: [] })
  const params = req.isAdmin ? [] : [req.companyId]
  const where = req.isAdmin ? '' : 'WHERE company_id = $1'
  const r = await query(
    `SELECT id, user_id, company_id, paperclip_issue_id, paperclip_issue_identifier,
            paperclip_agent_id, paperclip_company_id, title, task,
            feedback_decision, feedback_comment, feedback_at,
            completion_notified_at, created_at
     FROM agent_tasks ${where}
     ORDER BY created_at DESC LIMIT 50`,
    params
  )
  res.json({ tasks: r.rows })
})

app.get('/agent/tasks/:id', authenticate, tenantContext, async (req, res) => {
  const taskId = Number(req.params.id)
  if (!taskId) return res.status(400).json({ error: 'invalid id' })
  const r = await query(
    `SELECT id, user_id, company_id, paperclip_issue_id, paperclip_issue_identifier,
            paperclip_agent_id, paperclip_company_id, title, task,
            feedback_decision, feedback_comment, feedback_at, completion_notified_at, created_at
     FROM agent_tasks WHERE id = $1`,
    [taskId]
  )
  const row = r.rows[0]
  if (!row) return res.status(404).json({ error: 'not found' })
  if (!req.isAdmin && row.company_id !== req.companyId) {
    return res.status(403).json({ error: 'forbidden' })
  }
  const live = row.paperclip_issue_id ? await getPaperclipIssue(row.paperclip_issue_id) : { ok: false, error: 'no issue id' }

  // First-observed-completion: fire agent.task.completed once. We don't run a
  // background poller for this; the SPA already polls this endpoint so the
  // event fires as soon as the user is watching. If the user closes the tab
  // before completion, the event waits for the next watcher (acceptable for
  // launch; backend-side poller is a post-launch enhancement).
  const liveStatus = live?.issue?.status
  if (live.ok && !row.completion_notified_at && (liveStatus === 'done' || liveStatus === 'completed')) {
    try {
      await query('UPDATE agent_tasks SET completion_notified_at = NOW() WHERE id = $1 AND completion_notified_at IS NULL', [row.id])
      const summary = (live.workProducts || []).map((wp) => wp.kind || wp.path || 'work_product').join(', ') || liveStatus
      emitExternalEvent('agent.task.completed', {
        task_id: row.id,
        title: row.title,
        company_id: row.company_id,
        paperclip_issue_id: row.paperclip_issue_id,
        paperclip_agent_id: row.paperclip_agent_id,
        result_summary: summary,
        completed_at: live.issue?.completedAt,
      }, { companyId: row.company_id }).catch((err) => {
        console.warn('[agent-task] completion emit failed:', err.message)
      })
      console.log(`[agent-task] completion fired: id=${row.id} status=${liveStatus}`)
    } catch (err) {
      console.warn('[agent-task] completion notify update failed:', err.message)
    }
  }

  res.json({
    task: row,
    live: live.ok
      ? { status: live.issue?.status, completed_at: live.issue?.completedAt, work_products: live.workProducts }
      : { error: live.error },
  })
})

app.post('/agent/tasks/:id/feedback', authenticate, tenantContext, async (req, res) => {
  const taskId = Number(req.params.id)
  if (!taskId) return res.status(400).json({ error: 'invalid id' })
  const { decision, comment } = req.body || {}
  if (!['accept', 'changes'].includes(decision)) {
    return res.status(400).json({ error: 'decision must be accept or changes' })
  }
  const r = await query('SELECT id, company_id FROM agent_tasks WHERE id = $1', [taskId])
  const row = r.rows[0]
  if (!row) return res.status(404).json({ error: 'not found' })
  if (!req.isAdmin && row.company_id !== req.companyId) {
    return res.status(403).json({ error: 'forbidden' })
  }
  await query(
    `UPDATE agent_tasks SET feedback_decision = $1, feedback_comment = $2, feedback_at = NOW() WHERE id = $3`,
    [decision, comment || null, taskId]
  )
  console.log(`[agent-task] feedback id=${taskId} decision=${decision} userId=${req.userId} comment=${(comment || '').slice(0, 80)}`)
  res.json({ ok: true })
})

// Stripe Customer Portal: returns a hosted-portal session URL so customers
// can self-serve plan changes, payment method updates, invoices, cancellation.
app.post('/billing/portal', authenticate, async (req, res) => {
  if (!process.env.STRIPE_SECRET_KEY) {
    return res.status(503).json({ error: 'stripe_not_configured' })
  }
  try {
    const r = await query('SELECT stripe_customer_id FROM users WHERE id = $1', [req.userId])
    const customerId = r.rows[0]?.stripe_customer_id
    if (!customerId) {
      return res.status(400).json({ error: 'no_subscription', message: 'No active subscription on file. Subscribe first from /pricing.' })
    }
    const stripeMod = await import('stripe')
    const Stripe = stripeMod.default || stripeMod.Stripe
    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY)
    const session = await stripe.billingPortal.sessions.create({
      customer: customerId,
      return_url: (process.env.PUBLIC_URL || 'https://newfire.app') + '/dashboard',
    })
    res.json({ url: session.url })
  } catch (err) {
    console.error('[billing/portal] error:', err.message)
    res.status(500).json({ error: err.message })
  }
})

// Stripe webhook: updates tier/budget on subscription events. Signature verified when secret set.
app.post('/webhooks/stripe', async (req, res) => {
  const sig = req.headers['stripe-signature']
  if (!process.env.STRIPE_WEBHOOK_SECRET || !process.env.STRIPE_SECRET_KEY) {
    return res.status(503).json({ error: 'stripe_not_configured' })
  }
  let event
  try {
    const stripeMod = await import('stripe')
    const Stripe = stripeMod.default || stripeMod.Stripe
    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY)
    event = stripe.webhooks.constructEvent(req.body, sig, process.env.STRIPE_WEBHOOK_SECRET)
  } catch (err) {
    console.error('[stripe-webhook] signature failed:', err.message)
    return res.status(400).send(`Webhook Error: ${err.message}`)
  }

  try {
    const obj = event.data.object

    // Resolve userId: prefer stripe_customer_id lookup, fall back to reference/metadata, then email.
    const resolveUserId = async () => {
      const customerId = obj.customer || obj.id
      if (customerId) {
        const r = await query('SELECT id FROM users WHERE stripe_customer_id = $1', [customerId])
        if (r.rows[0]) return r.rows[0].id
      }
      const refId = Number(obj.client_reference_id || obj.metadata?.user_id)
      if (refId) return refId
      const email = obj.customer_email || obj.customer_details?.email
      if (email) {
        const r = await query('SELECT id FROM users WHERE LOWER(email) = LOWER($1)', [email])
        if (r.rows[0]) return r.rows[0].id
      }
      return null
    }

    if (event.type === 'checkout.session.completed') {
      const userId = await resolveUserId()
      const tier = getTier(obj.metadata?.tier_id)
      if (userId && obj.customer) {
        await query(
          `UPDATE users SET stripe_customer_id = $1, stripe_subscription_id = COALESCE($2, stripe_subscription_id) WHERE id = $3`,
          [obj.customer, obj.subscription || null, userId]
        )
      }
      if (userId && tier && tier.id !== 'free') {
        await query(
          `UPDATE companies SET tier = $1, monthly_budget_usd = $2, allow_cloud_models = $3 WHERE user_id = $4`,
          [tier.id, tier.monthly_budget_usd, tier.allow_cloud_models, userId]
        )
        console.log(`[stripe-webhook] checkout completed: user ${userId} -> ${tier.id} (customer ${obj.customer})`)
        emitExternalEvent('subscription.upgraded', { user_id: userId, to_tier: tier.id, stripe_customer_id: obj.customer }).catch(() => {})
      }
    } else if (event.type === 'customer.subscription.created' || event.type === 'customer.subscription.updated') {
      const userId = await resolveUserId()
      const priceId = obj.items?.data?.[0]?.price?.id
      const tier = priceId ? listTiers().find(t => t.stripe_price_id === priceId) : null
      if (userId && obj.id) {
        await query(
          `UPDATE users SET stripe_subscription_id = $1, stripe_customer_id = COALESCE(stripe_customer_id, $2) WHERE id = $3`,
          [obj.id, obj.customer || null, userId]
        )
      }
      if (userId && tier && tier.id !== 'free' && obj.status === 'active') {
        await query(
          `UPDATE companies SET tier = $1, monthly_budget_usd = $2, allow_cloud_models = $3 WHERE user_id = $4`,
          [tier.id, tier.monthly_budget_usd, tier.allow_cloud_models, userId]
        )
        console.log(`[stripe-webhook] subscription ${event.type}: user ${userId} -> ${tier.id}`)
      }
    } else if (event.type === 'customer.subscription.deleted') {
      const userId = await resolveUserId()
      if (userId) {
        const free = getTier('free')
        await query(
          `UPDATE companies SET tier = 'free', monthly_budget_usd = $1, allow_cloud_models = $2 WHERE user_id = $3`,
          [free.monthly_budget_usd, free.allow_cloud_models, userId]
        )
        await query('UPDATE users SET stripe_subscription_id = NULL WHERE id = $1', [userId])
        console.log(`[stripe-webhook] subscription deleted: user ${userId} -> free`)
      }
    }
    res.json({ received: true })
  } catch (err) {
    console.error('[stripe-webhook] handler error:', err.message)
    res.status(500).send(err.message)
  }
})

// Contact form for Enterprise interest
app.post('/contact/enterprise', async (req, res) => {
  const { name, email, company, notes } = req.body || {}
  if (!email) return res.status(400).json({ error: 'email_required' })
  await query(
    `INSERT INTO client_notes (user_id, key, value, updated_at)
     SELECT id, 'enterprise_inquiry', $1, NOW() FROM users WHERE email = $2
     ON CONFLICT DO NOTHING`,
    [JSON.stringify({ name, company, notes, received_at: new Date().toISOString() }), email]
  )
  console.log(`[contact-enterprise] ${email} (${company || 'no company'}): ${(notes || '').slice(0, 100)}`)
  res.json({ ok: true, message: 'Thank you. We will reach out within 1 business day.' })
})

// Public demo chat: no auth, session-capped, uses demo_marketing_agency collection
const DEMO_SESSION_CAP = Number(process.env.DEMO_SESSION_CAP || 5)
const DEMO_IP_DAILY_CAP = Number(process.env.DEMO_IP_DAILY_CAP || 30)
const DEMO_COLLECTION = 'demo_marketing_agency'

const DEMO_SYSTEM_PROMPT = [
  'You are the Lead Responder for Brand Brightly, a boutique marketing agency in the Delmarva region.',
  'This is a live demo a prospective NewFire client is trying out. Show them what a well-trained AI agent feels like.',
  '',
  'VOICE',
  'Be warm, specific, and concise. Match the tone of an experienced marketing strategist who respects the prospect\'s time. Use commas or two short sentences instead of em or en dashes. No exclamation stacking.',
  '',
  'GROUNDING (critical)',
  'You only know what is in the retrieved context about Brand Brightly. If the user asks about hours, pricing, services, or policies and the fact is not in retrieved context, respond: "That is not in my knowledge base yet. In your own NewFire setup, the agent would be trained on your actual business content."',
  'When retrieved context gives you an answer, cite it specifically (exact prices, exact hours, exact minimums).',
  '',
  'CONVERSION',
  'This is a demo for a prospective NewFire client. After answering their question, at the end of your 3rd reply, add a short line: "By the way, what you are seeing is Brand Brightly\'s setup. Your NewFire agent would answer with YOUR business facts instead. Ready to build one?" Do not mention NewFire in earlier replies.',
].join('\n')

app.post('/demo/chat', async (req, res) => {
  try {
    const { session_id, messages } = req.body || {}
    if (!session_id || typeof session_id !== 'string' || session_id.length < 10 || session_id.length > 80) {
      return res.status(400).json({ error: 'Invalid session_id (provide a random 20+ char string)' })
    }
    if (!Array.isArray(messages) || messages.length === 0) {
      return res.status(400).json({ error: 'messages required' })
    }
    const ip = (req.headers['x-forwarded-for'] || req.socket.remoteAddress || '').toString().split(',')[0].trim()

    // Per-session cap
    const sRes = await query('SELECT messages_used FROM demo_sessions WHERE session_id = $1', [session_id])
    let used = 0
    if (sRes.rows.length > 0) {
      used = Number(sRes.rows[0].messages_used || 0)
      if (used >= DEMO_SESSION_CAP) {
        return res.status(429).json({
          error: 'demo_session_cap_reached',
          message_cap: DEMO_SESSION_CAP,
          cta: 'You have used your free demo. Sign up free to build your own agent.',
        })
      }
    } else {
      // Per-IP daily cap
      const ipRes = await query(
        `SELECT COALESCE(SUM(messages_used),0)::int AS total
         FROM demo_sessions
         WHERE ip = $1 AND created_at >= NOW() - INTERVAL '24 hours'`,
        [ip]
      )
      if (Number(ipRes.rows[0].total || 0) >= DEMO_IP_DAILY_CAP) {
        return res.status(429).json({ error: 'demo_daily_cap_reached' })
      }
      await query(
        'INSERT INTO demo_sessions (session_id, ip) VALUES ($1, $2)',
        [session_id, ip]
      )
    }

    // Embed last user message and retrieve from demo collection
    const lastUser = [...messages].reverse().find((m) => m.role === 'user')
    let contextBlock = null
    if (lastUser?.content) {
      const embRes = await fetch(`${OLLAMA_URL}/api/embeddings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: 'nomic-embed-text', prompt: lastUser.content }),
      })
      if (embRes.ok) {
        const { embedding } = await embRes.json()
        const qRes = await fetch(
          `${process.env.QDRANT_URL || 'http://100.88.112.5:6333'}/collections/${DEMO_COLLECTION}/points/search`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'api-key': process.env.QDRANT_API_KEY || '',
            },
            body: JSON.stringify({ vector: embedding, limit: 5, with_payload: true }),
          }
        )
        if (qRes.ok) {
          const data = await qRes.json()
          const hits = data.result || []
          if (hits.length > 0) {
            const lines = hits.map((h, i) => `[${i+1}] (score ${h.score.toFixed(3)}) ${h.payload?.text || ''}`).join('\n\n')
            contextBlock = 'Retrieved context from Brand Brightly knowledge base:\n' + lines
          }
        }
      }
    }

    // Call the LLM
    const fullMessages = [
      { role: 'system', content: DEMO_SYSTEM_PROMPT },
      ...(contextBlock ? [{ role: 'system', content: contextBlock }] : []),
      ...messages,
    ]
    const t0 = Date.now()
    const demoModel = process.env.DEMO_MODEL || 'nvidia/nemotron-3-nano-30b-a3b:free'
    const llmRes = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.OPENROUTER_KEY}`,
        'HTTP-Referer': 'https://newfire.app',
        'X-Title': 'NewFire Demo',
      },
      body: JSON.stringify({ model: demoModel, messages: fullMessages, stream: false }),
    })
    if (!llmRes.ok) {
      const txt = await llmRes.text()
      console.error('[demo] llm error:', txt.slice(0, 200))
      return res.status(500).json({ error: 'demo_chat_failed' })
    }
    const data = await llmRes.json()
    const response = data.choices?.[0]?.message?.content || ''
    const duration = Date.now() - t0

    await query(
      'UPDATE demo_sessions SET messages_used = messages_used + 1, last_active_at = NOW() WHERE session_id = $1',
      [session_id]
    )

    res.json({
      response,
      messages_used: used + 1,
      message_cap: DEMO_SESSION_CAP,
      remaining: Math.max(0, DEMO_SESSION_CAP - (used + 1)),
      latency_ms: duration,
    })
  } catch (err) {
    console.error('[demo] error:', err.message)
    res.status(500).json({ error: err.message })
  }
})

const OLLAMA_URL = process.env.OLLAMA_URL || 'http://100.88.112.5:11434'

// Onboarding chat (uses Ollama directly for the onboarding interview)
app.post('/onboarding/chat', authenticate, async (req, res) => {
  try {
    const { messages } = req.body
    const OLLAMA_URL = process.env.OLLAMA_URL || 'http://100.88.112.5:11434'

    const ollamaRes = await fetch(`${OLLAMA_URL}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: process.env.ONBOARDING_MODEL || 'glm4:9b', messages, stream: false }),
    })

    if (!ollamaRes.ok) throw new Error(`Ollama error: ${ollamaRes.status}`)

    const data = await ollamaRes.json()
    const content = data.choices?.[0]?.message?.content || ''
    res.json({ response: content })
  } catch (err) {
    console.error('[onboarding] Error:', err.message)
    res.status(500).json({ error: err.message })
  }
})

// Parse onboarding result and create company
app.post('/onboarding/activate', authenticate, async (req, res) => {
  try {
    const { companyName, description, agents } = req.body
    if (!companyName || !agents || agents.length === 0) {
      return res.status(400).json({ error: 'Company name and agents are required' })
    }

    const result = await createCompanyForUser(req.userId, companyName, description || '', agents)
    invalidateTenant(req.userId)
    res.json({ success: true, ...result })
  } catch (err) {
    if (err.code === 'COMPANY_EXISTS') return res.status(409).json({ error: err.message, code: 'COMPANY_EXISTS' })
    if (err.code === 'TIER_AGENT_CAP') return res.status(400).json({ error: err.message, code: 'TIER_AGENT_CAP' })
    console.error('[onboarding] Activate error:', err.message)
    res.status(500).json({ error: err.message })
  }
})

registerWebhookRoutes(app, { authenticate })

async function start() {
  await initDatabase()
  await initWebhooksTable()
  app.listen(PORT, () => {
    console.log(`[server] NewFire Backend running on port ${PORT}`)
    console.log(`[server] Auth: POST /auth/signup, POST /auth/login, GET /auth/me`)
    console.log(`[server] Company: GET /company, POST /company/create`)
    console.log(`[server] Chat: POST /chat/:agentId, GET /chat/:agentId/history`)
    console.log(`[server] Onboarding: POST /onboarding/chat, POST /onboarding/activate`)
    console.log(`[server] Webhooks: POST /webhooks/:source, GET /webhooks/stream`)
  })
}

start().catch((err) => {
  console.error('[server] Failed to start:', err)
  process.exit(1)
})
