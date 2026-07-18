# Troubleshooting Guide

## Service-Specific Issues

### TigerBeetle
**Problem:** Container starts but fails with io_uring errors  
**Solution:** Add `--privileged` flag  
```bash
docker rm -f tigerbeetle
docker run -d --name tigerbeetle --privileged --network app-net -v tigerbeetle-data:/data ghcr.io/tigerbeetle/tigerbeetle:0.16.0 start --addresses=0.0.0.0:3000 /data/0_0.tigerbeetle
```

**Problem:** Data volume not formatted  
**Solution:** Format before starting  
```bash
docker run --rm --privileged -v tigerbeetle-data:/data ghcr.io/tigerbeetle/tigerbeetle:0.16.0 format --cluster=0 --replica=0 --replica-count=1 /data/0_0.tigerbeetle
```

### Fluvio
**Problem:** SPU can't bind to addresses  
**Solution:** Use `0.0.0.0` for public/private addresses in config  
```yaml
environment:
  FLUVIO_SPU_PUBLIC_ADDRESS: 0.0.0.0:9010
  FLUVIO_SPU_PRIVATE_ADDRESS: 0.0.0.0:9011
```

### Mojaloop
**Problem:** ECONNREFUSED on startup  
**Solution:** 
1. Use MySQL (not PostgreSQL)
2. Set correct environment variables with `CLEDG_` prefix
3. Disable proxy cache: `CLEDG_PROXY_CACHE_ENABLED=false`
4. Create `.CLEDGrc` config file in container

**Problem:** Container exits immediately  
**Solution:** Check logs and verify database connection  
```bash
docker logs mojaloop --tail 100
```

### APISIX
**Problem:** `sed: cannot rename ... Device or resource busy`  
**Solution:** Don't bind-mount config files, use standalone mode  
```bash
docker run -d --name apisix -e APISIX_STAND_ALONE=true apache/apisix:3.7.0-debian
```

**Problem:** Port already in use  
**Solution:** Change host port mapping  
```bash
docker run -p 9444:9443 ...  # Use 9444 instead of 9443
```

### Kafka
**Problem:** Permission denied writing to data directory  
**Solution:** Fix ownership to uid 1000  
```bash
sudo chown -R 1000:1000 /path/to/kafka-data
```

### OpenHands
**Problem:** Blank white screen, 401/404 errors  
**Solution:**
1. Verify container is running: `docker ps | grep openhands`
2. Check agent server URL: `AGENT_SERVER_URL=http://localhost:18000`
3. Expose port 18000: `-p 18000:18000`
4. Update cloudflared config for `agent.newfire.app`

**Problem:** Agent server not responding  
**Solution:** Check internal port (32785) and expose correctly

## Monitoring Issues

### Prometheus
**Problem:** Alerts not firing  
**Solution:**
1. Check rule files: `curl http://localhost:9090/api/v1/rules`
2. Verify alertmanager is configured
3. Check alert state: `curl http://localhost:9090/api/v1/alerts`

**Problem:** Targets not scraping  
**Solution:**
1. Check target status: `curl http://localhost:9090/api/v1/targets`
2. Verify network connectivity
3. Check Prometheus logs: `docker logs prometheus --tail 50`

### Loki
**Problem:** 429 Too Many Requests  
**Solution:** Increase rate limit in `loki-config.yml`  
```yaml
limits_config:
  max_ingestion_rate: 10485760  # 10MB/sec
```

**Problem:** Logs not appearing  
**Solution:**
1. Check Promtail logs: `docker logs promtail --tail 50`
2. Verify Docker socket is mounted
3. Check Loki ingestion endpoint: `curl http://localhost:3100/ready`

### Grafana
**Problem:** Authentication failed  
**Solution:**
1. Reset password: `docker exec -it grafana grafana-cli admin reset-admin-password new-password`
2. Check datasources: `/home/newwaveclaw/docker/observability/grafana/provisioning/datasources/`

**Problem:** Dashboards not loading  
**Solution:**
1. Check browser console for errors
2. Verify datasources are configured
3. Check Grafana logs: `docker logs grafana --tail 50`

## Network Issues

### Container can't reach another container
**Solution:** Ensure both containers are on same network  
```bash
docker network connect app-net <container>
```

### Port already in use
**Solution:** Find and stop conflicting service  
```bash
sudo lsof -i :<port>
docker stop <container>
```

### Cloudflare tunnel not working
**Solution:**
1. Check tunnel status: `cloudflared tunnel list`
2. Verify config file: `/home/newwaveclaw/.cloudflared/config.yml`
3. Restart service: `sudo systemctl restart cloudflared`
4. Check logs: `sudo journalctl -u cloudflared --since "1 hour ago"`

## Resource Issues

### Out of memory
**Solution:** Increase memory limit  
```bash
docker update --memory=2g <container>
```

### Disk space full  
**Solution:** Clean up old data  
```bash
docker system prune -a
sudo rm -rf /var/lib/docker/tmp/*
```

### CPU throttling
**Solution:** Check CPU limits and increase if needed  
```bash
docker update --cpus=4 <container>
```

## Emergency Procedures

### Stop all containers
```bash
docker stop $(docker ps -q)
```

### Start all containers
```bash
docker start $(docker ps -a -q)
```

### Full restart of monitoring stack
```bash
cd /home/newwaveclaw/docker/observability
docker compose down
docker compose up -d
```

### Full restart of main stack
```bash
cd /home/newwaveclaw/farmer-data-collection
docker compose down
docker compose up -d
```

## Getting Help

1. Check [[Quick-Reference]] for common commands
2. Review [[Docker-Setup]] for configuration details
3. See [[Monitoring-Stack]] for observability setup
4. Review [[Project-Status]] for current state

## Logs Locations

| Component | Log Location |
|-----------|--------------|
| Docker containers | `docker logs <container>` |
| Cloudflare tunnel | `sudo journalctl -u cloudflared` |
| System services | `sudo journalctl -u <service>` |
| Prometheus | `/prometheus` (inside container) |
| Loki | `/loki` (inside container) |
| Grafana | `/var/lib/grafana` (inside container) |
