# CEO Agent Readiness Pass — Tasks 1-5

Date: 2026-06-04
Branch: `docs/ceo-directive-readiness-pass`

## Executive summary

This pass implements the CEO directive as a governed, repeatable platform-readiness workflow. It completes the first evidence-backed pass for tasks 1-5: backend source-control merge, codebase intelligence, security threat modeling, testing/resilience planning, and performance/readiness scoring.

## Task 1 — Backend source officially tracked

PR #9 was reviewed as mergeable/clean and squash-merged into `main`.

Result:

- `newfire-backend/` is now tracked in `berylm1/newfire`.
- Backend implementation work can proceed through branches/PRs.
- Production worker mirror `/home/newwaveclaw/newfire-backend` should no longer be edited directly for governed work.

## Task 2 — Codebase/service intelligence inventory

A repeatable read-only scanner was added:

- `scripts/ceo_readiness_audit.py`

It maps:

- service inventory;
- file/line counts;
- backend HTTP routes;
- backend environment-variable dependencies.

Initial evidence:

- 4 primary tracked service surfaces:
  - `newfire-backend/`
  - `openclaw/`
  - `newfire_backend_docker/`
  - `infra/`
- 45 backend route registrations detected.
- 46 backend environment variables detected.
- Largest backend risk files:
  - `newfire-backend/src/server.js` — 1109 lines
  - `newfire-backend/src/orchestrator.js` — 925 lines
  - `newfire-backend/src/paperclip.js` — agent delegation/provisioning
  - `newfire-backend/src/dev.js` — OpenHands execution bridge
  - `newfire-backend/src/auth.js`, `tenant.js`, `webhooks.js`, `db.js`

See: `docs/ceo-agent/service-inventory.md`

## Task 3 — Security threat model and hardening backlog

Initial compromise paths were mapped across external and internal attack surfaces.

Highest-priority findings:

1. Public auth routes lack documented brute-force/rate-limit tests.
2. `cors()` currently allows default permissive behavior unless constrained by upstream proxy.
3. Security headers/helmet are not present in the backend dependency/runtime path.
4. `npm audit` reports 11 dependency vulnerabilities from the lockfile: 4 high, 7 moderate.
5. Agent execution paths (`/dev/openhands`, OpenClaw, Paperclip/OpenHands) need explicit sandbox/token boundary tests.
6. Tenant/RBAC boundaries remain the highest business-security test gap.
7. Webhook replay/signature behavior needs regression coverage.

See: `docs/ceo-agent/security-threat-model.md`

## Task 4 — Testing/resilience matrix

Verification performed in this pass:

- Backend syntax check: `node --check newfire-backend/src/*.js` passed.
- Backend npm audit from lockfile: 11 vulnerabilities found, documented for follow-up.
- OpenClaw test execution attempted in a temp venv; current branch reports no collected tests under `openclaw/tests`, so test discovery/merge state must be reconciled with PR #7.

Testing priorities:

1. Tenant/RBAC integration tests.
2. Auth brute-force and invalid-token regression tests.
3. Webhook signature/replay/idempotency tests.
4. Agent delegation authorization and timeout/failure tests.
5. RAG/Qdrant isolation tests.
6. Load and chaos tests against local/staging only, not production.

See: `docs/ceo-agent/testing-resilience-matrix.md`

## Task 5 — Performance baseline and readiness scorecard

Performance SLO targets were defined for the first governed benchmark pass:

- Health endpoint p95 target: under 100 ms local/staging.
- Auth/login p95 target: under 300 ms excluding bcrypt cost; bcrypt cost should be separately measured.
- Chat proxy p95 target: provider-dependent; track gateway overhead separately from model latency.
- Webhook acknowledgement p95 target: under 250 ms before async downstream work.
- Metrics endpoint p95 target: under 100 ms internal scrape.

Initial production-readiness snapshot:

- `newfire-backend`: 54/100 — now source-controlled, but needs tenant/RBAC tests, security hardening, dependency upgrades, and benchmark baselines.
- `openclaw`: 58/100 — clear service shape and auth posture, but test discovery is currently not passing in this branch and execution/sandbox coverage is required.
- `newfire_backend_docker`: 62/100 — documented deploy artifact, but image tag/source path drift and rollout/rollback checks need tightening.
- `infra`: 50/100 — docs/artifacts exist, but production ingress assumptions and readiness checks need formal score evidence.

See: `docs/ceo-agent/performance-and-readiness-scorecard.md`

## Task 6 — Product gap / missing feature / orphan audit

The first issue #11 audit is now captured in:

- `docs/ceo-agent/product-gap-orphan-audit.md`

It identifies three immediate implementation issues:

1. #27 — full platform source-control manifest and audit gate.
2. #28 — productize onboarding interview to provisioned company flow.
3. #29 — backend agent task reconciliation worker and SLA lifecycle.

## Governance status

Source-control preflight is now explicit for governed agent work:

- `docs/ceo-agent/source-control-manifest.json` lists the GitHub governance status for every known NewFire service.
- `scripts/check_source_control_manifest.py` fails strict preflight when a production/load-bearing service lacks a GitHub repo or approved vendored baseline.
- Current strict blockers are frontend plus NSS control/runner/portal/router; scaffolds MCP and SDK are deferred and excluded from production-ready scoring until promoted.

No destructive actions were performed:

- No production load testing.
- No chaos testing against production.
- No deployments.
- No service restarts.
- No migrations.
- No secret changes.

## Recommended next implementation PRs

1. #16 Dependency hardening: upgrade vulnerable backend dependencies and re-run `npm audit`.
2. #17 Backend security middleware: add explicit CORS allowlist, security headers, request ID, and auth-rate-limit controls.
3. #18 Tenant/RBAC tests: implement the backend integration harness now that backend source is tracked.
4. #19 Webhook security tests: signature, replay/idempotency, invalid payloads.
5. #20 Benchmark harness: add local/staging-only k6/autocannon scripts with safe defaults.
