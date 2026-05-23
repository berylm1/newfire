# OpenClaw v1 — Specification

**Date drafted:** 2026-05-18
**Target ship:** Phase 1 within 24h of build start; full v1 within 3-5 days
**Authors:** chisoba.9090@gmail.com plus Claude pairing notes

---

## 1. What OpenClaw is

A single coordinator service that sits in front of OpenHands and OpenCode, so a developer never has to choose. OpenClaw answers three questions:

1. **Where do I start?** Project templates create a scaffold on CephFS.
2. **Which tool do I use?** Smart dispatch picks OpenHands or OpenCode based on prompt intent, then opens the right one with the right workspace.
3. **What did we use?** Per-developer usage telemetry surfaces CEO-ready numbers.

Non-goals for v1: replacing OpenHands or OpenCode, building a new IDE, multi-tenant SaaS billing, self-hosted SSO. Anything beyond the three questions above ships in a later phase.

## 2. Architecture

```
                         claw.newfire.app                                
                                │                                       
                          (CF Access gate)                              
                                │                                       
                          ┌─────▼─────┐                                 
                          │ OpenClaw  │   FastAPI, container :5500      
                          │   v1      │   Minisforum                    
                          └─────┬─────┘                                 
            ┌─────────────┬─────┴──────┬───────────────┐                
            │             │            │               │                
            ▼             ▼            ▼               ▼                
   ┌──────────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────┐        
   │  OpenHands   │ │ OpenCode │ │  Template  │ │  newfire-db  │        
   │  (admin OH   │ │ (port    │ │  cloner    │ │  (projects + │        
   │   plus NSS   │ │  3030)   │ │  /opt/     │ │   usage      │        
   │  sandboxes)  │ │          │ │ openclaw/  │ │   tables)    │        
   └──────────────┘ └──────────┘ │ templates  │ └──────────────┘        
                                 └────────────┘                         
                                                                        
   LiteLLM at 100.88.112.5:4500 fans out to vLLM, Ollama, cloud routes  
   (unchanged). OpenClaw reads LiteLLM usage callbacks to populate the  
   usage table.                                                         
```

## 3. Identity model

- CF Access policy on `claw.newfire.app` validates email (one-time PIN flow).
- Cloudflare injects `Cf-Access-Jwt-Assertion` header on every authenticated request.
- OpenClaw verifies the JWT against Cloudflare's JWKS endpoint, extracts `email`, treats it as the canonical developer ID.
- A `developers` row is upserted in `newfire-db` on first login. No password, no separate session store.

## 4. Database schema (new schema `openclaw` in existing `newfire-db`)

```sql
create schema if not exists openclaw;

create table openclaw.developers (
  email          text primary key,
  display_name   text,
  first_seen_at  timestamptz not null default now(),
  last_seen_at   timestamptz not null default now()
);

create table openclaw.projects (
  id           bigserial primary key,
  owner_email  text not null references openclaw.developers(email),
  name         text not null,
  template     text not null,
  cephfs_path  text not null,             -- /mnt/cephfs-mgmt/projects/<owner>/<name>
  created_at   timestamptz not null default now(),
  destroyed_at timestamptz,
  unique (owner_email, name)
);

create table openclaw.dispatches (
  id             bigserial primary key,
  owner_email    text not null,
  project_id     bigint references openclaw.projects(id),
  prompt_snippet text not null,           -- first 200 chars only, privacy
  picked_tool    text not null check (picked_tool in ('openhands','opencode','direct')),
  picked_reason  text not null,           -- classifier output
  override_tool  text,                    -- if user overrode
  created_at     timestamptz not null default now()
);

create table openclaw.usage (
  id                bigserial primary key,
  owner_email       text not null,
  project_id        bigint,
  tool              text not null,
  model             text not null,
  prompt_tokens     int  not null,
  completion_tokens int  not null,
  latency_ms        int  not null,
  ts                timestamptz not null default now()
);

create index on openclaw.usage (owner_email, ts);
create index on openclaw.usage (model, ts);
create index on openclaw.dispatches (owner_email, created_at);
```

## 5. API surface (v1, public via `claw.newfire.app`)

| Method + path | What it does |
|---|---|
| `GET /v1/whoami` | Echo authenticated email plus first/last seen |
| `POST /v1/dispatch` | Body: `{prompt, project_id?}`. Returns `{suggested_tool, suggested_url, alternatives[], reason, dispatch_id}` |
| `POST /v1/dispatch/:id/override` | Body: `{picked_tool}`. Records the user override for classifier training |
| `GET /v1/templates` | List of available templates plus blurb |
| `POST /v1/projects` | Body: `{template, name}`. Creates project on CephFS plus DB row. Returns `{project_id, cephfs_path, open_in_openhands_url, open_in_opencode_url}` |
| `GET /v1/projects` | List caller's projects |
| `DELETE /v1/projects/:id` | Tombstone in DB, queue cleanup of cephfs path |
| `GET /v1/usage/me` | Caller's last 30 days of usage |
| `GET /v1/usage/team` | Aggregate counts across all devs, admin-only |
| `GET /v1/dashboards/grafana` | Redirect to the Grafana board scoped to caller |

## 6. Dispatch classifier

Stage A is keyword fast-path, Stage B is LLM classifier. Order matters because Stage A returns in <1ms; we hit Stage B only when Stage A is ambiguous.

**Stage A — keyword fast-path** (zero-cost, deterministic)
- Contains "build", "implement end-to-end", "ship me", "autonomously", "no questions" → `openhands`
- Contains "edit this file", "open", "look at line", "what does X do" → `opencode`
- Contains "?" only, no imperative verb → `opencode`
- Otherwise → fall to Stage B

**Stage B — LLM classifier** (LiteLLM `nss-tools-light`, ~300ms)
- System: "Classify the developer's intent. Reply with one of: openhands, opencode, direct. Pick openhands when the user wants the system to autonomously build or modify multiple files. Pick opencode for interactive code editing or single-file inspection. Pick direct for a one-off Q&A that doesn't need either tool."
- User: the prompt
- Temperature 0, max_tokens 5

Result stored in `dispatches.picked_reason`. If user overrides, `override_tool` populated. Over time we mine the discrepancies to tune Stage A.

## 7. Template system

Templates live at `/opt/openclaw/templates/<name>/` on Minisforum, each one a regular Git repo with a `.openclaw.yaml` manifest:

```yaml
name: fastapi-service
description: FastAPI service with Pydantic models, Dockerfile, and pytest
language: python
post_clone:
  - "python3 -m venv .venv"
  - "echo 'Run: source .venv/bin/activate && pip install -r requirements.txt'"
```

Five v1 templates:
1. `nextjs-app` — Next.js 15 + Tailwind 4 + Prisma stub
2. `fastapi-service` — FastAPI + Pydantic + pytest + Dockerfile
3. `go-microservice` — Go + chi + Dockerfile + Makefile
4. `django-app` — Django + Postgres adapter + docker-compose
5. `python-data` — Pandas + DuckDB + Jupyter notebook starter

Cloning is a shell action triggered by OpenClaw:
```
git clone --depth=1 /opt/openclaw/templates/<name>.git \
  /mnt/cephfs-mgmt/projects/<email>/<project-name>
```

## 8. Telemetry pipeline

LiteLLM has a callback hook (`success_callback`) that can POST to an HTTP endpoint per request. OpenClaw exposes `POST /v1/telemetry/litellm` that accepts the standard LiteLLM event payload and writes one `openclaw.usage` row.

Setup steps:
- Add `callbacks: ["openclaw_telemetry.OpenclawTelemetry"]` to LiteLLM config on DGX
- The callback class POSTs to `http://100.79.80.119:5500/v1/telemetry/litellm` with a shared secret in `X-Openclaw-Secret`
- OpenClaw verifies the secret, parses event, writes row

Grafana boards (4 panels in v1):
1. Tokens per dev, last 7 days (stacked bar)
2. Active devs last 24h, 7d, 30d (single-stat)
3. Tool split, OH vs OpenCode vs direct (donut)
4. Latency p50/p95 by model (time series)

## 9. Phase plan with acceptance criteria

### Phase 1 — Smart dispatch (Day 1–2)
- FastAPI service on :5500, dockerized, systemd unit
- CF JWT verification middleware
- `developers` table populated on first auth
- `/v1/dispatch` working end-to-end with both stages
- `claw.newfire.app` routes via cloudflared, gated by CF Access (allowlist matches OpenCode policy)
- Health endpoint, OpenAPI docs at `/docs`

**Acceptance:** 5 hand-crafted prompts dispatch correctly per [test suite in `/opt/openclaw/tests/dispatch_cases.json`]. Two of the five must hit Stage A only, three of five must hit Stage B and return in under 500 ms.

### Phase 2 — Project templates (Day 2–3)
- Templates repo at `/opt/openclaw/templates/` with the five v1 starters
- `/v1/projects` POST creates DB row, clones template, returns `open_in_*` URLs
- `/v1/projects` GET lists caller's projects
- `DELETE` tombstones the project row and queues cephfs cleanup (similar to NSS destroy hook)
- Dispatch in Phase 1 accepts optional `project_id` and surfaces the right workspace URL

**Acceptance:** create one project per template, verify cephfs layout, open in both OH and OpenCode, confirm bind mount picks up the right path.

### Phase 3 — Usage telemetry plus dashboard (Day 3–5)
- LiteLLM custom callback class (`openclaw_telemetry.py`), deployed on DGX
- OpenClaw `/v1/telemetry/litellm` ingest endpoint with HMAC verification
- `usage` table fills with one row per LiteLLM completion
- Grafana datasource pointed at `openclaw` schema
- Four panels listed in section 8

**Acceptance:** dashboard reflects the last 7 days of LiteLLM activity within 60 s of the call. CSV export endpoint returns 30 days of data for the CEO digest.

## 10. Rollback per phase

| Phase | Rollback |
|---|---|
| 1 | `systemctl stop openclaw`, remove the cloudflared ingress entry, restore from `/etc/cloudflared/config.yml.bak.*`. Postgres schema is additive and harmless to leave in place. |
| 2 | Disable the `/v1/projects` route via env flag, projects table stays untouched. Templates dir is read-only, no cleanup needed. |
| 3 | Remove the LiteLLM `callbacks:` line on DGX, restart LiteLLM. OpenClaw `/v1/telemetry/litellm` still accepts but receives nothing. |

## 11. Open questions for tomorrow's build

1. **Stage A keyword list** is a first pass; expect to tune by Day 3. Should we instrument the override route to feed back into the keyword list automatically, or keep human review in the loop?
2. **Project cleanup** when a developer destroys a project: rm -rf the cephfs subpath synchronously, or queue a cephfs reaper job similar to NSS?
3. **Per-project CephFS quotas** — should we set a 5 GiB ceiling per project to prevent abuse, or trust developers in this small team?
4. **Authentication during local development** of OpenClaw itself — we won't have CF headers when curling from the host. Add a dev-only `OPENCLAW_DEV_EMAIL` env override that bypasses JWT verification?
5. **Cost model**: vLLM is free per token, Ollama is free, cloud routes cost real money. Should `usage` separate "free vs metered" and roll up only the metered ones for the CEO digest?

## 12. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Stage B classifier mis-routes a frustrated user | Medium | Low | Override route surfaces the issue; classifier output stored for tuning |
| LiteLLM callback misses events (network blip) | Low | Medium | OpenClaw also exposes a backfill endpoint that reads LiteLLM's internal log file |
| CephFS storage runs out | Low | High | Per-project quota in question (3); reaper job for destroyed projects |
| CF JWT signing key rotation | Low | Low | Cache JWKS for 1 hour, retry on signature failure with fresh fetch |
| OpenHands or OpenCode goes down | Medium | Medium | Dispatch returns a clear error plus the alternative tool URL |

## 13. Tech stack pinned

- Python 3.12, FastAPI, uvicorn, asyncpg, httpx, PyJWT, cryptography
- Postgres reuses `newfire-db` at `host.docker.internal:5432`
- Docker image FROM `python:3.12-slim`
- Service runs as UID 1000 (no root)
- Single container on Minisforum, host network, systemd-managed (same pattern as OpenCode)
- Hostname `claw.newfire.app`, port 5500, CF Access policy with same allowlist as `opencode.newfire.app`

## 14. Resume points

When tomorrow's session starts, the build order is:

1. Skeleton FastAPI + Dockerfile + systemd unit + cloudflared ingress edit
2. CF JWT middleware (test with curl + a hand-signed test JWT first)
3. `developers` upsert on whoami
4. Stage A keyword classifier
5. Stage B LLM classifier (LiteLLM call)
6. `/v1/dispatch` route end-to-end
7. Phase 1 acceptance test
8. … phase 2 and 3 per section 9
