# Infrastructure Overview

## Server Architecture

### Machines

| Machine | IP | Purpose |
|---------|-----|---------|
| Minisforum (this host) | 100.79.80.119 | Main orchestration, monitoring, services |
| DGX Spark | 100.88.112.5 | GPU inference, DCGM metrics |

### Network

- **Primary Network:** `app-net` (Docker bridge)
- **Secondary Network:** `newfire_shared` (observability stack)
- **Cloudflare Tunnel:** `newfire-prod` (tunnel ID: d0f9998f-73ee-4c64-a259-0f09a65d9856)

### Cloudflare Tunnel Configuration

**Config File:** `/home/newwaveclaw/.cloudflared/config.yml`

**Service Routes:**
```yaml
newfire.app        → localhost:4000
app.newfire.app    → localhost:3000
dev.newfire.app    → localhost:4000
api.newfire.app    → localhost:9080
dash.newfire.app   → localhost:3100
files.newfire.app  → localhost:18789
metrics.newfire.app→ localhost:3399
agent.newfire.app  → localhost:32785
```

### Storage

- **CephFS:** Shared storage between Minisforum and DGX Spark
- **Docker Volumes:**
  - `prometheus_data` - Prometheus metrics
  - `loki_data` - Loki logs
  - `grafana_data` - Grafana dashboards
  - `tigerbeetle-data` - TigerBeetle accounting data

## Service Topology

```
┌─────────────────────────────────────────────────────────┐
│                    Cloudflare Edge                       │
│                     (metrics.newfire.app)                │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  Cloudflare Tunnel                       │
│              (newfire-prod: d0f9998f-...)                │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Minisforum (100.79.80.119)            │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  APISIX  │  │  OpenHands│  │ Grafana  │              │
│  │  :9080   │  │  :3000   │  │  :3100   │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       │              │              │                    │
│  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐              │
│  │  Kafka   │  │  Temporal│  │ Prometheus│              │
│  │  :9092   │  │  :7233   │  │  :9090   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  Keycloak│  │  Permify │  │   Vault  │              │
│  │  :8080   │  │  :3476   │  │  :8200   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │PostgreSQL│  │   Redis  │  │ Fluvio SC│              │
│  │  :5432   │  │  :6379   │  │  :9103   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

## Port Reference

### External (via Cloudflare)
| Port | Service |
|------|---------|
| 4000 | Main app / dev portal |
| 3000 | OpenHands frontend |
| 9080 | APISIX API gateway |
| 3100 | Grafana dashboards |
| 18789 | WebDAV file sharing |
| 3399 | Metrics dashboard (Loki) |
| 32785 | OpenHands agent server API |

### Internal Services
| Port | Service |
|------|---------|
| 9090 | Prometheus |
| 9093 | Alertmanager |
| 3101 | Loki |
| 16686 | Jaeger UI |
| 50005 | Dapr Placement |
| 9103 | Fluvio SC |
| 9110/9111 | Fluvio SPU |
| 3000 | TigerBeetle |
| 8444 | Mojaloop Central Ledger |

## Docker Networks

### app-net
- **Purpose:** Main application network
- **Containers:** 20+ (all application services)
- **DNS:** Containers reachable by name

### newfire_shared
- **Purpose:** Observability stack
- **Containers:** prometheus, loki, grafana, cadvisor, node_exporter, postgres_exporter, promtail
