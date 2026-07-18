# Quick Reference

## Essential Commands

### Docker
```bash
# List all containers
docker ps -a

# Check specific container
docker inspect <container>

# View logs
docker logs <container> --tail 100

# Restart container
docker restart <container>

# Stop container
docker stop <container>

# Remove container
docker rm <container>

# Execute command in container
docker exec -it <container> /bin/bash

# Check resource usage
docker stats --no-stream

# Network inspect
docker network inspect app-net
```

### System
```bash
# Check services
sudo systemctl status <service>

# Restart service
sudo systemctl restart <service>

# Check ports
sudo lsof -i :<port>
ss -tlnp | grep :<port>

# Check disk usage
df -h
du -sh /var/lib/docker

# Check memory
free -h
```

### Cloudflare Tunnel
```bash
# Check tunnel status
cloudflared tunnel list

# Check tunnel info
cloudflared tunnel info <tunnel-name>

# View logs
sudo journalctl -u cloudflared --since "1 hour ago"
```

### Monitoring
```bash
# Prometheus
curl http://localhost:9090/api/v1/targets
curl http://localhost:9090/api/v1/rules

# Loki
curl http://localhost:3100/ready

# Grafana
curl http://localhost:3100/api/health

# Alertmanager
curl http://localhost:9093/api/v2/status
```

## Service URLs

| Service | URL | Port |
|---------|-----|------|
| Grafana | http://localhost:3399 | 3399 |
| Prometheus | http://localhost:9090 | 9090 |
| Loki | http://localhost:3101 | 3101 |
| Jaeger | http://localhost:16686 | 16686 |
| APISIX | http://localhost:9080 | 9080 |
| Keycloak | http://localhost:8080 | 8080 |
| Vault | http://localhost:8200 | 8200 |
| Temporal | http://localhost:7233 | 7233 |
| Dapr Placement | http://localhost:50005 | 50005 |
| TigerBeetle | http://localhost:3000 | 3000 |
| Mojaloop | http://localhost:8444 | 8444 |
| OpenHands | http://openhands.newfire.app | 8000 (internal) |

## Cloudflare Tunnel

**Running as Docker container:** `cloudflared` (network: `host`)

**Why host network:** Cloudflared needs to access localhost services (agent-canvas on 3001, Grafana on 3399) and Docker containers (prometheus, loki) on shared networks.

**Config location:** `/home/newwaveclaw/.cloudflared/config.yml` (mounted into container at `/etc/cloudflared/`)

**Credentials path in container:** `/etc/cloudflared/d0f9998f-73ee-4c64-a259-0f09a65d9856.json`

## Service Endpoints

| Service | Port | Cloudflare Route |
|---------|------|------------------|
| Agent Canvas (frontend) | localhost:3001 | openhands.newfire.app |
| Agent Canvas (agent server) | localhost:18000 | agent.newfire.app |
| Grafana | localhost:3399 | metrics.newfire.app |
| Prometheus | localhost:9090 | internal only |
| Loki | localhost:3101 | internal only |
| DGX Spark DCGM | 100.88.112.5:9400 | scrape target |

## Prometheus Targets

| Job | Target | Status |
|-----|--------|--------|
| dcgm-dgx-spark | 100.88.112.5:9400 | ✅ up |
| node | localhost:9100 | ⚠️ down (need to verify) |
| cadvisor | localhost:8080 | ⚠️ down |
| prometheus | localhost:9090 | ✅ up |

## Environment Variables

### OpenHands
- `AGENT_SERVER_URL=http://localhost:18000` (needs fix)
- `NOVNC_PORT=8002`
- `LLM_API_KEY=***`
- `LLM_BASE_URL=http://100.88.112.5:8090/v1`

### Mojaloop
- `CLEDG_DATABASE_HOST=mojaloop-mysql`
- `CLEDG_DATABASE_PORT=3306`
- `CLEDG_DATABASE_USER=central_ledger`
- `CLEDG_DATABASE_PASSWORD=***`
- `CLEDG_DATABASE_SCHEMA=central_ledger`
- `CLEDG_PROXY_CACHE_ENABLED=false`
- `CLEDG_CACHE_ENABLED=false`

## Common Issues & Fixes

### Container won't start
1. Check logs: `docker logs <container>`
2. Check ports: `sudo lsof -i :<port>`
3. Check resources: `docker stats`
4. Restart: `docker restart <container>`

### Port conflict
```bash
# Find what's using the port
sudo lsof -i :<port>

# Stop the conflicting service
docker stop <container>

# Or change the port mapping
docker run -p <new-port>:<container-port> ...
```

### Memory limit exceeded
```bash
# Check current limit
docker inspect <container> --format '{{.HostConfig.MemoryLimit}}'

# Increase limit
docker update --memory=<new-limit> <container>
```

### Network connectivity
```bash
# Check network
docker network inspect app-net

# Connect container to network
docker network connect app-net <container>

# Disconnect from network
docker network disconnect app-net <container>
```

## File Locations

| Component | Path |
|-----------|------|
| Docker compose (main) | `/home/newwaveclaw/farmer-data-collection/docker-compose.yml` |
| Docker compose (fluvio) | `/home/newwaveclaw/farmer-data-collection/docker-compose-fluvio.yml` |
| Docker compose (observability) | `/home/newwaveclaw/docker/observability/docker-compose.yml` |
| Prometheus config | `/home/newwaveclaw/docker/observability/prometheus/prometheus.yml` |
| Prometheus alerts | `/home/newwaveclaw/docker/observability/prometheus/alerts.yml` |
| Loki config | `/home/newwaveclaw/docker/observability/loki/loki-config.yml` |
| Grafana provisioning | `/home/newwaveclaw/docker/observability/grafana/provisioning/` |
| Cloudflare config | `/home/newwaveclaw/.cloudflared/config.yml` |
| Cloudflare credentials | `/home/newwaveclaw/.cloudflared/<tunnel-id>.json` |
| Obsidian vault | `/home/newwaveclaw/obsidian-vault/` |

## Contact & Resources

- **Project:** NewFire Infrastructure
- **Documentation:** [[Project-Status]], [[Infrastructure-Overview]]
- **Monitoring:** [[Monitoring-Stack]], [[Alerts-Configuration]]
- **Docker:** [[Docker-Setup]]
