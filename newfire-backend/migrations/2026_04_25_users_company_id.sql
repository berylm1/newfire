-- Migration: add users.company_id with backfill and CHECK constraint
-- Date: 2026-04-25
-- Purpose: canonical tenant key on users; required for non-admin roles
-- Idempotent: safe to re-run

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id);

UPDATE users u
SET company_id = c.id
FROM (
  SELECT DISTINCT ON (user_id) id, user_id
  FROM companies
  WHERE user_id IS NOT NULL
  ORDER BY user_id, created_at DESC
) c
WHERE u.id = c.user_id AND u.company_id IS DISTINCT FROM c.id;

DO $$
DECLARE
  bad_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO bad_count
  FROM users
  WHERE role <> 'admin' AND company_id IS NULL;
  IF bad_count > 0 THEN
    RAISE EXCEPTION 'migration aborted: % non-admin users have no company_id', bad_count;
  END IF;
END $$;

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_company_required_for_non_admin;
ALTER TABLE users ADD CONSTRAINT users_company_required_for_non_admin
  CHECK (role = 'admin' OR company_id IS NOT NULL) NOT VALID;
ALTER TABLE users VALIDATE CONSTRAINT users_company_required_for_non_admin;

COMMIT;
