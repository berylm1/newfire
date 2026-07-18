# Project Status

## Overview

**Project:** NewFire Infrastructure  
**Last Updated:** 2026-07-01  
**Status:** Active Development

## Current State

### Services Status (2026-07-01)

| Service | Container | Status | Notes |
|---------|-----------|--------|-------|
| **Database** | | | |
| PostgreSQL | farmer-postgres | ✅ Up | Main database |
| PostgreSQL (app) | newfire-db | ✅ Up | Application database |
| MySQL (mojaloop) | mojaloop-mysql | ✅ Up | Mojaloop ledger |
| **Cache/Queue** | | | |
| Redis | redis | ✅ Up | Cache and sessions |
| Kafka | kafka | ✅ Up | Message broker |
| **API/Proxy** | | | |
| APISIX | apisix | ✅ Up | API gateway |
| **Message/Event** | | | |
| Fluvio SC | fluvio-sc | ✅ Up | Stream controller |
| Fluvio SPU | fluvio-spu | ✅ Up | Stream processor |
| **Identity/Auth** | | | |
| Keycloak | keycloak | ✅ Up | Identity provider |
| Permify | permify | ✅ Up | Authorization |
| Vault | vault | ✅ Up | Secrets management |
| **Workflow** | | | |
| Temporal | temporal | ✅ Up | Workflow engine |
| Temporal UI | temporal-ui | ✅ Up | Workflow UI |
| **Search/Observability** | | | |
| OpenSearch | opensearch | ✅ Up | Search engine |
| OpenSearch Dashboards | opensearch-dashboards | ✅ Up | Search UI |
| Prometheus | prometheus | ✅ Up | Metrics collection |
| Grafana | grafana | ✅ Up | Dashboards |
| Loki | loki | ✅ Up | Log aggregation |
| Jaeger | jaeger | ✅ Up | Tracing |
| **Other** | | | |
| Dapr Placement | dapr-placement | ✅ Up | Service mesh |
| TigerBeetle | tigerbeetle | ✅ Up | Accounting |
| Mojaloop CL | mojaloop | ✅ Up | Payment ledger |
| OpenHands | openhands-app | ✅ Up | AI agent |
| PostgreSQL Bouncer | pgbouncer | ✅ Up | Connection pooling |
| Legal Qdrant | legal-qdrant | ✅ Up | Vector DB |
| NSS Control | nss-control | ✅ Up | NSS service |
| NSS Portal | nss-portal | ✅ Up | NSS portal |
| Newfire Backend | newfire-backend | ✅ Up | Backend service |

### Network Configuration

**Primary Network:** `app-net` (13+ containers)

**Cloudflare Tunnel (newfire-prod):**
- `newfire.app` → `localhost:4000`
- `app.newfire.app` → `localhost:3000`
- `dev.newfire.app` → `localhost:4000`
- `api.newfire.app` → `localhost:9080`
- `dash.newfire.app` → `localhost:3100`
- `files.newfire.app` → `localhost:18789`
- `metrics.newfire.app` → `localhost:3399`
- `agent.newfire.app` → `localhost:32785` (OpenHands agent server)

### Monitoring

**Grafana:** `http://localhost:3100` (admin/admin)  
**Prometheus:** `http://localhost:9090`  
**Loki:** `http://localhost:3101`  
**Jaeger:** `http://localhost:16686`

### Alert Configuration

**Alert Manager:** Running on port 9093  
**Alert Rules:** `/home/newwaveclaw/docker/observability/prometheus/alerts.yml`

**Active Alerts:**
- High CPU Usage (>80% for 5m)
- High GPU Utilization (>80%)
- High Memory Usage (>85% for 5m)
- Container CPU Usage (>80% for 5m)
- Container Memory Usage (>85% for 5m)

## Recent Changes

### 2026-07-01
- ✅ Fixed TigerBeetle (added --privileged flag)
- ✅ Fixed Fluvio (two-container setup: SC + SPU)
- ✅ Fixed APISIX (increased memory to 1G)
- ✅ Fixed Kafka (increased memory to 2G)
- ✅ Set up MySQL for Mojaloop
- ✅ Connected all services to app-net
- ✅ Added Dapr Placement container
- ✅ Set up Cloudflare tunnel for metrics.newfire.app
- ✅ Configured Prometheus alert rules
- ⚠️ OpenHands needs AGENT_SERVER_URL fix

## TODO

- [ ] Fix OpenHands agent server URL configuration
- [ ] Verify all services are accessible via Cloudflare
- [ ] Set up Grafana dashboards for Docker metrics
- [ ] Configure alert notifications (email/Slack)
- [ ] Document service dependencies
