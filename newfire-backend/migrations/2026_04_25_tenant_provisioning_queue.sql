-- Provisioning queue. Backend enqueues actions; a host-side daemon polls and
-- executes them. Separation needed because provisioning requires sudo and the
-- backend runs in a docker container without privilege.

BEGIN;

CREATE TABLE IF NOT EXISTS tenant_provisioning_queue (
  id BIGSERIAL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  action VARCHAR(64) NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  retry_count INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Daemon's main scan: find next pending or retry-ready row.
CREATE INDEX IF NOT EXISTS idx_tpq_pending_next
  ON tenant_provisioning_queue (next_attempt_at)
  WHERE status IN ('pending', 'failed_retrying');

-- Per-company history.
CREATE INDEX IF NOT EXISTS idx_tpq_company_created
  ON tenant_provisioning_queue (company_id, created_at DESC);

-- Prevent duplicate active queue entries for the same (company, action).
-- Status 'pending', 'in_progress', and 'failed_retrying' all count as active.
CREATE UNIQUE INDEX IF NOT EXISTS idx_tpq_one_active_per_company_action
  ON tenant_provisioning_queue (company_id, action)
  WHERE status IN ('pending', 'in_progress', 'failed_retrying');

COMMIT;
