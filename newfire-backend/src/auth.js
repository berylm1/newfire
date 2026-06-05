import bcrypt from 'bcrypt'
import jwt from 'jsonwebtoken'
import { query } from './db.js'

const JWT_SECRET = process.env.JWT_SECRET
if (!JWT_SECRET || JWT_SECRET.length < 32) {
  console.error('[auth] FATAL: JWT_SECRET env var is required and must be at least 32 chars')
  process.exit(1)
}
const SALT_ROUNDS = 10

export async function signup(email, password, name) {
  const existing = await query('SELECT id FROM users WHERE email = $1', [email.toLowerCase()])
  if (existing.rows.length > 0) {
    throw new Error('Email already registered')
  }

  const hash = await bcrypt.hash(password, SALT_ROUNDS)
  const result = await query(
    'INSERT INTO users (email, password_hash, name) VALUES ($1, $2, $3) RETURNING id, email, name, role, onboarded',
    [email.toLowerCase(), hash, name]
  )

  const user = result.rows[0]
  const token = jwt.sign({ id: user.id, email: user.email }, JWT_SECRET, { expiresIn: '7d' })
  return { user, token }
}

export async function login(email, password) {
  const result = await query('SELECT * FROM users WHERE email = $1', [email.toLowerCase()])
  if (result.rows.length === 0) {
    throw new Error('Invalid email or password')
  }

  const user = result.rows[0]
  const valid = await bcrypt.compare(password, user.password_hash)
  if (!valid) {
    throw new Error('Invalid email or password')
  }

  const token = jwt.sign({ id: user.id, email: user.email }, JWT_SECRET, { expiresIn: '7d' })
  return {
    user: { id: user.id, email: user.email, name: user.name, role: user.role, onboarded: user.onboarded },
    token,
  }
}

export function authenticate(req, res, next) {
  const header = req.headers.authorization
  if (!header || !header.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Authentication required' })
  }

  try {
    const decoded = jwt.verify(header.split(' ')[1], JWT_SECRET)
    req.userId = decoded.id
    req.userEmail = decoded.email
    next()
  } catch {
    return res.status(401).json({ error: 'Invalid or expired token' })
  }
}

export async function getUser(userId) {
  const result = await query(
    'SELECT id, email, name, role, onboarded, created_at FROM users WHERE id = $1',
    [userId]
  )
  return result.rows[0] || null
}

export async function setOnboarded(userId) {
  await query('UPDATE users SET onboarded = TRUE WHERE id = $1', [userId])
}
