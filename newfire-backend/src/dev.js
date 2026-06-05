// Developer platform endpoints. Forwards instructions to the OpenHands shim
// (which translates to OpenHands' multi-step conversation protocol). Sessions
// are persisted so devs can review past runs and so we have an audit trail.

import { query } from './db.js'

const SHIM_URL = process.env.OPENHANDS_SHIM_URL || 'http://openhands-shim:8080'
const SHIM_TIMEOUT_MS = Number(process.env.OPENHANDS_SHIM_TIMEOUT_MS || 180_000)
const ALLOWED_ROLES = new Set(['developer', 'admin'])

function buildClonePrelude({ repo, branch, gitToken }) {
  if (!repo) return ''
  let cloneUrl = repo.trim()
  if (gitToken && /^https?:\/\/github\.com\//i.test(cloneUrl)) {
    cloneUrl = cloneUrl.replace(/^https?:\/\/github\.com\//i, `https://x-access-token:${gitToken}@github.com/`)
  }
  const branchClause = branch ? ` (branch ${branch})` : ''
  const checkout = branch ? `git checkout ${branch} && ` : ''
  return [
    `Before doing anything else, set up the working repository:`,
    `1. Run: cd /workspace && git clone ${cloneUrl} repo${branchClause}`,
    `2. cd repo && ${checkout}ls`,
    `3. Treat /workspace/repo as the project root for everything that follows.`,
    ``,
    `Then complete this task:`,
    ``,
  ].join('\n')
}

export function requireDeveloper(req, res, next) {
  // Caller must already be authenticated; attaches user.
  ;(async () => {
    try {
      const r = await query('SELECT role FROM users WHERE id = $1', [req.userId])
      const role = r.rows[0]?.role
      if (!role || !ALLOWED_ROLES.has(role)) {
        return res.status(403).json({ error: 'Developer access required', current_role: role || null })
      }
      req.userRole = role
      next()
    } catch (err) {
      console.error('[dev] role check failed:', err.message)
      res.status(500).json({ error: 'role_check_failed' })
    }
  })()
}

async function executeShimTask({ sessionId, finalInstruction, startedAt }) {
  try {
    // Node's built-in fetch (undici) has a 5-minute idle timeout that triggers
    // even with a longer signal. Use raw http.request so we can control the
    // socket idle timeout explicitly for long-running OpenHands conversations.
    const http = await import('http')
    const url = new URL(`${SHIM_URL}/task`)
    const body = JSON.stringify({ instruction: finalInstruction })
    const { status, text } = await new Promise((resolve, reject) => {
      const req = http.request({
        method: 'POST',
        hostname: url.hostname,
        port: url.port || 80,
        path: url.pathname,
        headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
      }, (res) => {
        let chunks = []
        res.on('data', (c) => chunks.push(c))
        res.on('end', () => resolve({ status: res.statusCode, text: Buffer.concat(chunks).toString('utf8') }))
        res.on('error', reject)
      })
      req.setTimeout(SHIM_TIMEOUT_MS, () => req.destroy(new Error('shim_timeout')))
      req.on('error', reject)
      req.write(body)
      req.end()
    })
    const shimRes = { ok: status >= 200 && status < 300, status }
    let json
    try { json = text ? JSON.parse(text) : {} } catch { json = { _raw: text } }

    if (!shimRes.ok) {
      await query(
        `UPDATE dev_openhands_sessions
         SET status = 'failed', error = $1, duration_ms = $2, completed_at = NOW()
         WHERE id = $3`,
        [String(json?.error || text).slice(0, 1000), Date.now() - startedAt, sessionId]
      )
      console.error(`[dev] session=${sessionId} shim error: ${json?.error || text}`)
      return
    }

    const result = json?.result || json?._raw || ''
    const finalStatus = json?.timedOut ? 'timed_out' : 'completed'
    await query(
      `UPDATE dev_openhands_sessions
       SET status = $1, response = $2, conversation_id = $3, duration_ms = $4, completed_at = NOW()
       WHERE id = $5`,
      [finalStatus, result.slice(0, 100_000), json?.conversationId || null, Date.now() - startedAt, sessionId]
    )
    console.log(`[dev] session=${sessionId} done status=${finalStatus} duration=${Date.now() - startedAt}ms`)
  } catch (err) {
    const aborted = err.message === 'shim_timeout' || err.name === 'AbortError'
    await query(
      `UPDATE dev_openhands_sessions
       SET status = $1, error = $2, duration_ms = $3, completed_at = NOW()
       WHERE id = $4`,
      [aborted ? 'timed_out' : 'failed', err.message.slice(0, 1000), Date.now() - startedAt, sessionId]
    )
    console.error(`[dev] session=${sessionId} error: ${err.message}`)
  }
}

export async function runOpenHandsTask(req, res) {
  const { instruction, repo, branch, git_token } = req.body || {}
  if (typeof instruction !== 'string' || !instruction.trim()) {
    return res.status(400).json({ error: 'instruction string required' })
  }
  if (repo && typeof repo !== 'string') {
    return res.status(400).json({ error: 'repo must be a string URL' })
  }
  const prelude = buildClonePrelude({ repo, branch, gitToken: git_token })
  const finalInstruction = prelude + instruction.trim()

  const ins = await query(
    `INSERT INTO dev_openhands_sessions (user_id, instruction, repo, branch, status)
     VALUES ($1, $2, $3, $4, 'in_progress')
     RETURNING id, created_at`,
    [req.userId, instruction.trim(), repo || null, branch || null]
  )
  const sessionId = ins.rows[0].id
  const startedAt = Date.now()

  // Fire and forget. Dev polls /dev/openhands/sessions/:id for completion.
  executeShimTask({ sessionId, finalInstruction, startedAt })

  res.status(202).json({
    session_id: sessionId,
    status: 'in_progress',
    poll_url: `/dev/openhands/sessions/${sessionId}`,
  })
}

export async function listSessions(req, res) {
  const limit = Math.min(Number(req.query.limit) || 25, 100)
  const r = await query(
    `SELECT id, instruction, repo, branch, status, conversation_id, duration_ms,
            created_at, completed_at,
            CASE WHEN response IS NULL THEN NULL
                 ELSE LEFT(response, 240) END AS response_preview
     FROM dev_openhands_sessions
     WHERE user_id = $1
     ORDER BY id DESC
     LIMIT $2`,
    [req.userId, limit]
  )
  res.json({ sessions: r.rows })
}

export async function getSession(req, res) {
  const id = Number(req.params.id)
  if (!Number.isInteger(id) || id <= 0) return res.status(400).json({ error: 'bad id' })
  const r = await query(
    `SELECT id, user_id, instruction, repo, branch, status, response, error,
            conversation_id, duration_ms, created_at, completed_at
     FROM dev_openhands_sessions
     WHERE id = $1`,
    [id]
  )
  const row = r.rows[0]
  if (!row) return res.status(404).json({ error: 'not_found' })
  if (row.user_id !== req.userId && req.userRole !== 'admin') {
    return res.status(403).json({ error: 'forbidden' })
  }
  res.json({ session: row })
}
