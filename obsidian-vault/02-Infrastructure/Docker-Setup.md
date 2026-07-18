# Docker Setup

## Compose Files

### Main Stack
**Location:** `/home/newwaveclaw/farmer-data-collection/docker-compose.yml`

**Services:** apisix, n8n, redis, minio, postgrest, tigerbeetle

### Fluvio Stack
**Location:** `/home/newwaveclaw/farmer-data-collection/docker-compose-fluvio.yml`

**Services:** fluvio-sc, fluvio-spu

### Observability Stack
**Location:** `/home/newwaveclaw/docker/observability/docker-compose.yml`

**Services:** prometheus, cadvisor, node_exporter, postgres_exporter, loki, promtail, grafana

## Container Images

| Service | Image | Version |
|---------|-------|---------|
| APISIX | apache/apisix | 3.7.0-debian |
| Kafka | bitnami/kafka | 3.7.0 |
| TigerBeetle | ghcr.io/tigerbeetle/tigerbeetle | 0.16.0 |
| Fluvio SC/SPU | infinyon/fluvio | latest |
| Dapr Placement | daprio/dapr | 1.13.0 |
| Mojaloop CL | mojaloop/central-ledger | snapshot |
| MySQL | mysql | 8.0 |
| Prometheus | prom/prometheus | v2.55.0 |
| Grafana | grafana/grafana | 11.3.0 |
| Loki | grafana/loki | 3.2.0 |
| Jaeger | jaegertracing/jaeger | latest |
| OpenSearch | opensearchproject/opensearch | latest |
| Keycloak | quay.io/keycloak/keycloak | latest |
| Permify | permify/permify | latest |
| Vault | hashicorp/vault | latest |
| Temporal | temporalio/auto-setup | latest |
| cAdvisor | gcr.io/cadvisor/cadvisor | v0.49.1 |
| node_exporter | prom/node-exporter | v1.8.2 |

## Memory Limits

| Service | Limit | Notes |
|---------|-------|-------|
| APISIX | 1G | Increased from 512M |
| Kafka | 2G | Increased from 1G |
| Prometheus | 8G (host limit) | GOMEMLIMIT set |

## Critical Notes

### TigerBeetle
- **Requires `--privileged` flag** for io_uring access
- Data volume: `tigerbeetle-data`
- Format command: `format --cluster=0 --replica=0 --replica-count=1 /data/0_0.tigerbeetle`
- Start command: `start --addresses=0.0.0.0:3000 /data/0_0.tigerbeetle`

### Fluvio
- Two-container setup: SC (streaming controller) + SPU (streaming processing unit)
- SC port: 9103
- SPU ports: 9110 (public), 9111 (private)
- Both on `app-net` network

### Kafka
- Uses `bitnami/kafka:3.7.0` with uid 1000
- Data dir: `/bitnami/kafka` (ownership: 1000:1000)
- Environment: KAFKA_NODE_ID=1, KAFKA_PROCESS_ROLES=broker,controller

### Mojaloop
- Requires MySQL (mysql2 dialect), NOT PostgreSQL
- Config file: `/home/newwaveclaw/farmer-data-collection/mojaloop/.CLEDGrc`
- Environment prefix: `CLEDG_`
- Proxy cache must be disabled: `CLEDG_PROXY_CACHE_ENABLED=false`

### OpenHands
- Frontend: port 3000 (external) → 8000 (internal)
- Agent server: port 32785 (internal only)
- Environment: `AGENT_SERVER_URL=http://localhost:18000` (needs fix)
- NOVNC: port 8002

## Common Commands

```bash
# Check all containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check network connections
docker network inspect app-net

# Restart a specific service
docker restart <container-name>

# View logs
docker logs <container-name> --tail 50

# Check resource usage
docker stats --no-stream

# Remove stopped containers
docker container prune -f
```

## Troubleshooting

### Container won't start
1. Check logs: `docker logs <container>`
2. Check ports: `docker port <container>`
3. Check network: `docker network inspect app-net`
4. Check resources: `docker stats`

### Port conflicts
```bash
# Find what's using a port
sudo lsof -i :<port>

# Or
ss -tlnp | grep :<port>
```

### Memory issues
```bash
# Check container memory
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"

# Increase limit
docker update --memory=<limit> <container>
```
