# 2026-06-05 - CEO Agent Issue 18 Tenant RBAC Harness PR Notes

## GitHub

- Issue: [#18 Testing: implement tenant/RBAC integration harness for backend](https://github.com/berylm1/newfire/issues/18)
- PR: [#25 test(backend): add tenant RBAC harness](https://github.com/berylm1/newfire/pull/25)
- Branch: `test/issue-18-tenant-rbac-harness`
- Commit: `f8ce6157b52c16ef5afc7e2192f8db1ff6067e7a`
- Status: open, clean, mergeable; no GitHub checks configured.

## What changed

- Added `newfire-backend/tests/tenant-rbac.test.js`.
- Added backend `npm test` script using Node's built-in test runner.
- Added test-only query injection hooks in `newfire-backend/src/db.js` so backend modules can be exercised without production DB access.
- Extracted `getTenantAgent(companyId, agentId)` in `newfire-backend/src/orchestrator.js` and reused it from `chatWithAgent` for explicit tenant-scoped lookup.

## Test coverage

The harness covers:

- signup and login token generation;
- company creation;
- user-to-company tenant assignment;
- tenant-scoped agent listing;
- cross-tenant denial for agent lookup.

## TDD evidence

- RED: `node --test tests/tenant-rbac.test.js` failed because `db.setQueryImplementation` did not exist.
- GREEN: added DB query injection hooks and tenant-scoped agent resolver; tests now pass.

## Verification

From `newfire-backend/`:

```bash
npm install --ignore-scripts
npm test
node --check src/db.js
node --check src/orchestrator.js
node --check tests/tenant-rbac.test.js
git diff --check
```

Results:

- `npm test`: 3 tests passed.
- `node --check`: passed for touched JS files and test file.
- `git diff --check`: passed.

## CEO reporting angle

This advances lane **E: Testing / QA / resilience** and supports lane **C: Security**.

CEO-facing line:

> We added the first backend tenant/RBAC integration harness. It runs without production secrets or a production database and verifies signup/login, company creation, tenant assignment, tenant-scoped agent access, and cross-tenant denial.

## Next work

- Issue #19: webhook signature, replay, idempotency, and invalid payload regression tests.
- Issue #22: GitHub-wide OpenClaw control-plane design.
- Issue #11: product gap/orphan feature audit.
