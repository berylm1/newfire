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
