# OpenClaw v1

Junior-dev coordinator service for the NewFire homelab. Sits in front of OpenHands, OpenCode, and the llama.cpp router. Answers three questions for every developer brief: where do I start, which tool do I use, and now also runs the work end to end.

Public URL: `https://claw.newfire.app` (gated by Cloudflare Access).

## What ships in this directory

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI entrypoint, mounts static UI and API routes. |
| `app/auth.py` | Cloudflare Access JWT verification (JWKS cached 1h) plus dev bypass for local testing. |
| `app/classifier.py` | Two-stage dispatch classifier (keyword fast-path, LLM stub). |
| `app/tools/llm.py` | Inference backend; routes to llama.cpp router on ghana over Tailscale. |
| `app/routes/` | `health`, `whoami`, `dispatch`, `runs`. |
| `app/static/index.html` | Single-page UI: brief textarea, classify and run buttons, live status, recent runs table. |
| `migrations/001_openclaw_schema.sql` | Tables: developers, projects, dispatches, usage. |
| `migrations/002_runs.sql` | Runs table for executor mode. |
| `tests/dispatch_cases.json` | 5-case acceptance suite for the classifier. |
| `Dockerfile`, `docker-compose.yml` | Containerized on Minisforum, joins `newfire_shared` network. |
| `deploy.sh` | One-shot deploy script. Pulls DB password from existing newfire-backend env on the host. |
| `spec.md` | Full v1 specification. |

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Single-page UI |
| GET | `/v1/health` | Service + DB liveness (no auth) |
| GET | `/v1/whoami` | Authenticated email plus first/last seen |
| POST | `/v1/dispatch` | Classify; optionally execute (when `execute=true`). |
| GET | `/v1/runs/{id}` | Run status, output, tokens, duration. |
| GET | `/v1/runs` | Caller's recent 25 runs. |

## How execute mode works

When `execute=true` on a dispatch:
1. Brief goes through Stage A keyword + Stage B classifier.
2. A `runs` row is created with status `pending`.
3. A background task picks a model based on the classified tool:
   - `openhands` -> `qwen3-coder-30b` on the llama router
   - `opencode` -> `qwen-coder-7b`
   - `direct` -> `gemma3-4b`
4. The LLM responds; we record output, tokens, and duration.
5. Client polls `/v1/runs/{id}` (the UI does this every 1.2s) until status is terminal.

PR 3 will swap the LLM-only executor for a real OpenCode workspace runner and OpenHands shim caller, so the executor will actually write files and run code instead of just generating text.

## Local development

```bash
# 1. fill .env-secrets with DB_PASSWORD and (for dev only) OPENCLAW_DEV_EMAIL
cp .env-secrets.example .env-secrets
# edit DB_PASSWORD and set OPENCLAW_DEV_EMAIL=you@example.com

# 2. start
docker compose up --build

# 3. hit the UI
open http://127.0.0.1:5500/
```

Startup refuses to boot if neither `OPENCLAW_DEV_EMAIL` nor `CF_ACCESS_AUD` is set; this prevents accidentally shipping a wide-open service.

## Security posture (current)

- Public URL gated by Cloudflare Access policy (out-of-band Zero Trust dashboard).
- Service refuses unauthenticated requests on every protected route.
- Postgres reached only via internal docker network.
- No secrets in the image. `.env-secrets` written at deploy time, mode 0600.

Spec: `spec.md`.
