# Performance and Production Readiness Scorecard

Purpose: provide the first CEO-facing production-readiness and completion score for tracked NewFire services and features.

## Benchmark targets

These are initial targets for local/staging measurement. Production load tests require explicit approval.

### Backend HTTP/API

- `GET /health`: p95 under 100 ms local/staging.
- `GET /metrics`: p95 under 100 ms internal scrape.
- `POST /auth/login`: p95 under 300 ms excluding bcrypt calibration; bcrypt cost should be tracked separately.
- `POST /auth/signup`: p95 under 500 ms excluding downstream webhook emission.
- `POST /webhooks/:source`: p95 under 250 ms before async downstream processing.
- `POST /chat/proxy` and `POST /chat/:agentId`: track gateway overhead separately from provider/model latency.
- Error rate target: under 1% for stable local/staging smoke journeys.

### OpenClaw

- `GET /v1/health`: p95 under 100 ms local/staging.
- `POST /v1/dispatch execute=false`: p95 under 500 ms when Stage A keyword fast-path applies.
- `POST /v1/dispatch execute=true`: measure queue-to-complete duration separately from HTTP acknowledgement.
- Run polling: bounded response size and stable status transitions.

### Agent execution

- Explicit timeout budget per agent task.
- Queue time, model time, workspace write time, and total duration tracked separately.
- No unbounded waits in API request/response path.

## Current performance risks

- `server.js` is a large 1109-line route hub; route-level bottlenecks will be harder to isolate without structured route tests.
- `orchestrator.js` is a 925-line model/RAG/provider router; provider latency, fallback behavior, Qdrant retrieval, and APISIX metering need separate timing.
- No tracked benchmark harness currently exists.
- No formal SLO dashboard is documented beyond Prometheus metrics endpoint.
- Chat/model endpoints need careful benchmarking so NewFire does not blame model latency for backend overhead or vice versa.

## Scorecard dimensions

Each service/feature is scored from 0-100 across:

- Functional completeness
- Test evidence
- Security posture
- Performance posture
- Observability/operability
- Deployment/rollback clarity
- Business-flow completeness

## Service readiness snapshot

### newfire-backend — 54/100

Strengths:

- Now tracked in GitHub after PR #9 merge.
- Clear Express/Postgres service baseline.
- Health and metrics endpoints exist.
- Auth, tenant, billing, webhooks, RAG/model routing, and agent endpoints are visible in source.

Blockers:

- No package test script.
- Tenant/RBAC integration tests still pending.
- Dependency audit shows 4 high and 7 moderate vulnerabilities.
- CORS/security-header/rate-limit hardening not yet implemented.
- Benchmark harness missing.

Next PRs:

- Tenant/RBAC tests.
- Dependency/security middleware hardening.
- Local/staging benchmark harness.

### openclaw — 58/100

Strengths:

- Clear FastAPI service layout and documented API.
- Cloudflare Access posture documented.
- Classifier PR exists in prior workstream.

Blockers:

- Current branch test discovery reported no collected tests.
- Agent execution/workspace path confinement tests required.
- Local benchmark and timeout/failure tests required.

Next PRs:

- Reconcile PR #7 merge/test state.
- Add/verify classifier and auth tests.
- Add workspace confinement and timeout tests.

### newfire_backend_docker — 62/100

Strengths:

- Compose file documents networks, environment, restart policy, and log rotation.
- Backend container path and exposed port are clear.

Blockers:

- Image tag/source drift exists in docs vs current backend baseline.
- Rollback procedure and config validation tests are not formalized.
- Secret presence validation is runtime-only, not CI-checked.

Next PRs:

- Add compose config validation.
- Document rollback tags and safe deploy checklist.

### infra — 50/100

Strengths:

- Infrastructure docs and artifacts exist.
- Cloudflare/APISIX/NewFire homelab context is documented.

Blockers:

- Ingress exposure assumptions need verification.
- No formal readiness checks for public/internal endpoint boundary.
- No automated drift detection.

Next PRs:

- Add ingress exposure checklist.
- Document metrics/admin endpoint network boundaries.

## Feature readiness snapshot

### Auth and user management — 55/100

Main blocker: rate limiting, invalid-token tests, and brute-force handling.

### Tenant/company/agent access — 45/100

Main blocker: cross-tenant denial tests and role checks across all routes.

### Chat/model routing/RAG — 50/100

Main blocker: provider fallback tests, Qdrant isolation tests, and performance timing.

### Webhooks — 50/100

Main blocker: signature/replay/idempotency tests.

### Agent delegation/OpenHands/OpenClaw — 45/100

Main blocker: sandbox/token/role boundary tests and timeout behavior.

### Billing/tiers — 55/100

Main blocker: checkout/portal/webhook E2E tests and tenant ownership assertions.

## How the CEO should read these scores

These scores are not a claim that the platform is broken. They are a governance baseline. A service can be functional while still scoring below production-ready because it lacks tests, hardening, benchmarks, or rollback evidence. The goal is to raise each critical surface above 80/100 through small PRs with proof.
