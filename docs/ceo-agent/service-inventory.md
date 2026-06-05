# Service Inventory

Generated from the first CEO readiness pass. Source scanner: `scripts/ceo_readiness_audit.py`.

## Service surfaces

### newfire-backend

- Path: `newfire-backend/`
- Runtime: Node.js, Express, Postgres
- Main entrypoints:
  - `src/server.js`
  - `src/auth.js`
  - `src/orchestrator.js`
  - `src/tenant.js`
  - `src/webhooks.js`
  - `src/dev.js`
  - `src/paperclip.js`
- Health: `GET /health`
- Deployment artifact: `newfire_backend_docker/docker-compose.yml`
- Risk level: high
- Why high: owns auth, tenancy, billing, webhooks, model/provider routing, Qdrant/RAG access, CEO chat, and agent task delegation.

### openclaw

- Path: `openclaw/`
- Runtime: Python, FastAPI, Postgres
- Main entrypoints:
  - `app/main.py`
  - `app/auth.py`
  - `app/classifier.py`
  - `app/routes/`
- Health: `GET /v1/health`
- Deployment: `openclaw/docker-compose.yml`, public URL gated by Cloudflare Access
- Risk level: high
- Why high: developer-agent routing and execution surface.

### newfire_backend_docker

- Path: `newfire_backend_docker/`
- Runtime: Docker Compose deployment artifact
- Main files:
  - `docker-compose.yml`
  - `Dockerfile`
- Risk level: medium
- Why medium: controls production runtime wiring, environment injection, networks, and image/source path relationship.

### infra

- Path: `infra/`
- Runtime: Cloudflare/codeep/dev-hub deployment artifacts and docs
- Risk level: medium
- Why medium: documents ingress and operator control-plane assumptions.

## Repository size snapshot

- Markdown: 42 files, 11055 lines
- JSON: 15 files, 3572 lines
- JavaScript: 11 files, 3367 lines
- Python: 17 files, 1312 lines
- Shell: 10 files, 786 lines
- SQL: 13 files, 734 lines
- YAML: 4 files, 249 lines

## Backend route inventory

Detected 45 route registrations in `newfire-backend/src`.

Public or unauthenticated by design / to verify:

- `GET /health`
- `GET /metrics` — documented as internal Docker-only; must verify not externally exposed.
- `POST /auth/signup`
- `POST /auth/login`
- `POST /webhooks/stripe`
- `POST /contact/enterprise`
- `POST /demo/chat`
- `POST /onboarding/chat`
- `POST /onboarding/activate`

Authenticated/user/business routes:

- `GET /auth/me`
- `GET /company`
- `GET /company/usage`
- `POST /company/create`
- `GET /agents`
- `PUT /agents/:agentId`
- `DELETE /agents/:agentId`
- `POST /chat/proxy`
- `POST /chat/:agentId`
- `GET /chat/:agentId/history`
- `GET /tiers`
- `POST /billing/checkout`
- `POST /billing/portal`
- `POST /agent/delegate`
- `GET /agent/tasks`
- `GET /agent/tasks/:id`
- `POST /agent/tasks/:id/feedback`
- `POST /ceo/chat`
- `GET /ceo/history`
- `POST /ceo/reset`

Admin/developer-sensitive routes:

- `GET /admin/stats`
- `GET /admin/crm`
- `POST /admin/crm/note`
- `GET /admin/roi`
- `GET /admin/metrics`
- `POST /admin/regenerate-prompts`
- `POST /admin/set-role`
- `POST /admin/users`
- `DELETE /admin/users/:id`
- `POST /dev/openhands`
- `GET /dev/openhands/sessions`
- `GET /dev/openhands/sessions/:id`

Webhook/SSE routes:

- `POST /webhooks/:source`
- `GET /webhooks/stream`

## Environment dependency snapshot

The backend references 46 environment variables. Critical classes:

- Database: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- Auth/secrets: `JWT_SECRET`, `WEBHOOK_SECRET`, `STRIPE_WEBHOOK_SECRET`, `N8N_HOOK_SECRET`
- Billing: `STRIPE_SECRET_KEY`, `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_PRO`
- Model/RAG: `OPENROUTER_KEY`, `OLLAMA_URL`, `QDRANT_URL`, `QDRANT_API_KEY`, `EMBED_MODEL`, `RAG_TOP_K`
- Agent execution: `OPENCLAW_URL`, `OPENCLAW_TOKEN`, `PAPERCLIP_*`, `OPENHANDS_SHIM_*`
- Metering/rate limiting: `APISIX_ADMIN_URL`, `APISIX_ADMIN_KEY`, `CLIENT_RATE_LIMIT_RPS`, `CLIENT_RATE_LIMIT_BURST`, `CLIENT_DAILY_QUOTA`

## Inventory gaps

- Frontend source is still not tracked in this repo based on current source map history.
- Runtime exposure of `/metrics` must be verified at ingress/proxy level.
- Current backend has no formal test script in `package.json`.
- Current branch did not collect OpenClaw tests locally; reconcile with PR #7 merge state.
