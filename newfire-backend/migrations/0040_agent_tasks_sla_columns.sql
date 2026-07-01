-- Migration: Add SLA columns to agent_tasks table
-- This migration adds the columns needed for SLA reporting and reconciliation tracking

-- Add SLA tracking columns
ALTER TABLE agent_tasks ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE agent_tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE agent_tasks ADD COLUMN IF NOT EXISTS duration_ms INTEGER;
ALTER TABLE agent_tasks ADD COLUMN IF NOT EXISTS queue_time_ms INTEGER;

-- Add index for efficient reconciliation queries
CREATE INDEX IF NOT EXISTS idx_agent_tasks_status_reconciliation 
ON agent_tasks(status) 
WHERE status IN ('pending', 'running', 'blocked');

-- Add index for tenant isolation in reconciliation
CREATE INDEX IF NOT EXISTS idx_agent_tasks_company_status 
ON agent_tasks(company_id, status) 
WHERE status IN ('pending', 'running', 'blocked');

-- Add index for timeout detection
CREATE INDEX IF NOT EXISTS idx_agent_tasks_started_at 
ON agent_tasks(started_at) 
WHERE status IN ('pending', 'running', 'blocked');

-- Migration tracking
INSERT INTO schema_migrations (version, applied_at)
VALUES ('0040', NOW())
ON CONFLICT (version) DO NOTHING;
