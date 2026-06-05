import { query } from './db.js'

const TTL_MS = 5 * 60 * 1000
const cache = new Map()

function readCache(userId) {
  const entry = cache.get(userId)
  if (!entry) return null
  if (entry.expiresAt < Date.now()) {
    cache.delete(userId)
    return null
  }
  return entry.value
}

function writeCache(userId, value) {
  cache.set(userId, { value, expiresAt: Date.now() + TTL_MS })
}

export function invalidateTenant(userId) {
  cache.delete(userId)
}

export async function loadTenant(userId) {
  const cached = readCache(userId)
  if (cached) return cached
  const result = await query(
    'SELECT id, role, company_id FROM users WHERE id = $1',
    [userId]
  )
  const row = result.rows[0]
  if (!row) return null
  const value = { userId: row.id, role: row.role, companyId: row.company_id, isAdmin: row.role === 'admin' }
  writeCache(userId, value)
  return value
}

export async function tenantContext(req, res, next) {
  if (!req.userId) {
    return res.status(401).json({ error: 'Authentication required' })
  }
  try {
    const tenant = await loadTenant(req.userId)
    if (!tenant) return res.status(401).json({ error: 'User not found' })
    if (!tenant.isAdmin && !tenant.companyId) {
      return res.status(403).json({ error: 'No tenant assigned for this user' })
    }
    req.companyId = tenant.companyId
    req.isAdmin = tenant.isAdmin
    req.role = tenant.role
    next()
  } catch (err) {
    console.error('[tenant] resolve failed:', err.message)
    res.status(500).json({ error: 'Tenant resolution failed' })
  }
}
