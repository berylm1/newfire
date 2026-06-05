-- Track when we've already fired agent.task.completed for an agent_tasks row,
-- so we don't duplicate the webhook every time the SPA polls /agent/tasks/:id.

BEGIN;

ALTER TABLE agent_tasks ADD COLUMN IF NOT EXISTS completion_notified_at TIMESTAMPTZ;

COMMIT;
