# `newwaveclaw` — Primary Control Node

> Takeover-ready documentation. Generated from a live snapshot of the machine.

## 1. Overview

| Field | Value |
| --- | --- |
| Hostname | `newwaveclaw` |
| Tailscale hostname | `america` |
| Tailscale IP | `100.79.80.119` |
| LAN IP | `192.168.1.157` |
| OS | Ubuntu 24.04.4 LTS (Noble Numbat) |
| Kernel | `6.17.0-1028-oem` (x86_64) |
| CPU cores | 24 |
| RAM | 91 GiB total / ~72 GiB available |
| Disk | 492 GB LVM (`ubuntu--vg-ubuntu--lv`), 88% used (415G/57G) |
| Uptime | ~7 days at snapshot |
| Primary user | `newwaveclaw` (uid 1000, in `docker`, `sudo`, `lxd`, `ollama`) |
| GPU | None (CPU-only node — inference runs on DGX Spark) |

## 2. Access

| Method | Address | Notes |
| --- | --- | --- |
| SSH (LAN) | `newwaveclaw@192.168.1.157` | standard ssh |
| SSH (Tailscale) | `newwaveclaw@100.79.80.119` or `america.tail3a833f.ts.net` | via Tailscale |
| VNC | `127.0.0.1:5901` (localhost only) | desktop access |

- SSH key: `/home/newwaveclaw/.ssh/id_ed25519` (pub registered on DGX Spark).
- GitHub auth uses a PAT stored in `/home/newwaveclaw/.git-credentials`
  (helper `store`). **Rotate this token if the box is decommissioned.**

## 3. Installed Tooling

| Tool | Version |
| --- | --- |
| Docker | 29.6.2 |
| Git | 2.43.0 |
| Node.js | v22.23.1 |
| npm | 11.12.1 |
| Python | 3.12.3 |
| Go | present |
| Cloudflared | 2026.3.0 |
| Tailscale | 1.98.9 |
| PM2 | 7.0.3 |

## 4. Running Services (Docker)

> `docker ps` at snapshot. Containers in `Restarting` state are **broken** — see notes.

### NewFire platform / core
| Container | Image | Status | Purpose |
| --- | --- | --- | --- |
| `newfire-app` | `newfire-app:latest` | **Restarting** | Main NewFire application (failing — check logs) |
| `opencode` | `newfire/opencode:local` | Up 33h | OpenCode agent runtime |
| `agent-canvas` | `ghcr.io/openhands/agent-canvas:latest` | Up 33h (healthy) | OpenHands agent canvas |
| `agent-canvas-nginx` | `nginx:alpine` | Up 33h (healthy) | Reverse proxy for canvas |
| `openhands-app` | `ghcr.io/openhands/agent-canvas:latest` | Up 33h | OpenHands app |
| `cloudflared` | `cloudflare/cloudflared:latest` | Up 28h | Cloudflare Tunnel ingress |
| `newfire-provisioner.service` (systemd user) | — | active | NewFire tenant provisioning daemon |

### Healthpoint (patient/care platform)
| Container | Image | Status |
| --- | --- | --- |
| `healthpoint-postgres-1` | `postgres:16-alpine` | Up 30h (healthy) |
| `healthpoint-redis-1` | `redis:7-alpine` | Up 25h (healthy) |
| `healthpoint-minio-1` | `minio/minio:latest` | Up 25h (healthy) |

### Identity & authorization
| Container | Image | Status |
| --- | --- | --- |
| `keycloak` | `quay.io/keycloak/keycloak:26.2.5` | Up 25h |
| `permify` | `ghcr.io/permify/permify:latest` | Up 25h |

### Monitoring / observability (two Prometheus stacks)
| Container | Image | Status |
| --- | --- | --- |
| `nss-prometheus` | `prom/prometheus:v2.55.0` | Up 33h |
| `nss-grafana` | `grafana/grafana:11.3.0` | Up 33h |
| `nss-loki` | `grafana/loki:3.2.0` | Up 33h |
| `nss-promtail` | `grafana/promtail:3.2.0` | Up 33h |
| `nss-alertmanager` | `prom/alertmanager:v0.27.0` | **Restarting** |
| `nss-node-exporter` | `prom/node-exporter:v1.8.2` | Up 33h |
| `nss-cadvisor` | `gcr.io/cadvisor/cadvisor:v0.49.1` | Up 33h (healthy) |
| `nss-postgres-exporter` | `prometheuscommunity/postgres-exporter:v0.16.0` | Up 33h |
| `prometheus` | `prom/prometheus:latest` | Up 33h |
| `promtail` | `grafana/promtail:latest` | Up 33h |
| `blackbox-exporter` | `prom/blackbox-exporter:latest` | Up 33h |

### Eventing / streaming
| Container | Image | Status |
| --- | --- | --- |
| `kafka` | `apache/kafka:3.7.0` | Up 33h |
| `fluvio-sc` / `fluvio-spu` | `infinyon/fluvio:latest` | Up 33h |
| `dapr-placement` | `daprio/dapr:latest` | Up 33h |
| `temporal-ui` | `temporalio/ui:2.26.2` | Up 33h |

### Utility / scratch
| Container | Image | Status |
| --- | --- | --- |
| `intelligent_agnesi` | `alpine:latest` | Up 31h |
| `pedantic_ganguly` | `alpine:latest` | Up 32h |
| `6d9c397c8f88_twenty-db` | `postgres:16` | Up 33h (healthy) |

## 5. Listening Ports (selected)

| Port | Bound to | Likely service |
| --- | --- | --- |
| 22 | LAN/TS | SSH |
| 3306 | 127.0.0.1 | MySQL |
| 5433 | 127.0.0.1 | Postgres (secondary) |
| 6379 | 127.0.0.1 | Redis |
| 8081 | 127.0.0.1 | app / proxy |
| 8101–8106 | 127.0.0.1 | agent services |
| 18000 / 18001 | 0.0.0.0 | agent/worker ports |
| 18789 | 0.0.0.0 | service port |
| 3300, 6800–6811, 7443 | 192.168.1.157 | NewFire agent/API endpoints |
| 5901 | 127.0.0.1 | VNC |
| 43349, 43163, 41849, 49741, 50005, 51955 | 0.0.0.0 | misc/runtime |

> Many ports are bound to the LAN IP only; external exposure is via the
> `cloudflared` tunnel. Verify the tunnel config before assuming public reachability.

## 6. Project / Data Directories (`/home/newwaveclaw`)

| Path | Purpose |
| --- | --- |
| `obsidian-vault/` | Obsidian notes (daily notes, infra, monitoring, projects) |
| `newfire/`, `openhands/`, `openclaw/`, `deepagents/`, `opencode/` | Agent / platform codebases |
| `healthpoint/` | Healthpoint platform (extensive docs + code) |
| `mojaloop/`, `farmconnect/`, `lanai/`, `paperclip/`, `zrok2/`, `n8n/` | Project workspaces |
| `monitoring/`, `docker/`, `apisix-conf/` | Infra config (incl. `MONITORING-SETUP.md`) |
| `litellm-venv/`, `go/`, `builds/`, `projects/` | Toolchains & builds |
| `backups/`, `homelab-backup/` | Backup stores |
| `scripts/`, `bin/`, `logs/` | Ops scripts & logs |

## 7. Secrets & Security (provision before takeover)

- **GitHub PAT** in `/home/newwaveclaw/.git-credentials` — rotate on handover.
- **`.env`** files exist in project dirs — never commit; reconstruct from a secret manager.
- **SSH keys** in `/home/newwaveclaw/.ssh/` — transfer or re-issue to new operator.
- **Cloudflare Tunnel** token is in the `cloudflared` container env — re-create tunnel on handover.
- **Keycloak / Postgres / Minio** credentials live in compose files & `.env` — re-key on takeover.
- This doc excludes all secrets by design (see repo `.gitignore`).

## 8. Known Issues at Snapshot

1. `newfire-app` container is **restart-looping** — inspect `docker logs newfire-app`.
2. `nss-alertmanager` container is **restart-looping** — check config/volume mount.
3. Root filesystem is at **88%** usage (415G/492G) — prune Docker + archive backups.

## 9. Takeover Checklist

- [ ] Gain SSH access (key or password) to `newwaveclaw`.
- [ ] Join the Tailscale network (`tail3a833f.ts.net`) or LAN `192.168.1.0/24`.
- [ ] Clone this repo and read `machine-docs/dgx-spark.md` (inference lives there).
- [ ] Rotate GitHub PAT, Cloudflare tunnel token, and all DB/app credentials.
- [ ] Fix the two restart-looping containers (`newfire-app`, `nss-alertmanager`).
- [ ] Confirm `cloudflared` tunnel still points at the right upstreams.
- [ ] Free disk space (prune images, offload `backups/`).
