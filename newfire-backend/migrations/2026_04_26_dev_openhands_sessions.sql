-- Developer platform: OpenHands task sessions per developer.
-- Logs every /dev/openhands invocation for audit and "history" UI.

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
);

CREATE INDEX IF NOT EXISTS idx_dev_oh_sessions_user_created
  ON dev_openhands_sessions (user_id, created_at DESC);
