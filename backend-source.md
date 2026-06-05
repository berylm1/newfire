# Backend Source Map

Where every piece of the NewFire platform lives on disk and where the deployed copy runs. Use this as the lookup table whenever you ask where the source for X is.

## At a glance

| Project | Local source (Mac) | Deployment artifacts | Container on host |
|---|---|---|---|
| NewFire backend | `/Users/oluwajobamalomo/newfire-backend/` | `/home/newwaveclaw/newfire-backend-docker/docker-compose.yml` on america | `newfire-backend` on `newfire_shared`, host `127.0.0.1:3200` |
| NewFire frontend | `/Users/oluwajobamalomo/newfire-app/` | built and shipped as `newfire-app` container | `newfire-app` nginx on `:4000` |
| NSS control plane | `/Users/oluwajobamalomo/newfire-nss-control/` | `/home/newwaveclaw/newfire-nss-control/` on america | `nss-control` on `:3300` |
| NSS runner | `/Users/oluwajobamalomo/newfire-nss-runner/` | mirror on ghana | `nss-runner` on Tailscale `100.88.112.5:3301` |
| NSS dev portal | `/Users/oluwajobamalomo/newfire-nss-portal/` | on america | `nss-portal` on `:4001` |
| NSS router | `/Users/oluwajobamalomo/newfire-nss-router/` | on ghana | `nss-router` on `:4500` |
| MCP server scaffold | `/Users/oluwajobamalomo/newfire-mcp/` | not deployed | scaffold only |
| Client SDK scaffold | `/Users/oluwajobamalomo/newfire-sdk/` | not published | scaffold only |
| Homelab docs and infra | `/Users/oluwajobamalomo/newfire-infra/` | this repo | n/a |

## NewFire backend (the load-bearing one)

- **Stack**: Express + Postgres, JWT auth, smart routing via OpenClaw, per-tenant Qdrant collections, HMAC webhooks, Stripe billing.
- **Source**: `newfire-backend/` in this GitHub repo; production worker mirror is `/home/newwaveclaw/newfire-backend/` on america. The baseline was imported from local commit `16b1571 chore: baseline NewFire backend source`.
- **Key files**:
  - `src/server.js` Express entry, route registration, startup log
  - `src/auth.js` JWT login, signup, refresh, middleware
  - `src/db.js` pg pool, requires `DB_PASSWORD` env, fails fast if missing
  - `src/orchestrator.js` smart routing across Ollama, OpenRouter, OpenClaw with health probes, fallback chain, Qdrant retrieve with `company_id` payload filter
  - `src/tenant.js` `tenantContext` middleware plus in-memory cache, invalidation hooks
  - `src/webhooks.js` HMAC-SHA256 inbound webhooks, SSE stream, outbound `emitExternalEvent` with retry
  - `src/paperclip.js` per-tenant company and agent provisioning, OpenClaw / OpenCode / OpenHands wiring, `delegateCodingTask`
  - `src/metrics.js` prom-client default and custom histograms (`http_requests_total`, `chat_request_duration_seconds`)
  - `migrations/` ordered SQL migrations (Stripe, tenant column, agent_tasks, webhooks_inbox, n8n columns, and so on)
- **Latest container tag in production** as of 2026-04-25: `newfire-backend:1.18.2-provisioner`. Newer tags may have shipped since.
- **Reachable internally**: `http://newfire-backend:3200` on the `newfire_shared` Docker network
- **Public path**: `https://newfire.app/backend/*`. Proxy chain is Cloudflare edge to `newfire-app` nginx to the backend container.
- **Health**: `GET /backend/health` returns 200 when up.

## NewFire frontend

- **Stack**: React 19 + Vite + Tailwind + react-router-dom
- **Source**: `/Users/oluwajobamalomo/newfire-app/`
- **Pages**: Landing, Login, Dashboard, Chat, DevPortal, DevDashboard, Onboarding, AdminDashboard, plus `/team-dashboard` (iframes Paperclip) and `/agent-tasks` (delegated coding task tracker)
- **Build output**: served by the `newfire-app` container nginx on america at `:4000`, plus Cloudflare edge.
- **SPA calls**: relative `/backend/*` which the nginx proxies to the backend container.

## NSS pieces (sandbox service)

- `newfire-nss-control` is the Express + Postgres + JWT control plane on Minisforum. Owns `nss_*` tables in newfire-db, mints invites, issues JWTs, creates and destroys sandbox rows.
- `newfire-nss-runner` is the Node + dockerode + zod runner on DGX Spark. Owns the Docker socket and the NVIDIA toolkit. Spawns sandbox containers off `nss/sandbox:ubuntu-22.04-cuda12`.
- `newfire-nss-portal` is the React SPA at `dev.newfire.app` for sandbox management.
- `newfire-nss-router` is the FastAPI classifier on ghana `:4500` that rewrites `model: nss-auto` to the right backend (coder, thinker, general, tools, vision, fast) before forwarding to LiteLLM.

## Scaffolds not yet deployed

- **MCP server** (`newfire-mcp/`): JSON-RPC 2.0 over POST `/rpc`, tools `qdrant_search`, `db_query` (SELECT-only with allowlist), `health`. Bearer auth via `MCP_AUTH_TOKEN`. Dockerfile ready. Intended to run on ghana next to Qdrant.
- **Client SDK** (`newfire-sdk/`): ESM-only `@newfire/sdk` v0.1.0. Auth, company, agents, chat, onboarding, admin stats, plus `subscribeWebhooks`. Browser localStorage and Node in-memory storage. README + `examples/browser.html` included.

## Homelab docs and infra repo (this repo)

- **Path**: `/Users/oluwajobamalomo/newfire-infra/`
- **Remote**: `https://github.com/berylm1/newfire`
- **Branch**: `main`
- **What lives here**:
  - Top-level numbered docs (`00_OVERVIEW.md` through `08_CHECKLIST.md`)
  - `blueprint/` synthesis of the 3-video AI Operating System framework
  - `progress/` long-form progress notes
  - `scripts/` ad-hoc operator scripts
  - `infra/` deployment artifacts for codeep, dev-hub, cloudflared
  - This file (`backend-source.md`)

## Git status caveats

- `newfire-backend` is now staged for GitHub PR control under `newfire-backend/` in this repo. Do not edit the production worker mirror directly for governed implementation work; create a branch/PR here first, then deploy separately after review.
- `newfire-app` was `git init` initialized on 2026-04-21 but had no remote configured at that time. Verify with `git remote -v` in that dir; if still no remote, plan a push to `berylm1` or a sibling repo before it grows further.
- `newfire-nss-control`, `newfire-nss-runner`, `newfire-nss-portal`, `newfire-mcp`, and `newfire-sdk` each have their own local git repos. Remote status is unknown without checking each.
- `newfire-infra` (this repo) is the only one confirmed to have a working remote and push history.

## Where to add a new project

If you start a new piece of the platform:

1. Create the local source dir under `/Users/oluwajobamalomo/<name>/`
2. Add a row to the table at the top of this file
3. If it deploys to a host, document the build dir on that host and the container name
4. If it has its own GitHub remote, link it here
5. Commit and push this file so the source map stays the single source of truth
