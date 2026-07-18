# AI Homelab — Complete Build Guide

A ground-up record of building a two-machine AI inference platform with metered API access, from unboxing hardware to serving models.

---

## Hardware

### Machine 1: Minisforum X1 Pro 370 — Control Plane

| Spec | Value |
|------|-------|
| Role | Orchestration, API gateway, lightweight inference |
| CPU | AMD Ryzen AI 9 HX 370 (12 cores, 24 threads) |
| RAM | 96 GB DDR5 |
| Storage | 2 TB NVMe SSD |
| GPU | Integrated Radeon 890M (not used for inference) |
| OS | Ubuntu 24.04.4 LTS (kernel 6.17.0-19-generic, x86_64) |
| LAN IP | 192.168.1.157 |
| Tailscale IP | 100.79.80.119 |
| Username | `newwaveclaw` |

### Machine 2: NVIDIA DGX Spark — Compute Engine

| Spec | Value |
|------|-------|
| Role | GPU inference, large model serving |
| CPU | NVIDIA GB10 Grace Superchip (Arm, 10 cores) |
| RAM | 128 GB Unified (CPU+GPU shared) |
| Storage | 4 TB NVMe |
| GPU | NVIDIA Blackwell GB10 (1 PFLOP FP4, 209 TFLOPS FP16) |
| OS | Ubuntu 24.04.4 LTS, DGX Spark Version 7.5.0 (kernel 6.17.0-1014-nvidia, aarch64) |
| NVIDIA Driver | 580.142, CUDA 13.0 |
| LAN IP | 192.168.1.158 |
| Tailscale IP | 100.88.112.5 |
| Username | `newwave-dgx` |

### Network Equipment

| Device | Role |
|--------|------|
| GL.iNet Router | Main router at 192.168.1.1, DHCP server |
| Network Switch | Ethernet switch connecting DGX Spark to router |
| Phone Hotspot | Backup internet (used during initial setup) |

---

## Network Topology

```
Internet
  |
  +-- GL.iNet Router (192.168.1.1)
        |
        +-- [WiFi] Minisforum (192.168.1.157)
        |
        +-- [Switch] --> [Ethernet] DGX Spark (192.168.1.158)
```

### Tailscale Overlay Network

Both machines are on Tailscale with MagicDNS hostnames, allowing SSH access from anywhere.

```
Tailscale Network (MagicDNS names):
  100.79.80.119   america     (Minisforum)
  100.88.112.5    ghana       (DGX Spark)
  100.76.78.50    nigeria     (GL-X3000 Router)
  100.107.229.67  MacBook Air (client)
  100.112.32.48   iPhone 14   (mobile)
```

### Production Domain (newfire.app)

Traffic flows through Cloudflare Tunnel (outbound only, no open ports):

```
Public Internet
  |
Cloudflare Edge (TLS termination, DDoS protection)
  |
cloudflared tunnel (Minisforum, systemd service)
  |
  +-- newfire.app         -> :4000  (NewFire app)
  +-- app.newfire.app     -> :4000  (Client portal)
  +-- dev.newfire.app     -> :4000  (Developer portal)
  +-- api.newfire.app     -> :9080  (APISIX gateway)
  +-- dash.newfire.app    -> :3100  (Paperclip AI, pending)
  +-- files.newfire.app   -> :18789 (WebDAV file sharing)
```

### Port Map (Current)

**Minisforum (192.168.1.157 / 100.79.80.119)**

| Port | Service | Protocol | Access |
|------|---------|----------|--------|
| 22 | SSH | TCP | LAN + Tailscale |
| 3000 | OpenHands (reserved) | TCP | LAN + Tailscale |
| 3002 | OpenCode (reserved) | TCP | LAN + Tailscale |
| 9080 | APISIX HTTP | TCP | LAN + Tailscale |
| 9180 | APISIX Admin | TCP | Localhost only |
| 9443 | APISIX HTTPS | TCP | LAN + Tailscale |
| 11434 | Ollama (CPU) | TCP | Localhost |
| 18789 | OpenClaw Gateway | TCP | LAN + Tailscale |

**DGX Spark (192.168.1.158 / 100.88.112.5) (UFW active)**

| Port | Service | Protocol | Access |
|------|---------|----------|--------|
| 22 | SSH | TCP | Anywhere (key auth) |
| 3000 | OpenHands | TCP | Tailscale only |
| 9000 | Whisper ASR | TCP | Minisforum only |
| 11434 | Ollama (GPU) | TCP | Minisforum only |

---

## Software Stack (Current)

| Software | Version | Machine | Purpose |
|----------|---------|---------|---------|
| OpenClaw | 2026.4.2 (d74a122) | Minisforum | Multi-agent orchestrator / gateway |
| NemoClaw | 0.0.6 | DGX Spark | Sandbox manager, agent isolation |
| OpenShell | 0.0.22 | DGX Spark | Container orchestration for NemoClaw |
| Ollama | Latest | Both | Local LLM serving |
| APISIX | 3.15.0 | Minisforum | API gateway with metering |
| etcd | 3.5.7 | Minisforum | APISIX config store |
| Tailscale | Latest | Both | VPN overlay network |
| cloudflared | 2026.3.0 | Minisforum | Cloudflare Tunnel for production ingress |
| Docker | 29.2.1 (Spark), CE (Mini) | Both | Container runtime |
| Node.js | 22.22.2 | Both | Runtime for OpenClaw/NemoClaw |
| UFW | Latest | Both | Firewall (now active on both machines) |
| fail2ban | Latest | Minisforum | SSH brute-force protection |
| Whisper ASR | latest | DGX Spark | Speech-to-text (Docker, port 9000) |

---

## Models Deployed

| Model | Size | Location | Context | Use Case |
|-------|------|----------|---------|----------|
| gemma4:26b | 18 GB | DGX Spark (GPU) | 128K | General purpose, content creation (55 tok/s) |
| deepseek-r1:32b | 19.9 GB (Q4_K_M) | DGX Spark (GPU) | 8K | Document drafting, reasoning |
| deepseek-r1:70b | 42.5 GB (Q4_K_M) | DGX Spark (GPU) | 4K | Complex legal reasoning |
| glm4:9b | 5.5 GB (Q4_0) | DGX Spark (GPU) | 128K | Fast Q&A, classification |
| nemotron-3-super | 86.8 GB | DGX Spark (GPU) | N/A | Heavy reasoning |
| nomic-embed-text | 274 MB | DGX Spark (GPU) | N/A | Vector embeddings (768-dim) |
| qwen | 2.3 GB | DGX Spark (GPU) | N/A | Lightweight tasks |
| glm-5.1:cloud | Cloud (744B MoE) | OpenRouter | 198K | Agentic coding (cloud, $0.95/M in) |
| Claude Sonnet 4.5 | Cloud | OpenRouter | 200K | Cloud fallback (paid) |
| Nemotron Nano 30B | Cloud | OpenRouter | 131K | Free cloud fallback |

---
## Application Layer
| Service | Image | Port(s) | Status | Description |
|---------|-------|---------|--------|-------------|
| Newfire App | `newfire-app:latest` | - | ⚠️ Restarting | Main application frontend |
| Newfire Backend | `newfire-backend:1.18.3-tasklist` | 3200 (internal) | ✅ Healthy | Backend API with tasklist features |
| OpenCode | `newfire/opencode:local` | - | ✅ Running | Code editor/IDE service |


---
## Ai & Agent Services 
| Service | Image | Port(s) | Status | Description |
|---------|-------|---------|--------|-------------|
| OpenHands App | `ghcr.io/openhands/agent-canvas:latest` | - | ✅ Running | AI agent interface |
| Agent Canvas | `ghcr.io/openhands/agent-canvas:latest` | 8001→8000 | ✅ Healthy | Agent visualization canvas |
| Agent Canvas Nginx | `nginx:alpine` | 8002→80 | ✅ Healthy | Reverse proxy for agent canvas |
| IDR Rust Service 1 | `alpine:latest` | 8002 (internal) | ✅ Running | Rust microservice instance |
| IDR Rust Service 2 | `alpine:latest` | 8002 (internal) | ✅ Running | Rust microservice instance |

---
## Identity & Access Management
| Service | Image | Port(s) | Status | Description |
|---------|-------|---------|--------|-------------|
| Keycloak | `quay.io/keycloak/keycloak:26.2.5` | 8080 | ✅ Running | IAM and SSO provider |
| Permify | `ghcr.io/permify/permify:latest` | 3476, 3478 | ✅ Running | Fine-grained authorization service |
| Vault | `hashicorp/vault:latest` | 8200 | ✅ Running | Secrets management |

---
## Databases
| Service | Image | Port(s) | Status | Description |
|---------|-------|---------|--------|-------------|
| Healthpoint Postgres | `postgres:16-alpine` | 5432 | ✅ Healthy | Primary database (Healthpoint) |
| Twenty Database | `postgres:16` | 5432 (internal) | ✅ Healthy | Database for Twenty CRM |
| Newfire Database | `postgres:16-alpine` | 5432 (internal) | ✅ Healthy | Application database |
| Redis | `redis:7-alpine` | - | ✅ Healthy | In-memory cache/session store |
| Qdrant | `qdrant/qdrant:latest` | 6333-6334 (localhost) | ✅ Running | Vector database for embeddings |
| PgBouncer | `edoburu/pgbouncer` | 6432 | ✅ Running | Connection pooler for Postgres |

---
## Message Streaming
| Service | Image | Port(s) | Status | Description |
|---------|-------|---------|--------|-------------|
| Kafka | `apache/kafka:3.7.0` | 9092 | ✅ Running | Event streaming platform |
| Fluvio SC | `infinyon/fluvio:latest` | 9103→9003 | ✅ Running | Streaming controller |
| Fluvio SPU | `infinyon/fluvio:latest` | 9110-9111→9010-9011 | ✅ Running | Streaming processing unit |

---
## Observability Stack
Metrics Collection
| Service | Image | Port(s) | Status | Description |
|---------|-------|---------|--------|-------------|
| Prometheus | `prom/prometheus:latest` | 9090 | ✅ Running | Metrics storage and querying |
| Node Exporter | `prom/node-exporter:v1.8.2` | 9100 (internal) | ✅ Running | Host metrics exporter |
| cAdvisor | `gcr.io/cadvisor/cadvisor:v0.49.1` | 8080 (internal) | ✅ Healthy | Container metrics exporter |
| Postgres Exporter | `prometheuscommunity/postgres-exporter:v0.16.0` | 9187 (internal) | ✅ Running | Postgres metrics exporter |
| Blackbox Exporter | `prom/blackbox-exporter:latest` | 9115 | ✅ Running | Endpoint probing/monitoring |

Logging
| Service | Image | Port(s) | Status | Description |
|---------|-------|---------|--------|-------------|
| Loki | `grafana/loki:latest` | 3101→3100 | ✅ Running | Log aggregation system |
| NSS Loki | `grafana/loki:3.2.0` | 3100 (internal) | ✅ Running | Secondary Loki instance |
| Promtail | `grafana/promtail:latest` | - | ✅ Running | Log shipper |
| NSS Promtail | `grafana/promtail:3.2.0` | - | ✅ Running | Secondary log shipper |

Visualization & Alerting
| Service | Image | Port(s) | Status | Description |
|---------|-------|---------|--------|-------------|
| Grafana | `grafana/grafana:11.3.0` | 3399→3000 (localhost) | ✅ Running | Dashboards and visualization |
| Alertmanager | `prom/alertmanager:v0.27.0` | - | ⚠️ Restarting | Alert routing and deduplication |

Tracing
| Service | Image | Port(s) | Status | Description |
|---------|-------|---------|--------|-------------|
| Jaeger | `jaegertracing/all-in-one:latest` | 16686 | ✅ Running | Distributed tracing UI |

Infrastructure Services
| Service | Image | Port(s) | Status | Description |
|---------|-------|---------|--------|-------------|
| Dapr Placement | `daprio/dapr:latest` | 50005→50001 | ✅ Running | Actor placement service |
| Temporal UI | `temporalio/ui:2.26.2` | 8085→8080 | ✅ Running | Workflow orchestration UI |
| Cloudflared | `cloudflare/cloudflared:latest` | - | ✅ Running | Cloudflare tunnel |

---
Port Mapping Summary

Externally Accessible Ports
| Port | Service | URL |
|------|---------|-----|
| 8001 | Agent Canvas | `http://localhost:8001` |
| 8002 | Nginx (Agent Canvas) | `http://localhost:8002` |
| 8080 | Keycloak | `http://localhost:8080` |
| 8085 | Temporal UI | `http://localhost:8085` |
| 8200 | Vault | `http://localhost:8200` |
| 9000 | MinIO API | `http://localhost:9000` |
| 9001 | MinIO Console | `http://localhost:9001` |
| 9090 | Prometheus | `http://localhost:9090` |
| 9092 | Kafka | `localhost:9092` |
| 9115 | Blackbox Exporter | `http://localhost:9115` |
| 16686 | Jaeger UI | `http://localhost:16686` |

----
Localhost Only Ports
| Port | Service |
|------|---------|
| 3399 | Grafana |
| 6333-6334 | Qdrant |



---
## Three-Tier Inference Architecture

```
Request → OpenClaw (Minisforum) → Route Decision
                |
                +→ Tier 1: Minisforum CPU (free, instant, light tasks)
                |    └── glm-4.7-flash
                |
                +→ Tier 2: DGX Spark GPU (free, fast, heavy tasks)
                |    └── deepseek-r1:32b-8k, glm4:9b
                |
                +→ Tier 3: OpenRouter Cloud (paid, always available)
                     └── Claude Sonnet 4.5, DeepSeek R1, Nemotron Nano
```

### Metered Access via APISIX

```
External App → APISIX (:9080) → [API Key Check] → DGX Spark Ollama → Response
                                      |
                                 No key? → 401 Rejected
```

---

## Credentials & Endpoints (Quick Reference)

| Item | Value |
|------|-------|
| Minisforum SSH | `ssh newwaveclaw@america` |
| DGX Spark SSH | `ssh newwave-dgx@ghana` |
| Production Site | `https://newfire.app` (basic auth: newfire / may1st.) |
| Developer Portal | `https://dev.newfire.app/developers` |
| API Gateway | `https://api.newfire.app` |
| WebDAV Files | `https://files.newfire.app/webdav/` |
| Cloudflare Tunnel ID | d0f9998f-73ee-4c64-a259-0f09a65d9856 |
| OpenClaw Dashboard | `http://america:18789` |
| OpenClaw Token | `[REDACTED-ROTATED]` |
| APISIX Gateway | `http://100.79.80.119:9080` |
| APISIX Admin API | `http://127.0.0.1:9180` (from Minisforum only) |
| APISIX Admin Key | `1613a2c9306d7f98f8c926eb8a6a469ea76d0eda70aa3fc34fc32b18c58678d1` |
| Personal API Key (APISIX) | `homelab-personal-2026` |
| OpenRouter API Key | `[REDACTED-REVOKED]` |
| NemoClaw Sandbox UI | `http://127.0.0.1:18789/#token=6e8df882...` (DGX Spark local only) |

---
Stack composition
Total Containers: 37
├── Application Layer:      3
├── AI & Agent Services:    5
├── Identity & Security:    3
├── Databases:              6
├── Message Streaming:      3
├── Object Storage:         1
├── Observability:         13
└── Infrastructure:         3
---

## Build Sessions

| Date | File | Summary |
|------|------|---------|
| 2026-04-04 | [SESSION_1.md](2026-04-04_SESSION_1.md) | Foundation build: SSH access, OpenClaw, NemoClaw, Ollama models, OpenRouter, APISIX |
| 2026-04-04 | [SESSION_2.md](2026-04-04_SESSION_2.md) | Integration and hardening: APISIX consumers, agent workers, smart routing, Docker log rotation |
| 2026-04-10 | [2026-04-10_SESSION.md](2026-04-10_SESSION.md) | Zero-trust networking (zrok2+OpenZiti), NewFire client portal frontend |
| 2026-04-11 to 16 | [2026-04-11-16_SESSION.md](2026-04-11-16_SESSION.md) | Domain, TLS, developer portal, live API keys, model expansion, security hardening |

## Config Snapshots

| Date | File | Description |
|------|------|-------------|
| 2026-04-04 | [openclaw_config_2026-04-04_v1.json](openclaw_config_2026-04-04_v1.json) | Initial config with 3 providers: ollama, openrouter, dgx-ollama |
| 2026-04-04 | [openclaw_config_2026-04-04_v2.json](openclaw_config_2026-04-04_v2.json) | Full config with aliases, fallbacks, 3 agents, smart routing |

---

## Gotchas & Lessons Learned

1. **DGX Spark username is `newwave-dgx`** (not `newwave-gdx`). The `d` vs `g` difference caused hours of SSH password failures.

2. **SSH terminal mangles multi-line pastes**: Long commands and JSON payloads break when pasted over SSH. Workaround: write files on Mac and `scp` them to the server.

3. **NodeSource apt conflict on Minisforum**: Two repo files (`nodesource.list` and `nodesource.sources`) with different `Signed-By` paths. Fix: `sudo rm /etc/apt/sources.list.d/nodesource.sources`.

4. **The `openclaw` system user has no sudo password**: Install system packages (Ollama, etc.) as `newwaveclaw` first, then `sudo su - openclaw` for OpenClaw commands.

5. **Ollama KV cache explosion**: Default context (524K tokens) allocates 77+ GB KV cache, causing OOM. Fix: create context-limited variants with `PARAMETER num_ctx 8192` in a Modelfile.

6. **OpenClaw config is strict**: All provider fields (baseUrl, api, apiKey, models array) must be set together. Cannot incrementally set them via `openclaw config set`. Edit the JSON file directly instead.

7. **OpenClaw `api` field enum**: Must be exactly one of: `openai-completions`, `openai-responses`, `openai-codex-responses`, `anthropic-messages`, `google-generative-ai`, `github-copilot`, `bedrock-converse-stream`, `ollama`, `azure-openai-responses`. For OpenRouter use `openai-responses`.

8. **OpenClaw `gateway.bind`**: Cannot use `0.0.0.0` directly. Use bind mode names: `lan`, `loopback`, `custom`, `tailnet`, `auto`.

9. **NemoClaw port 8080 is gRPC, not REST**: You cannot `curl` it. Cross-machine inference goes through Ollama port 11434 directly.

10. **APISIX admin key is random per container**: Check `/usr/local/apisix/conf/config.yaml` for the actual key after each container recreation. Also need `allow_admin: ["0.0.0.0/0"]` to access admin API from the Docker host.

11. **HDMI cable matters for DGX Spark display**: HDMI-to-DisplayPort adapter did not work. Full HDMI-to-HDMI cable was required to get monitor output.

12. **NemoClaw is a real NVIDIA project**: Unlike some tools mentioned in AI-generated guides, NemoClaw exists at `github.com/NVIDIA/NemoClaw` and installs successfully. However, its role is sandbox management (not a REST API gateway as some guides assume).

---

## What's Done (since April 11)

- [x] Domain acquired: newfire.app with Cloudflare Tunnel (all subdomains live with TLS)
- [x] Developer portal and dashboard built (live API key management via APISIX)
- [x] Per-agent model mapping (7 agents, 5 models, hybrid local+cloud)
- [x] Gemma 4 (26B) and GLM-5.1 (cloud) pulled and tested
- [x] Embedding model (nomic-embed-text) and Whisper transcription deployed on DGX Spark
- [x] OpenClaw updated to 2026.4.14, WebDAV plugin installed
- [x] UFW firewall enabled on DGX Spark, Minisforum rules tightened
- [x] zrok2 share persistent via systemd agent service
- [x] Tailscale MagicDNS hostnames (america, ghana, nigeria)
- [x] nginx basic auth gate on production site
- [x] Disk cleanup: Minisforum 88% to 77%

## What's Remaining

- [ ] Install Paperclip AI (agent hierarchy, budgets, audit logging) on port 3100
- [ ] Wire Paperclip to dash.newfire.app (Cloudflare route already exists)
- [ ] Pull additional models: qwen3, llama4, phi-4, codestral
- [ ] Verify agent chat end-to-end through newfire.app domain
- [ ] Mesibo or Telegram channel for mobile client access
- [ ] CongaLine fleet management for per-client agent isolation
- [ ] Claude Corp daemon for autonomous overnight operation
- [ ] LLMtary security audit (pentest against all endpoints)
- [ ] Fix APISIX Prometheus scrape target (currently down)
- [ ] Grafana dashboards: budget tracker, client dashboard, system health
- [ ] Operational runbook for restart procedures and disaster recovery
- [ ] Beta onboard Ms. Sherifah and Aunty Funmi
- [ ] Move OpenRouter API key from frontend to backend proxy
