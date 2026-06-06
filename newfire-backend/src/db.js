import pg from 'pg'

if (!process.env.DB_PASSWORD) {
  console.error('[db] FATAL: DB_PASSWORD env var is required')
  process.exit(1)
}

const pool = new pg.Pool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: parseInt(process.env.DB_PORT || '5432'),
  user: process.env.DB_USER || 'newfire',
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME || 'newfire',
  max: 20,
})

let queryImplementation = null

export function setQueryImplementation(fn) {
  queryImplementation = fn
}

export function resetQueryImplementation() {
  queryImplementation = null
}

export async function query(text, params) {
  if (queryImplementation) return queryImplementation(text, params)
  const res = await pool.query(text, params)
  return res
}

export async function initDatabase() {
  await query(`
    CREATE TABLE IF NOT EXISTS users (
      id SERIAL PRIMARY KEY,
      email VARCHAR(255) UNIQUE NOT NULL,
      password_hash VARCHAR(255) NOT NULL,
      name VARCHAR(255) NOT NULL,
      role VARCHAR(50) DEFAULT 'user',
      onboarded BOOLEAN DEFAULT FALSE,
      created_at TIMESTAMP DEFAULT NOW()
    )
  `)

  await query(`
    CREATE TABLE IF NOT EXISTS companies (
      id SERIAL PRIMARY KEY,
      user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
      name VARCHAR(255) NOT NULL,
      description TEXT,
      paperclip_id VARCHAR(255),
      qdrant_collection VARCHAR(255),
      created_at TIMESTAMP DEFAULT NOW()
    )
  `)
  await query('ALTER TABLE companies ADD COLUMN IF NOT EXISTS qdrant_collection VARCHAR(255)')
  await query('ALTER TABLE companies ADD COLUMN IF NOT EXISTS monthly_budget_usd NUMERIC(10,2) DEFAULT 5.00')
  await query('ALTER TABLE companies ADD COLUMN IF NOT EXISTS allow_cloud_models BOOLEAN DEFAULT TRUE')
  await query('ALTER TABLE companies ADD COLUMN IF NOT EXISTS tier VARCHAR(30) DEFAULT \'free\'')

  await query('ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(64)')
  await query('ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(64)')
  await query('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_stripe_customer ON users(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL')

  await query(`
    CREATE TABLE IF NOT EXISTS agents (
      id SERIAL PRIMARY KEY,
      company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
      agent_id VARCHAR(100) NOT NULL,
      name VARCHAR(255) NOT NULL,
      role TEXT,
      description TEXT,
      system_prompt TEXT,
      model VARCHAR(100) DEFAULT 'gemma4:26b',
      provider VARCHAR(50) DEFAULT 'local',
      openclaw_worker_id VARCHAR(255),
      icon VARCHAR(50) DEFAULT 'MessageSquare',
      color VARCHAR(100) DEFAULT 'from-blue-500 to-blue-600',
      status VARCHAR(20) DEFAULT 'active',
      created_at TIMESTAMP DEFAULT NOW()
    )
  `)

  await query(`
    CREATE TABLE IF NOT EXISTS conversations (
      id SERIAL PRIMARY KEY,
      user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
      agent_id VARCHAR(100) NOT NULL,
      messages JSONB DEFAULT '[]'::jsonb,
      updated_at TIMESTAMP DEFAULT NOW()
    )
  `)

  await query(`
    CREATE UNIQUE INDEX IF NOT EXISTS idx_conversations_user_agent
    ON conversations(user_id, agent_id)
  `)

  await query(`
    CREATE TABLE IF NOT EXISTS client_notes (
      id SERIAL PRIMARY KEY,
      user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
      key VARCHAR(100) NOT NULL,
      value TEXT,
      updated_by INTEGER REFERENCES users(id),
      updated_at TIMESTAMP DEFAULT NOW(),
      UNIQUE(user_id, key)
    )
  `)

  await query(`
    CREATE TABLE IF NOT EXISTS chat_metrics (
      id BIGSERIAL PRIMARY KEY,
      user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
      agent_id VARCHAR(100),
      model VARCHAR(120),
      provider VARCHAR(40),
      input_tokens INTEGER,
      output_tokens INTEGER,
      total_tokens INTEGER,
      temperature NUMERIC(4,2),
      context_window INTEGER,
      context_used_tokens INTEGER,
      context_used_pct INTEGER,
      duration_ms INTEGER,
      status VARCHAR(20),
      created_at TIMESTAMPTZ DEFAULT NOW()
    )
  `)
  await query(`
    CREATE TABLE IF NOT EXISTS demo_sessions (
      id BIGSERIAL PRIMARY KEY,
      session_id VARCHAR(100) UNIQUE NOT NULL,
      ip VARCHAR(64),
      messages_used INTEGER DEFAULT 0,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      last_active_at TIMESTAMPTZ DEFAULT NOW(),
      converted_user_id INTEGER
    )
  `)
  await query('CREATE INDEX IF NOT EXISTS idx_demo_sessions_ip ON demo_sessions(ip, created_at DESC)')

  await query('CREATE INDEX IF NOT EXISTS idx_chat_metrics_created ON chat_metrics(created_at DESC)')
  await query('CREATE INDEX IF NOT EXISTS idx_chat_metrics_user_agent ON chat_metrics(user_id, agent_id, created_at DESC)')
  await query('CREATE INDEX IF NOT EXISTS idx_chat_metrics_model ON chat_metrics(model, created_at DESC)')

  await query(`
    CREATE TABLE IF NOT EXISTS dev_openhands_sessions (
      id BIGSERIAL PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      instruction TEXT NOT NULL,
      repo TEXT,
      branch TEXT,
      status VARCHAR(32) NOT NULL DEFAULT 'in_progress',
      response TEXT,
      error TEXT,
      conversation_id TEXT,
      duration_ms INTEGER,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      completed_at TIMESTAMPTZ
    )
  `)
  await query('CREATE INDEX IF NOT EXISTS idx_dev_oh_sessions_user_created ON dev_openhands_sessions (user_id, created_at DESC)')

  console.log('[db] Database tables initialized')
}

export default pool
