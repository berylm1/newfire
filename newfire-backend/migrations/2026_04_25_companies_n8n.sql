-- Per-tenant n8n: subdomain and webhook URL map per company.
-- The hooks JSONB stores { "user.signup": "https://...", "user.onboarded": "https://...", ... }
-- emitExternalEvent looks here first; if the key is absent it falls back to the env var.

BEGIN;

ALTER TABLE companies ADD COLUMN IF NOT EXISTS n8n_subdomain VARCHAR(64);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS n8n_hooks JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_n8n_subdomain
  ON companies(n8n_subdomain) WHERE n8n_subdomain IS NOT NULL;

COMMIT;
