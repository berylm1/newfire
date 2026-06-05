-- Track customer-initiated agent task delegations and their feedback.
-- The execution itself lives in Paperclip; we keep enough local state to
-- list a customer's tasks, link back to the Paperclip issue, and record
-- the accept / request-changes decision.

BEGIN;

CREATE TABLE IF NOT EXISTS agent_tasks (
  id BIGSERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  paperclip_issue_id VARCHAR(64),
  paperclip_issue_identifier VARCHAR(64),
  paperclip_agent_id VARCHAR(64),
  paperclip_company_id VARCHAR(64),
  title VARCHAR(255),
  task TEXT NOT NULL,
  feedback_decision VARCHAR(32),
  feedback_comment TEXT,
  feedback_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_tasks_user_created ON agent_tasks(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_company_created ON agent_tasks(company_id, created_at DESC);

COMMIT;
