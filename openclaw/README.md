# OpenClaw v1

Junior-dev coordinator service for the NewFire homelab. Sits in front of OpenHands, OpenCode, and the llama.cpp router. Answers three questions for every developer brief: where do I start, which tool do I use, and now also runs the work end to end and writes the resulting files.

Public URL: `https://claw.newfire.app` (gated by Cloudflare Access).

## Three PRs in this directory

| PR | What it does |
|---|---|
| PR 1 | FastAPI skeleton, CF Access JWT, Postgres `openclaw` schema, Stage A keyword + Stage B classifier stub, `/v1/whoami`, `/v1/dispatch` (suggest mode). |
| PR 2 | Adds `execute=true` on dispatch, background task, `runs` table, `/v1/runs[/{id}]`, single-page UI at `/`. Inference via the llama.cpp router on ghana. |
| PR 3 | Captures `finish_reason` (warns when truncated). Materializes a per-run workspace on CephFS at `/mnt/cephfs-mgmt/openclaw-workspaces/run-{id}/`. Parses fenced code blocks from the LLM output and writes them as real files with filename inference (markdown header, first-line comment, or fallback). README.md added in each workspace with the prompt and prose. |

## Layout

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI entrypoint, mounts static UI and API routes. |
| `app/auth.py` | Cloudflare Access JWT verification (JWKS cached 1h) plus dev bypass. |
| `app/classifier.py` | Two-stage dispatch classifier. |
| `app/tools/llm.py` | Inference backend; routes to llama.cpp router on ghana over Tailscale. |
| `app/tools/codeblocks.py` | Parse fenced code blocks, infer filenames, write to workspace. |
| `app/routes/` | `health`, `whoami`, `dispatch`, `runs`. |
| `app/static/index.html` | Single-page UI: brief textarea, classify and run, file viewer, history. |
| `migrations/001_openclaw_schema.sql` | Tables: developers, projects, dispatches, usage. |
| `migrations/002_runs.sql` | Runs table for executor mode. |
| `migrations/003_workspaces.sql` | Adds workspace_path, files_written, finish_reason, truncated columns. |
| `tests/dispatch_cases.json` | 5-case acceptance suite for the classifier. |
| `Dockerfile`, `docker-compose.yml` | Container on Minisforum, `newfire_shared` network, CephFS bind mount. |
| `deploy.sh` | One-shot deploy: pulls DB password from existing newfire-backend env on the host. |
| `spec.md` | Full v1 specification. |

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Single-page UI |
| GET | `/v1/health` | Service + DB liveness (no auth) |
| GET | `/v1/whoami` | Authenticated email plus first/last seen |
| POST | `/v1/dispatch` | Body `{prompt, execute, max_tokens}`. Classify; optionally execute. |
| GET | `/v1/runs/{id}` | Status, output, files_written, tokens, duration, finish_reason. |
| GET | `/v1/runs` | Caller's recent 25 runs. |

## How execute mode works (PR 3)

1. Brief classified by Stage A keyword and Stage B stub.
2. `runs` row created with status `pending` and workspace path `/workspaces/run-{id}`.
3. Background task picks the model: openhands -> qwen3-coder-30b, opencode -> qwen-coder-7b, direct -> gemma3-4b.
4. LLM is called via the homelab llama router; response captured along with `finish_reason` (so truncation surfaces).
5. Output is parsed for fenced code blocks. Filenames are inferred from markdown headers above the fence (`## name.ext` or `filename: name.ext`), from a comment on the first line of the block, or by fallback `file{N}.{ext}`.
6. README.md is written to the workspace containing the brief and the prose between blocks.
7. Files are written to the workspace; metadata is persisted in `runs.files_written` (jsonb).
8. UI polls `/v1/runs/{id}` every 1.2s and renders the file list, sizes, and the workspace path.

Workspaces survive on CephFS at `/mnt/cephfs-mgmt/openclaw-workspaces/run-{id}/`.

## Local development

```bash
cp .env-secrets.example .env-secrets
# edit DB_PASSWORD and (dev only) OPENCLAW_DEV_EMAIL=you@example.com
docker compose up --build
open http://127.0.0.1:5500/
```

Startup refuses to boot if neither `OPENCLAW_DEV_EMAIL` nor `CF_ACCESS_AUD` is set.

## Security posture

- Public URL gated by Cloudflare Access policy (out-of-band Zero Trust dashboard).
- Service refuses unauthenticated requests on every protected route.
- Postgres reached only via internal docker network.
- No secrets in the image. `.env-secrets` written at deploy time, mode 0600.

Spec: `spec.md`.
