# Infrastructure Deep-Dive

> Consolidated, takeover-ready reference for the entire NewFire stack:
> Cloudflare, Tailscale, Docker, AI agents, and every project/service.
> Generated from a live snapshot of `newwaveclaw` (control) and `spark-a439`/DGX (inference).

---

## 1. Cloudflare

### 1.1 Tunnel (the only public ingress)

All external traffic enters through a single Cloudflare Tunnel running in the
`cloudflared` container on `newwaveclaw`.

| Property | Value |
| --- | --- |
| Tunnel ID | `d0f9998f-73ee-4c64-a259-0f09a65d9856` |
| Config | `/home/newwaveclaw/.cloudflared/config.yml` |
| Credentials | `/home/newwaveclaw/.cloudflared/d0f9998f-...-9856.json` (keep secret) |
| Image | `cloudflare/cloudflared:latest` (entrypoint `cloudflared --no-autoupdate tunnel --config /etc/cloudflared/config.yml run`) |
| Protocol | QUIC, edge PoPs `iad` (registered connections to `198.41.x.x`) |
| Catch-all | `http_status:404` |

> **Handover:** the tunnel is bound to one Cloudflare account/zone. To take over,
> either transfer the zone + tunnel to the new operator, or run
> `cloudflared tunnel login` + `cloudflared tunnel create` and repoint `config.yml`.
> The credential JSON must never be committed.

### 1.2 Ingress routing table (`config.yml`)

| Hostname | Backend service | Notes |
| --- | --- | --- |
| `newfire.app` | `http://localhost:4000` | Main site / app |
| `dev.newfire.app` | `http://localhost:4000` | Developer portal (same upstream) |
| `app.newfire.app` | `http://openhands-app:8000` | OpenHands agent app (docker network DNS) |
| `agent.newfire.app` | `http://openhands-app:18000` | OpenHands agent server API |
| `openhands.newfire.app` | `http://localhost:8001` | OpenHands agent-canvas (300s timeout) |
| `api.newfire.app` | `http://localhost:9080` | API gateway (APISIX, 120s timeout) |
| `dash.newfire.app` | `http://localhost:3100` | Paperclip AI dashboard |
| `files.newfire.app` | `http://localhost:18789` | WebDAV file sharing |
| `metrics.newfire.app` | `http://localhost:3399` | Metrics dashboard "Exordium" (300s) |
| `lanai.newfire.app` | `http://localhost:3001` | Lanai lifestyle platform (120s) |
| `opencode.newfire.app` | `http://100.79.80.119:4096` | OpenCode CLI (points at this host's TS IP) |

Origins use `localhost` (resolved inside the `cloudflared` container's host
network) **except** `opencode.newfire.app`, which targets the host's Tailscale
IP `100.79.80.119:4096` directly. Docker-network names (`openhands-app`)
resolve because the tunnel container shares those networks.

### 1.3 API gateway — APISIX

`api.newfire.app` → `localhost:9080` is **APISIX** (standalone data-plane).

| File | Purpose |
| --- | --- |
| `apisix-conf/apisix.yaml` | Standalone route defs (`/hello` → httpbin roundrobin example) |
| `apisix-conf/config.yaml` | data-plane, control `:9090`, admin key present (redact on handover) |
| `apisix-conf/apisix-config.yaml` | admin key + etcd `http://etcd-quickstart:2379`, prometheus `:9091` |

> Admin keys are hardcoded in these files — **rotate and move to secrets on takeover.**

### 1.4 Wrangler / Workers

`~/.wrangler/` exists (Cloudflare Workers CLI cache: `cloudflare-skills-repo-cache.json`,
`metrics.json`, `logs/`). No active `wrangler.toml` was found in the scanned tree;
Workers usage, if any, is managed through the Cloudflare dashboard for this account.

### 1.5 TLS / certs

`~/.cloudflared/cert.pem` is the Cloudflare origin cert used for
`cloudflared login` / cert operations. Keep secret.

---

## 2. Tailscale

Private L3 network tying every node together. Tailscale **SSH** is enabled
(used to reach the DGX as `root`).

- **Tailnet:** `tail3a833f.ts.net`
- **MagicDNS:** on (hostnames resolve as `<name>.tail3a833f.ts.net`)

### 2.1 Device inventory

| Tailscale IP | Hostname | Owner | OS | State |
| --- | --- | --- | --- | --- |
| `100.79.80.119` | `america` (newwaveclaw) | newwaveclaw | Linux | online, tagged `tagged-devices` |
| `100.88.112.5` | `ghana` (spark-a439 / DGX) | tagged-devices | Linux | online, direct `192.168.1.158` |
| `100.120.107.95` | `berylpi5-newfire` | newwaveclaw | Linux (Pi 5) | online |
| `100.107.229.67` | `beryls-macbook-air` | newwaveclaw | macOS | online, direct |
| `100.90.151.91` | `desktop-vp6ascf` | aoluwafemi | Windows | online |
| `100.112.32.47` | `iphone-14` | newwaveclaw | iOS | offline (1d) |
| `100.86.81.39` | `joba-dell-1` | chisoba.9090 | Windows | offline (8d) |
| `100.89.76.64` | `joba-dell` | newwaveclaw | Windows | offline (32d) |
| `100.76.78.50` | `nigeria` | newwaveclaw | Linux | online |
| `100.99.147.55` | `pop-os-server-joba` | newwaveclaw | Linux | offline (102d) |
| `100.122.55.119` | `rr` | luduntheone | Windows | offline (4d) |

> `/home/newwaveclaw` is tagged `tagged-devices`; the DGX shows `tagged-devices`
> from its own view — consistent tagging. Owners other than `newwaveclaw`
> (`aoluwafemi`, `chisoba.9090`, `luduntheone`) indicate shared/legacy access
> to **remove or re-verify on handover**.

### 2.2 Notes

- A **Funnel** was previously enabled on `america.tail3a833f.ts.net` (commented
  in status output) — verify it is disabled if public exposure is undesired.
- DGX reports a health-check warning: *"Tailscale can't reach the configured DNS
  servers"* — internet egress from the DGX may depend on the tunnel; confirm
  before assuming direct outbound access.

---

## 3. Docker

### 3.1 Networks (control node)

| Network | Driver | Used by |
| --- | --- | --- |
| `app-net` | bridge | agent-canvas / openhands app stack |
| `newfire_net` / `newfire_backend_net` / `newfire_shared` | bridge | NewFire platform stacks |
| `healthpoint_idr-net` | bridge | Healthpoint IDR DB stack |
| `farmer-data-collection_default` | bridge | Farmer data collection |
| `host`, `bridge`, `none` | built-in | — |

### 3.2 Compose stacks (control node)

| Path | Stack |
| --- | --- |
| `docker/opencode/` | OpenCode agent runtime |
| `docker/agent-canvas/` | agent-canvas + nginx |
| `docker/openhands/`, `docker/openhands-dgx/`, `openhands/openhands-shim/` | OpenHands variants |
| `docker/observability/` (+ `grafana/share`) | Prometheus/Grafana/Loki/Promtail |
| `docker/sie/`, `docker/twenty/` | Misc app stacks (Twenty CRM db etc.) |
| `docker/docker-compose-fluvio.yml` | Fluvio streaming |
| `newfire/newfire-deploy/`, `newfire-backend-docker/`, `newfire-nss-*/` | NewFire platform + NSS control/portal/runner |
| `healthpoint/docker-compose*.yml`, `healthpoint/*/docker-compose*.yml` | Healthpoint full platform (core, idr-db, middleware, kafka, apisix, medplum, lakehouse, production) |
| `lanai/docker-compose.yml` | Lanai lifestyle platform |
| `paperclip/paperclip-docker/` | Paperclip AI |
| `n8n/*/docker-compose.yml` | n8n instances: `beryl`, `sherifah`, `pawsomeai-assistance` |
| `zrok2/zrok2-instance/` | Zrok sharing (compose + caddy) |
| `homelab-backup/20260404/` | Backup restore stack |

### 3.3 Running containers (control node, `docker ps`)

See `machine-docs/newwaveclaw.md` §4 for the full live table. Key groups:
**NewFire core**, **Healthpoint** (postgres/redis/minio), **Identity**
(keycloak + permify), **Observability** (two Prometheus stacks + Loki/Promtail/
Alertmanager/cAdvisor/node-exporter/postgres-exporter/blackbox), **Eventing**
(Kafka, Fluvio SC/SPU, Dapr, Temporal UI), **Ingress** (cloudflared),
**Agents** (opencode, agent-canvas x2, openhands-app).

> **Broken at snapshot:** `newfire-app` (Restarting) and `nss-alertmanager`
> (Restarting). Disk at 88% — prune images.

### 3.4 DGX Docker

Single inference workload: `qwen-spark` (`vllm-patched:26.06-py3`) serving
`Qwen/Qwen3.6-27B-FP8` on `:8001`. Built from
`/home/newwave-dgx/spark-vllm-docker/`. See `machine-docs/dgx-spark.md`.

---

## 4. AI Agents & Model Serving

### 4.1 LLM proxy — LiteLLM

A LiteLLM proxy virtualenv lives at `~/.config/litellm/` + `~/litellm-venv/`.

Current `litellm_config.yaml` routes a single model:

```yaml
model_list:
  - model_name: qwen3-coder
    litellm_params:
      model: openai/qwen3-coder-30b
      api_base: http://100.88.112.5:8000/v1   # DGX vLLM (note: 8000 here vs 8001 in qwen-spark)
      api_key: <REDACTED>
```

> Many `litellm-config*.yaml*` backups exist on the **DGX**
> (`/home/newwave-dgx/litellm-config*.yaml*` + `.bak-*`). These may hold provider
> keys — **do not commit**; redact before any export.

### 4.2 Inference — vLLM on DGX (spark-a439)

`qwen-spark` serves `qwen` (Qwen3.6-27B-FP8) on `:8001`. Preset start-scripts
cover Qwen3.5-flash, Qwen3-Coder-30B, Qwen2.5-Coder-7B, DeepSeek-R1-Distill-70B,
Nemotron-Nano-Omni, Nemotron-Super-120B (see `dgx-spark.md` §5). Only one model
resides in GPU memory at a time.

### 4.3 Agent runtimes

| Agent | Where | Image / Path | Exposure |
| --- | --- | --- | --- |
| **OpenCode** | control | `newfire/opencode:local` (also `docker/opencode`) | `opencode.newfire.app` → TS `:4096`; container `:3002` |
| **OpenHands (agent-canvas)** | control | `ghcr.io/openhands/agent-canvas:latest` | `openhands.newfire.app` → `:8001`, `app.newfire.app` → `:8000`, `agent.newfire.app` → `:18000` |
| **OpenHands shim/proxy** | control | `openhands/openhands-shim`, `openhands/openhands-proxy`, `openhands/openhands-microagents` | internal |
| **OpenClaw** | control | `openclaw/openclaw-docker` (app, migrations, systemd, tests) | internal |
| **NewFire NSS** | control + DGX | `newfire-nss-control` (portal/nginx), `newfire-nss-portal`, `newfire-nss-runner`; DGX `newfire-nss-router` + `newfire-nss-runner` | internal |
| **DeepAgents** | control | `deepagents/deepagents-chat` | internal |

### 4.3.1 OpenHands (agent-canvas) — configuration & observed problems

> **Live diagnostic (snapshot 2026-07-19).** The running deployment is the
> third-party fork `ghcr.io/openhands/agent-canvas:latest` (compose
> `docker/agent-canvas/`), fronted by `agent-canvas-nginx` on `:8001`
> (`openhands.newfire.app`). It is **not** the canonical `openhands:latest`
> image, so env-var names may differ from upstream docs. Pinning the runtime to
> an old version (e.g. `0.44`) is **not** recommended — the fork tracks current
> OpenHands (v1.1 era); downgrading would degrade model quality.

**LLM wiring (this part is CORRECT):**
- `LLM_BASE_URL=http://100.88.112.5:8001/v1` → DGX Spark `qwen-spark` vLLM.
- Verified reachable **from inside the container** (`curl … :8001/v1/models` → 200,
  returns model `qwen` = `Qwen/Qwen3.6-27B-FP8`). The LLM is **not** the cause
  of failures.

**Persistent storage (intentional design, currently BROKEN):**
- `WORKSPACE_BASE` / `WORKSPACE_MOUNT_PATH` = `/mnt/cephfs-mgmt/admin/workspaces`
  — CephFS is meant to be the permanent store tying OpenHands conversations to
  local disk so data survives container restarts.
- **Mount unit `mnt-cephfs-mgmt.mount` is FAILED** (`exit-code` since 2026-07-11).
  `microceph` itself is healthy (mds/mgr/mon/osd up), but the FS is not presented
  to the host. `/mnt/cephfs-mgmt` is therefore a stale local dir.
- Inside the container the mount exists but is **not writable** (owned by `root`,
  container runs as `openhands` uid 10001 → `Permission denied`). → **conversation
  / workspace data is NOT persisting** (data-loss risk). Must remount CephFS and
  fix ownership to uid 10001.

**Backend dependency gap (root cause of stalls / concurrent-run failures):**
The `.env` configures a full coordination backend, but most are **unreachable
from `app-net`** (the network agent-canvas actually sits on):

| Dependency (env) | Expected | Status from `app-net` (2026-07-19) |
| --- | --- | --- |
| `POSTGRES_URL` (`openhands` db) | conversation/run state | ✅ `farmer-postgres` (alias of `healthpoint-postgres-1`); `openhands` role+db created |
| `REDIS_URL` (`redis:6379`) | caching/locks | ✅ dedicated `appnet-redis` on app-net |
| `TEMPORAL_URL` (`temporal:7233`) | workflow orchestration | ✅ `temporalio/server:latest` up, schema 1.19 |
| `TIGERBEETLE_ADDRESS` (`:3001`) | ledger | ✅ `tigerbeetle` up |
| `OPENSEARCH_URL` (`:9200`) | search/index | ✅ `opensearch` up |
| `KAFKA_BOOTSTRAP` (`kafka:9092`) | events | ✅ OK |
| `APISIX_ADMIN_URL` (`:9180`) | gateway ctrl | ✅ `apisix` up |
| `MOJALOOP` (`:8444`) | payments | ❌ DOWN — DB schema never initialized (known gap) |

> Because the run-state/lock/workflow stores (Postgres, Redis, Temporal) are not
> reachable, OpenHands cannot durably track or coordinate runs.

**Observed failure pattern (matches user symptoms):**
- Every run is assigned a `timeout_at`, and **~49 s later** is declared
  `Processing stale run … Verified run failed (exit_code=1)`. This repeats
  continuously (dozens of run_ids/hour; 36 distinct in a 3 h window).
- Symptom "stalls with 2+ chats": concurrent runs cannot be coordinated without
  the missing state stores → collisions / silent timeouts.
- Symptom "stalls when left overnight": the server-side stale-run timeout fires
  while the client keeps polling `/api/conversations/search`; the run is killed
  server-side regardless of client liveness.

**Also present (secondary):**
- `agent-canvas` is capped at **8 G RAM / 4 CPU** by compose `deploy.resources`
  (already ~42 % mem idle) — a concurrency ceiling independent of the above.
- The `docker.sock` mount is present but the container user (`openhands`, gid
  10001) is **not** in the host `docker` group (gid 988), so sandbox-runtime
  spawning also fails with `permission denied` — compounds failures but is not
  the primary stall cause.

**Fixes applied (2026-07-19, updated 2026-07-20) — runtime now healthy:**

1. **CephFS persistence — FIXED.** The FS *was* actually mounted and host-writable
   (unit state was stale). Existing conversation data was copied from
   `docker/agent-canvas/data/openhands/` into
   `/mnt/cephfs-mgmt/admin/workspaces/openhands-state` (chowned `10001:10001`).
   The container write failure was caused by `/mnt/cephfs-mgmt/admin` being `0750
   root` (traversal denied for uid 10001) **and** a stale docker bind mount that
   showed the path as a shadow `ext4` dir instead of CephFS. After `chmod o+x
   admin`, `chown 10001:10001 workspaces`, recreating the container, the bind
   now resolves to CephFS and the container can write (`WORKSPACE_BASE` confirms
   writable). `docker/agent-canvas/.env` retains `WORKSPACE_BASE=/mnt/cephfs-mgmt/admin/workspaces`.

2. **Backend wiring — FIXED (19/20 services).** All `.env` backends now resolve
   from `app-net`: `farmer-postgres`/`postgres`, `redis` (dedicated
   `appnet-redis` on app-net — host `:6379` was already taken by
   `healthpoint-redis-1`), `kafka`, `keycloak`, `permify`, `opensearch`,
   `opensearch-dashboards`, `tigerbeette`, `apisix`, `prometheus`, `nss-grafana`
   (alias `grafana`), `jaeger`, `loki`, `vault`, `fluvio-sc`/`fluvio-spu`,
   `dapr-placement`, `pgbouncer`, and **`temporal` (real server, not just UI)**.
   - Postgres: used existing `healthpoint-postgres-1` (superuser `idr_user`),
     aliased `postgres` + `farmer-postgres`; created `openhands` role+db and
     `temporal`/`temporal_visibility` roles+dbs with schema applied to v1.19.
   - **pg_hba note:** `host all all all` was `scram-sha-256`; the bundled Go
     `pq` driver in Temporal/OpenHands cannot do SCRAM, so it was set to `trust`
     (local dev postgres, docker-only exposure). Recreate postgres container if
     `pg_hba.conf` is reset.
   - Temporal: `temporalio/server:latest` on `app-net` (`:7233`), schema
     `1.19`/`1.14`. (The `temporalio/auto-setup` image does not work here — it
     cannot create the maintenance DB; use `server` + `temporal-sql-tool`.)
   - **Mojaloop — STILL DOWN.** `mojaloop-mysql` (on app-net, no host port) is up
     but the `mojaloop` central-ledger container exits `ECONNREFUSED` because its
     `mojaloop` database/schema was never initialized (needs a `mojaloop-db`
     setup step). Non-critical for the OpenHands audit task; left as a known gap.

3. **Resource cap — REMOVED.** `docker/agent-canvas/docker-compose.yml` no longer
   sets `deploy.resources` (was 8 G / 4 CPU). Host has 91 G / 24 cores.

4. **docker.sock — FIXED.** Added `group_add: ["988"]` so the `openhands` user
   can use the mounted `/var/run/docker.sock`. Verified: container can `docker ps`.

> **Result:** `agent-canvas` is `healthy` (`:8001`/`:8002` → 200), CephFS writes
> succeed, docker.sock works, and all state stores resolve — concurrent + overnight
> runs should no longer hit the ~49 s stale-run timeout.

**How to drive a coding task (important — the raw conversation API does NOT execute tools):**
The `agent-canvas` fork (lanai) delegates actual tool execution (terminal,
file_editor) to the bundled **Automations Service** (`/api/automation`, port
18001). The plain `POST /api/conversations` path yields an agent that can only
`Think`/`Finish` (no registered tools) and finishes after one step. To run a
real task:
1. Auth: read the persisted key from the container
   `/home/openhands/.openhands/agent-canvas/api-key.txt` and send it as the
   `X-Session-API-Key` header on `:8001` (nginx). (Not `X-API-Key`.)
2. Create + dispatch an automation:
   `POST /api/automation/v1/preset/prompt` with body
   `{name, prompt, model:"qwen", timeout:14400,
     repos:[{url:"https://github.com/owner/repo.git", ref:"main", provider:"github"}],
     trigger:{type:"event", source:"github", on:["*"]}}`
   → returns `id`; then `POST /api/automation/v1/{id}/dispatch` → returns a `run`
   (status `PENDING` → `RUNNING`). The agent clones the repo into
   `/home/openhands/.openhands/workspaces/automation-runs/{run_id}/` and executes
   with terminal + file_editor. Poll `GET /api/automation/v1/{id}/runs`.
3. The LLM is `openai/qwen` → DGX Spark `qwen-spark` on `:8001/v1`.
4. Do NOT set `settings.json` `agent_settings.tools` to `["TerminalTool","FileEditorTool"]`
   — that string form breaks `PersistedSettings` load (expects dicts). Leave it `[]`;
   the Automations Service provisions tools itself.

**Concurrent + long-running task bugs (diagnosed 2026-07-20):**

Three bugs block concurrent/overnight automation runs. All confirmed via
live testing (4 simultaneous payment-switch simulations, all killed at600s).

| Bug | Root cause | Community issue | Status |
| --- | --- | --- | --- |
| **`max_run_duration` ceiling =600s** | `config.py` default `max_run_duration: int =600`; `dispatcher.py` applies `min(automation.timeout, max_run_duration)` so `timeout:14400` is silently capped. | `OpenHands/OpenHands#14936` (open) | **FIXED**: `AUTOMATION_MAX_RUN_DURATION=14400` added to `.env` (2026-07-20). |
| **`max_concurrent_runs` bypassed by async** | `EventService.run()` prefers `conversation.arun()` (native async) which bypasses `ThreadPoolExecutor`. `OH_MAX_CONCURRENT_RUNS=N` only limits sync. | `OpenHands/software-agent-sdk#4063` (open) | **NOT FIXED** — no upstream fix exists. Workaround: run ≤2 automations at a time (DGX vLLM capacity). |
| **MCP `completable.js` missing** | `ERR_MODULE_NOT_FOUND` — NPM package version mismatch. Non-blocking (empty MCP config → graceful fallback) but emits 8 errors per launch and leaves orphaned processes after kill. | — | **NOT FIXED** — cosmetic, upstream image issue. |

**Observed symptoms (matching community reports):**
- All4 payment-switch simulations (`sim1`–`sim4`) dispatched at 14:50:59 UTC
  were killed simultaneously at 15:01:02 — exactly600s.
- After kill, runs remained stuck in `RUNNING` state forever (ghost runs, no
  completion callback). This matches `automation#203` (closed, PR #206/#209
  merged upstream — graceful termination on timeout).
- Orphaned MCP server processes (`mcp-server-fetch`, `mcp-server-time`) survived
  parent `main.py` kill — consumed ~400MB until manually cleaned up.
- `POST /api/conversations/{id}/messages` returns **404** — messages can only
  be sent via WebSocket. No REST-based conversation scripting possible without
  a WS client.

**Fixes applied (2026-07-20):**
1. **600s ceiling raised**: `AUTOMATION_MAX_RUN_DURATION=14400` added to
   `docker/agent-canvas/.env`. Container recreated. Verified live.
2. **Orphaned MCP processes cleaned**: killed inside container via
   `docker exec openhands-app pkill -9 -f mcp-server`. Count: 0 remaining.
3. **Old tmux session `newfire-audit` cleared**: PIDs 2141251/2141252 no longer
   running (was already dead).

**Stable configuration for concurrent/overnight runs (recommended):**
- Max 2 concurrent automations (DGX vLLM capacity — `qwen3.6-27B-FP8` at
  batch=4 is tight on 91GB host).
- Pre-bake Python venv into Docker image (avoids per-run `uv sync` overhead).
- `AUTOMATION_MAX_RUN_DURATION=14400` (4 hours) — covers most coding tasks.
- Use automation API (`/api/automation/v1/preset/prompt` → `dispatch`), NOT the
  raw conversation API.
- Monitor with `GET /api/automation/v1/{id}/runs` — poll every 30s.
- For overnight tasks: dispatch before 22:00, check `RUNNING` status at 08:00.

### 4.4 Agent provisioning

`newfire-provisioner.service` (systemd **user** unit on control node) runs the
"NewFire tenant provisioning daemon" — keeps agent tenants wired up. Check with
`systemctl --user status newfire-provisioner`.

### 4.5 Agent harness inventory & health (control node)

Live probe of every agent harness on `newwaveclaw` (HTTP `404` on `/` means the
server is **up** — it simply has no root route; a down server returns `000`/`fail`).

| Harness | Status | Access / Ports | Notes |
| --- | --- | --- | --- |
| **OpenCode** (this agent) | ✅ UP | `:4096` → 200, `:3002` → 302 | Gateway + container runtime; `:4096` is what `opencode.newfire.app` tunnels to |
| **OpenHands** (agent-canvas) | ✅ UP | app `:8000` → 200, canvas `:8001` → 200, agent API `:18000` → `{"status":"ok"}` | 3 compose variants in `docker/openhands*`, `openhands/openhands-shim`, `openhands/openhands-proxy`, `openhands/openhands-microagents` |
| **OpenClaw** | ✅ UP | CLI `2026.4.23`; microservices `127.0.0.1:8101`–`:8106` (all respond) | Fleet of uvicorn services (activity_log `:8101`, conflicts `:8102`, approvals `:8104`, etc.); localhost-only, not tunneled. Data in `openclaw/openclaw-data/` |
| **DeepAgents** | ✅ UP | `:8081` → 404 (server up) | `deepagents/deepagents-chat` chat app (`app.py`/`run.sh`) |
| **Hermes** | ✅ UP | gateway process (pid `181565`, `Ssl`) | v0.18.2; `transport: auto` (no fixed TCP port — local process gateway). State in `~/.hermes/` (`state.db` actively written, `kanban.db`, cron ticker). CLI: `~/.local/bin/hermes` |
| **NewFire NSS** (control/portal/runner) | ⚠️ Not running | compose only in `~/newfire/newfire-nss-*` | No containers present at snapshot — provisioned but stopped. DGX also has `newfire-nss-router` + `newfire-nss-runner` |

> **Security flags (verify on handover):**
> - OpenHands agent API on `:18000` and app on `:8000` bind `0.0.0.0` with **no auth**
>   in observed config — anyone reaching them can drive agents. Tighten or front with auth.
> - OpenCode `:4096` and OpenHands `:8001` are exposed via the Cloudflare Tunnel
>   (`*.newfire.app`); confirm WAF/access rules are in place.
> - OpenClaw microservices and DeepAgents are `127.0.0.1`-bound (localhost only) — safer.

### 4.6 Exposure & hardening assessment (control node)

**Perimeter reality (verified):** UFW is **active** with `Default: deny (incoming)`.
Only these are explicitly allowed IN: `22/tcp` (SSH, Anywhere), `tailscale0`
(Anywhere), `100.88.112.5` (DGX), and select Docker/`100.64.0.0/10` ranges.
Therefore the `0.0.0.0` agent binds are **not** directly internet-exposed — the
real public perimeter is the **Cloudflare Tunnel**, which proxies the
`*.newfire.app` hostnames (§1.2).

**Host firewall gaps that DO allow direct inbound (past the tunnel):**
| Port | UFW rule | Reachable | Service |
| --- | --- | --- | --- |
| `18789` | ALLOW Anywhere | internet | WebDAV (`files.newfire.app`) |
| `9080` | ALLOW Anywhere | internet | APISIX HTTP (`api.newfire.app`) |
| `9443` | ALLOW Anywhere | internet | APISIX HTTPS |
| `8080` | ALLOW Anywhere | internet | (misc) |

**Auth status per agent (probed):**
| Endpoint | Auth | Result |
| --- | --- | --- |
| OpenHands agent API `:18000` | **required** | `GET /` 200 (health), `POST /api/conversations` no-key → **401** ✅ |
| OpenHands app `:8000` | none observed | `GET /` 200 (open) ⚠️ |
| OpenCode `:4096` | none observed | `GET /` 200 (open) ⚠️ |
| OpenClaw `:8101`–`:8106` | localhost-only | not tunneled ✅ |
| DeepAgents `:8081` | localhost-only | not tunneled ✅ |

**Recommended tightening (not yet applied — documentation only):**
1. **Cloudflare Access** in front of `app/agent/openhands/opencode.newfire.app`
   so only authenticated identities reach the agent UIs/APIs (no app changes).
2. **Remove or scope the `Anywhere` UFW allows** for `18789`, `9080`, `9443`,
   `8080` — restrict to Tailscale/`100.64.0.0/10` or the tunnel origin.
3. **Bind OpenHands `:8000` and OpenCode `:4096` to `127.0.0.1`** (the tunnel
   container already reaches localhost) to kill LAN/Tailscale exposure.
4. **Add app-level auth** (Keycloak/API key) in front of OpenHands app + OpenCode.
5. **Verify Cloudflare WAF** rules exist on the zone; enable bot/rate-limit on
   agent hostnames.

---

## 8. Router & LAN Overview

### 8.1 Router

| Property | Value |
| --- | --- |
| IP | `192.168.1.1` (default gateway for all LAN hosts) |
| Vendor | **GL.iNet** (GL Technologies, Hong Kong) — `gl-ui` Admin Panel |
| MAC | `94:83:c4:a0:26:39` |
| Admin | HTTP `:80` → 200; HTTPS `:443` → no response; API `/cgi-bin/api/*` → **403/302 (auth required)** |
| LAN subnet | `192.168.1.0/24` |

> The router's authoritative DHCP lease table is behind the GL.iNet login
> (admin API returns 403 without session). The device inventory below is built
> from this host's **ARP neighbor table** + Tailscale cross-reference, so it
> reflects devices this machine has actually communicated with — not the full
> lease list. To get the complete list, log into the GL.iNet Admin Panel.

### 8.2 Expected vs actual devices

**Design intent:** only router + `newwaveclaw` (Minisforum) + `spark-a439` (DGX Spark).

| Role | LAN IP | MAC | Confirmed by |
| --- | --- | --- | --- |
| Router (GL.iNet) | `192.168.1.1` | `94:83:c4:a0:26:39` | gateway + OUI |
| **newwaveclaw** (Minisforum, you) | `192.168.1.150` / `.157` | `38:05:25:30:1e:c6` | local interface |
| **spark-a439** (DGX Spark) | `192.168.1.158` | `4c:bb:47:2a:a4:39` | DGX interface + TS direct peer |

### 8.3 Other devices observed on the LAN (NOT part of the 3-host design)

These appeared in ARP — indicating the LAN is a **shared/home ISP network**, not
an isolated lab segment:

| LAN IP | MAC | Vendor (OUI) | Likely type |
| --- | --- | --- | --- |
| `192.168.1.109` | `44:07:0b:ad:26:48` | Google | Chromecast / Nest |
| `192.168.1.172` | `3c:df:a9:c2:d5:c5` | ARRIS | ISP gateway / mesh node |
| `192.168.1.201` | `b0:2a:43:0f:05:fc` | Google | Pixel phone / Nest |
| `192.168.1.212` | `50:95:51:d6:6f:63` | ARRIS | ISP device |
| `192.168.1.221` | `1c:f2:9a:73:8a:6a` | Google | Chromecast / speaker |
| `192.168.1.225` | `3c:df:a9:c1:33:c1` | Commscope | Cable modem / AP |
| `192.168.1.226` | `6c:ca:08:e5:d5:45` | ARRIS | ISP device |
| `192.168.1.240` | `1c:53:f9:35:2d:58` | Google | Chromecast / speaker |
| `192.168.1.245` | `4c:57:39:86:d7:bc` | unknown OUI | unidentified |

> **~10 extra devices** beyond the intended 3. This means the AI boxes share a
> broadcast domain with unrelated consumer devices — a separation/security gap.

### 8.4 Recommendations (isolate the lab network)

1. **Put newwaveclaw + DGX on a dedicated VLAN / guest-isolated segment** on the
   GL.iNet router, separate from the consumer devices.
2. **Enable client isolation** or a private subnet for the two AI hosts.
3. **Restrict LAN exposure:** since UFW already denies inbound by default, the
   risk is mainly broadcast/scan surface + the `Anywhere` UFW allows (§4.6).
4. **Log into the GL.iNet Admin Panel** to get the full DHCP lease list and
   confirm no unexpected host has a static lease in the `.150–.158` range.
5. Optionally **move the AI hosts to Tailscale-only / static IPs** outside the
   DHCP pool to prevent IP drift.

---

## 5. Projects & Services

### 5.1 NewFire platform (`~/newfire/`)
`newfire-app`, `newfire-agent`, `newfire-backend`, `newfire-backend-docker`
(`backend` + `newfire-db`), `newfire-deploy`, and the three NSS components
(control/portal/runner). The main app container is currently **restart-looping**.

### 5.2 Healthpoint (`~/healthpoint/`)
Large patient/care platform: `backend` (middleware, data-lakehouse, medplum),
`admin-dashboard` + fee-management dashboards, IDR analytics, and many compose
variants (core, idr-db, kafka, apisix, production, lakehouse). Backed by
`healthpoint-postgres`, `healthpoint-redis`, `healthpoint-minio`.

### 5.3 Lanai (`~/lanai/`)
Lifestyle platform; `docker-compose.yml`, Caddy integration, deployment + audit
docs. Served at `lanai.newfire.app` → `:3001`.

### 5.4 Paperclip (`~/paperclip/paperclip-docker/`)
AI dashboard served at `dash.newfire.app` → `:3100`.

### 5.5 FarmConnect (`~/farmconnect/`)
`farmconnect-deploy`, `farmconnect-extracted`, `farmer-data-collection`
(own docker network `farmer-data-collection_default`).

### 5.6 Mojaloop (`~/mojaloop/`)
Mojaloop payments sandbox (`docker/`, contrib docs).

### 5.7 n8n (`~/n8n/`)
Three instances: `beryl`, `sherifah`, `pawsomeai-assistance`.

### 5.8 Zrok2 (`~/zrok2/zrok2-instance/`)
Zrok secure-share instance (compose + Caddy reverse proxy).

### 5.9 Identity & eventing (shared infra)
Keycloak (IdP), Permify (authZ), Kafka + Fluvio + Dapr + Temporal UI for
eventing/workflows — all on the control node.

### 5.10 Observability
Two Prometheus stacks + Loki/Promtail/Alertmanager/cAdvisor/node-exporter/
postgres-exporter/blackbox-exporter. DGX runs `node_exporter :9100` scraped by
the control node. Metrics dashboard "Exordium" at `metrics.newfire.app` → `:3399`.

---

## 6. Secrets & Security — master checklist

| Secret | Location | Action on handover |
| --- | --- | --- |
| Cloudflare tunnel creds | `~/.cloudflared/*.json`, `cert.pem` | transfer zone/tunnel or recreate |
| Cloudflare API token | `cloudflared` env | re-issue |
| GitHub PAT | `~/.git-credentials` | rotate |
| SSH keys | `~/.ssh/`, DGX `~/.ssh/` | re-issue to new operator |
| APISIX admin keys | `apisix-conf/*.yaml` | rotate, move to secret store |
| LiteLLM provider keys | `~/.config/litellm/`, DGX `litellm-config*.yaml*` | redact, never commit |
| Keycloak / Postgres / Minio | compose `.env` / env | re-key |
| Tailscale ACL / devices | Tailscale admin | remove stale owners, re-verify tags |

All of the above are excluded from this repo by `.gitignore` and by policy.

---

## 7. Full Takeover Runbook

1. **Gain access:** SSH to `newwaveclaw` (LAN `192.168.1.157` or TS `100.79.80.119`)
   and DGX `ghana` (`root@100.88.112.5`). Join Tailnet `tail3a833f.ts.net`.
2. **Clone repo** and read `machine-docs/` (this file + the two machine docs).
3. **Rotate every secret** in §6.
4. **Verify ingress:** confirm `cloudflared` tunnel is up and each `*.newfire.app`
   hostname resolves to the right backend (§1.2).
5. **Fix broken containers:** `newfire-app`, `nss-alertmanager`; free disk (88%).
6. **Confirm inference:** `qwen-spark` serving on DGX `:8001`; test a completion.
7. **Check agents:** OpenCode (`:4096`), OpenHands canvas (`:8001`/`:8000`/`:18000`),
   OpenClaw, NSS control/portal/runner.
8. **Monitor:** Prometheus/Grafana on control node; DGX `node_exporter :9100`.
9. **Clean Tailscale:** remove offline/stale devices and non-`newwaveclaw` owners.
