# Testing and Resilience Matrix

Purpose: convert the CEO directive into a concrete QA, regression, integration, load, and chaos test roadmap.

## Verification completed in this pass

- Backend syntax check: `node --check newfire-backend/src/*.js` passed.
- Backend dependency audit: `npm audit --package-lock-only --audit-level=moderate --json` found 11 vulnerabilities.
- OpenClaw test command attempted in a temporary venv; current branch reported no collected tests under `openclaw/tests`.

## Current testing gaps

### Backend

Current evidence:

- `newfire-backend/package.json` has only `dev` and `start` scripts.
- No test script is defined.
- No backend integration test harness is present in the tracked baseline.

Required tests:

- Auth: signup/login/me, invalid token, expired token, missing token, bad credentials, repeated failures.
- Tenant/RBAC: signup, company creation, agent creation/update/delete, chat history, task feedback, cross-tenant denial.
- Admin/dev: non-admin denial, developer role requirement, admin-only operations.
- Webhooks: valid signature, invalid signature, replay/idempotency, malformed JSON, downstream retry.
- Billing: checkout/portal requires tenant ownership and valid tier.
- RAG/Qdrant: per-company collection isolation and empty-result fallback.
- Metrics: `/metrics` internal-only exposure and metric labels do not leak secrets.

### OpenClaw

Current evidence:

- README documents FastAPI routes, Cloudflare Access, dispatch, runs, and workspace writing.
- Local test discovery did not collect tests from current branch in this checkout.

Required tests:

- Classifier acceptance cases.
- Auth required for protected routes.
- Dev bypass disabled unless explicitly configured.
- Dispatch execute=false suggest path.
- Execute=true run lifecycle.
- Workspace path confinement and codeblock filename sanitization.
- LLM timeout/truncation behavior.

### Docker/deployment

Required tests:

- Compose config validates without expanding real secrets.
- Backend container exposes only intended port/network.
- Log rotation exists and works.
- Health endpoint fails fast when DB/JWT secrets missing.
- Rollback image tag is documented.

## E2E flow priorities

1. New user signup -> company creation -> agents visible -> chat works -> usage increments.
2. Tenant A cannot access Tenant B company, agents, chat history, tasks, or Qdrant collection.
3. Developer creates OpenHands session -> session appears -> result/failure is visible only to owner/admin.
4. Stripe checkout/webhook updates plan state exactly once.
5. Webhook receiver accepts signed event and rejects invalid/replayed events.

## Regression strategy

Every CEO-agent bug fix should add a regression test before or with the fix. The initial regression suite should start with:

- OpenClaw classifier routing from PR #7.
- Tenant/RBAC issue #3.
- RAG/memory issue #4 after design approval.
- APISIX metering/rate-limit issue #6.

## Load testing plan

Safe default: local/staging only unless explicitly approved.

Tools to add later:

- `autocannon` for Node HTTP route microbenchmarks.
- `k6` for E2E API journey tests.
- `pytest`/`httpx` for OpenClaw API integration tests.

Initial load scenarios:

- `/health` steady state.
- `/auth/login` with known test user in staging.
- `/chat/proxy` with provider mocked or stubbed.
- `/webhooks/:source` with valid signed synthetic events.
- `/dev/openhands` with shim mocked.

## Chaos/failure scenarios

Local/staging-only first:

- DB unavailable.
- Qdrant unavailable.
- OpenRouter unavailable.
- Ollama unavailable.
- OpenClaw unavailable.
- Stripe webhook duplicate delivery.
- Slow model provider timeout.
- Agent shim timeout.

Expected behavior:

- No secret leakage in error messages.
- Bounded timeout.
- Clear user-safe error.
- Retry only where idempotent.
- Metrics emitted for failure.

## First implementation PRs

1. #18 Backend test harness and tenant/RBAC integration tests.
2. #17 Auth/security middleware tests.
3. #19 Webhook security tests.
4. #20 Local/staging benchmark harness.
5. OpenClaw test discovery repair and classifier regression tests after PR #7 status is reconciled.
