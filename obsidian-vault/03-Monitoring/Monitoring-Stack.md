# Monitoring Stack

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Grafana (port 3100)                   │
│              http://metrics.newfire.app                  │
└─────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Prometheus │ │    Loki     │ │   Jaeger    │
│  (port 9090)│ │ (port 3101) │ │ (port 16686)│
└─────────────┘ └─────────────┘ └─────────────┘
         │              │
         ▼              ▼
┌─────────────┐ ┌─────────────┐
│  cAdvisor   │ │ node_exporter│
│  (container)│ │  (host OS)   │
└─────────────┘ └─────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              Docker Daemon (via Docker socket)           │
└─────────────────────────────────────────────────────────┘
```

## Components

### Prometheus
- **Image:** `prom/prometheus:v2.55.0`
- **Port:** 9090
- **Config:** `/home/newwaveclaw/docker/observability/prometheus/prometheus.yml`
- **Alert Rules:** `/home/newwaveclaw/docker/observability/prometheus/alerts.yml`
- **Retention:** 15 days, 10GB

**Scrape Targets:**
- `dcgm-dgx-spark` - DGX Spark GPU metrics (100.88.112.5:9400)
- `prometheus` - Self-monitoring
- `cadvisor` - Container metrics
- `node` - Host OS metrics
- `postgres` - PostgreSQL metrics
- `nss-control` - NSS control service health

### Loki
- **Image:** `grafana/loki:3.2.0`
- **Port:** 3100
- **Config:** `/home/newwaveclaw/docker/observability/loki/loki-config.yml`
- **Retention:** 168 hours (7 days)
- **Rate Limit:** 10MB/sec ingestion

### Grafana
- **Image:** `grafana/grafana:11.3.0`
- **Port:** 3100 (host: 3399)
- **Config:** `/home/newwaveclaw/docker/observability/grafana/provisioning/`
- **Default User:** admin/admin

**Datasources:**
- Prometheus (default)
- Loki

### Alertmanager
- **Image:** `prom/alertmanager:latest`
- **Port:** 9093
- **Config:** Running with default config

### cAdvisor
- **Image:** `gcr.io/cadvisor/cadvisor:v0.49.1`
- **Purpose:** Container resource metrics
- **Network:** `newfire_shared`

### node_exporter
- **Image:** `prom/node-exporter:v1.8.2`
- **Purpose:** Host OS metrics (CPU, memory, disk, network)
- **Network:** `newfire_shared`
- **Mode:** `--path.rootfs=/host` (host filesystem)

## Logs

### Promtail
- **Image:** `grafana/promtail:3.2.0`
- **Purpose:** Collects Docker container logs and sends to Loki
- **Config:** `/home/newwaveclaw/docker/observability/promtail/promtail-config.yml`
- **Labels:** container, stream, nss_role, sandbox_id

## Dashboards

### Pre-configured Dashboards
- **Project Exordium Single Pane of Glass**
  - URL: `http://100.79.80.119:3100/d/exordium-v1/project-exordium-e28094-single-pane-of-glass`
  - Shows: DGX, Minisforum, OpenHands logs

### Custom Dashboards
(To be created in Grafana UI)
- Docker container metrics
- CPU/GPU usage
- Memory usage
- Network throughput
- Service health

## Alert Rules

**File:** `/home/newwaveclaw/docker/observability/prometheus/alerts.yml`

### Active Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighCPUUsage | CPU > 80% for 5m | warning |
| HighGPUPerformance | GPU > 80% for 5m | warning |
| HighMemoryUsage | Memory > 85% for 5m | warning |
| ContainerCPUUsage | Container CPU > 80% for 5m | warning |
| ContainerMemoryUsage | Container memory > 85% for 5m | warning |

## Configuration Files

| File | Purpose |
|------|---------|
| `/home/newwaveclaw/docker/observability/prometheus/prometheus.yml` | Prometheus config |
| `/home/newwaveclaw/docker/observability/prometheus/alerts.yml` | Alert rules |
| `/home/newwaveclaw/docker/observability/loki/loki-config.yml` | Loki config |
| `/home/newwaveclaw/docker/observability/promtail/promtail-config.yml` | Promtail config |
| `/home/newwaveclaw/docker/observability/grafana/provisioning/datasources/*.yml` | Grafana datasources |

## Troubleshooting

### Prometheus not scraping
```bash
# Check Prometheus logs
docker logs prometheus --tail 50

# Check target status
curl http://localhost:9090/api/v1/targets

# Check alert rules
curl http://localhost:9090/api/v1/rules
```

### Loki rate limiting
```bash
# Check Loki logs for 429 errors
docker logs loki --tail 50

# Increase rate limit in loki-config.yml
limits_config:
  max_ingestion_rate: 10485760  # 10MB/sec
```

### Grafana authentication
```bash
# Reset admin password
docker exec -it grafana grafana-cli admin reset-admin-password <new-password>

# Or via API
curl -X POST http://localhost:3100/api/admin/users/reset-password \
  -H "Content-Type: application/json" \
  -d '{"oldPassword":"admin","newPassword":"new-password"}'
```
