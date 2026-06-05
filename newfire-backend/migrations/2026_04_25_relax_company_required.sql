-- Hotfix: relax users_company_required_for_non_admin so signups work.
-- Original constraint blocked the legitimate signup window where a user exists
-- but has not yet completed onboarding (and therefore has no company yet).
-- New rule: company_id is required only for non-admin users who have onboarded.

BEGIN;

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_company_required_for_non_admin;
ALTER TABLE users ADD CONSTRAINT users_company_required_for_non_admin
  CHECK (role = 'admin' OR onboarded = false OR company_id IS NOT NULL);

COMMIT;
