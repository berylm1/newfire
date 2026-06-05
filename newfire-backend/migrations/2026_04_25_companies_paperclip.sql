-- Track Paperclip provisioning per NewFire tenant.
-- paperclip_company_id is the UUID returned by Paperclip's POST /api/companies.
-- paperclip_status records the outcome so the admin dashboard can surface
-- failures without blocking signup.

BEGIN;

ALTER TABLE companies ADD COLUMN IF NOT EXISTS paperclip_company_id VARCHAR(64);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS paperclip_status VARCHAR(32) DEFAULT 'not_attempted';
ALTER TABLE companies ADD COLUMN IF NOT EXISTS paperclip_error TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS paperclip_provisioned_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_companies_paperclip_status
  ON companies(paperclip_status) WHERE paperclip_status <> 'created';

COMMIT;
