// CEO conversation handler. Single endpoint customers talk to. The LLM acts
// as a "company consultant" that can invoke tools to actually build/modify
// the customer's company. Tools are detected by parsing fenced JSON blocks
// in the LLM's response and executed server-side.

import { query } from './db.js'
import { proxyChat } from './orchestrator.js'

const CEO_AGENT_ID = '_ceo'

const SYSTEM_PROMPT_TEMPLATE = (companyName) => `You are the AI Company Consultant for ${companyName || 'this company'}.

You help the owner think through what their business needs. You ask short, useful clarifying questions about their business, then offer to set up AI agents and workflows for them. Your job is to be conversational and clear, not technical.

When the owner agrees to add an agent, output a tool block in this exact format on its own lines, after your conversational text:

\`\`\`tool
{"name": "create_agent", "args": {"name": "<short title>", "role": "<one phrase>", "description": "<2 short sentences about what this agent will do>"}}
\`\`\`

Rules:
- ALWAYS ask once before invoking a tool. ("Want me to set that up?")
- ONE tool block per response, max.
- Keep names short like "Receptionist" or "Content Writer".
- Don't use technical words like "API", "deployment", "container", "endpoint".
- If the owner asks what you can do, list 2-3 examples in plain language and ask what fits their business.

If you don't need a tool, just reply normally without any \`\`\`tool block.`

function extractToolBlocks(text) {
  const blocks = []
  const re = /```tool\s*\n([\s\S]*?)\n```/g
  let m
  while ((m = re.exec(text)) !== null) {
    try {
      blocks.push({ raw: m[0], parsed: JSON.parse(m[1]) })
    } catch (err) {
      blocks.push({ raw: m[0], parseError: err.message })
    }
  }
  return blocks
}

async function loadConversation(userId) {
  const r = await query(
    'SELECT messages FROM conversations WHERE user_id = $1 AND agent_id = $2',
    [userId, CEO_AGENT_ID]
  )
  return r.rows[0]?.messages || []
}

async function saveConversation(userId, messages) {
  await query(
    `INSERT INTO conversations (user_id, agent_id, messages, updated_at)
     VALUES ($1, $2, $3::jsonb, NOW())
     ON CONFLICT (user_id, agent_id)
     DO UPDATE SET messages = $3::jsonb, updated_at = NOW()`,
    [userId, CEO_AGENT_ID, JSON.stringify(messages)]
  )
}

async function executeCreateAgent(args, ctx) {
  const name = String(args?.name || '').trim()
  const role = String(args?.role || '').trim()
  const description = String(args?.description || '').trim()
  if (!name || !role) {
    return { ok: false, error: 'create_agent requires name and role' }
  }
  // Tier cap check.
  const cmp = await query('SELECT tier FROM companies WHERE id = $1', [ctx.companyId])
  const tier = cmp.rows[0]?.tier || 'free'
  const cap = tier === 'free' ? 3 : tier === 'starter' ? 5 : tier === 'pro' ? 15 : null
  if (cap !== null) {
    const cnt = await query('SELECT COUNT(*)::int AS n FROM agents WHERE company_id = $1', [ctx.companyId])
    if (Number(cnt.rows[0].n) >= cap) {
      return { ok: false, error: `${tier} tier supports up to ${cap} agents. Trim or upgrade at /pricing.` }
    }
  }
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || `agent-${Date.now()}`
  const systemPrompt = `You are ${name}. Your role: ${role}. ${description}\n\nBe warm, direct, professional. Use commas or two short sentences instead of em dashes or en dashes. If asked about a fact you do not know, say so honestly and offer to follow up with the owner.`
  const ins = await query(
    `INSERT INTO agents (company_id, agent_id, name, role, description, system_prompt, model, provider, icon, color, status)
     VALUES ($1, $2, $3, $4, $5, $6, 'glm4:9b', 'local', 'MessageSquare', 'from-fire-500 to-fire-600', 'active')
     RETURNING id, agent_id, name, role`,
    [ctx.companyId, slug, name, role, description, systemPrompt]
  )
  return { ok: true, agent: ins.rows[0] }
}

const TOOLS = {
  create_agent: executeCreateAgent,
}

async function executeTools(blocks, ctx) {
  const results = []
  for (const b of blocks) {
    if (b.parseError) {
      results.push({ name: '?', ok: false, error: 'tool block was not valid JSON' })
      continue
    }
    const handler = TOOLS[b.parsed?.name]
    if (!handler) {
      results.push({ name: b.parsed?.name || '?', ok: false, error: `unknown tool: ${b.parsed?.name}` })
      continue
    }
    try {
      const result = await handler(b.parsed.args || {}, ctx)
      results.push({ name: b.parsed.name, ...result })
    } catch (err) {
      results.push({ name: b.parsed.name, ok: false, error: err.message })
    }
  }
  return results
}

function renderToolNotes(results) {
  if (!results.length) return ''
  return '\n\n' + results.map((r) => {
    if (r.ok && r.name === 'create_agent') {
      return `_(Done. Your "${r.agent.name}" agent is now live in your team.)_`
    }
    if (r.ok) return `_(Done.)_`
    return `_(I couldn't do that: ${r.error})_`
  }).join('\n')
}

export async function ceoChat(req, res) {
  const { message, reset } = req.body || {}
  if (typeof message !== 'string' || !message.trim()) {
    return res.status(400).json({ error: 'message string required' })
  }

  const userRow = await query('SELECT email, name FROM users WHERE id = $1', [req.userId])
  const companyRow = await query('SELECT name FROM companies WHERE id = $1', [req.companyId])
  const companyName = companyRow.rows[0]?.name || userRow.rows[0]?.name || 'your business'

  const history = reset ? [] : await loadConversation(req.userId)
  const userMsg = { role: 'user', content: message.trim(), at: new Date().toISOString() }
  const messagesForLLM = [
    { role: 'system', content: SYSTEM_PROMPT_TEMPLATE(companyName) },
    ...history.map(({ role, content }) => ({ role, content })),
    { role: 'user', content: message.trim() },
  ]

  let assistantContent = ''
  let toolResults = []
  try {
    const out = await proxyChat({
      userId: req.userId,
      companyId: req.companyId,
      isAdmin: req.isAdmin,
      messages: messagesForLLM,
      model: process.env.CEO_MODEL || 'nvidia/nemotron-3-nano-30b-a3b:free',
      temperature: 0.5,
    })
    assistantContent = out.content || ''
    const blocks = extractToolBlocks(assistantContent)
    if (blocks.length) {
      toolResults = await executeTools(blocks, { userId: req.userId, companyId: req.companyId })
      // Strip the raw tool block from the visible message; append plain-language note.
      assistantContent = blocks.reduce((acc, b) => acc.replace(b.raw, ''), assistantContent).trim()
      assistantContent += renderToolNotes(toolResults)
    }
  } catch (err) {
    console.error('[ceo] chat error:', err.message)
    return res.status(502).json({ error: 'consultant_unavailable', detail: err.message })
  }

  const assistantMsg = { role: 'assistant', content: assistantContent, at: new Date().toISOString() }
  const newHistory = [...history, userMsg, assistantMsg]
  await saveConversation(req.userId, newHistory)

  res.json({
    message: assistantMsg,
    tool_results: toolResults,
    history_length: newHistory.length,
  })
}

export async function ceoHistory(req, res) {
  const history = await loadConversation(req.userId)
  res.json({ messages: history })
}

export async function ceoReset(req, res) {
  await saveConversation(req.userId, [])
  res.json({ ok: true })
}
