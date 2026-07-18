# Monitoring & Alerting System

## Overview

Comprehensive monitoring for all systems:
- **Minisforum**: Docker containers, CPU, memory, disk, network
- **DGX Spark**: GPU metrics, memory, disk, llama-server status
- **Agent-Canvas**: Health, context window, errors
- **OpenHands**: API health, error rates
- **Cloudflare Tunnel**: Connectivity

## Architecture

```
Internet
    ↓
Cloudflare Tunnel (app.newfire.app)
    ↓
Minisforum (100.79.80.119)
    ├── Prometheus (port 9090) - Metrics collection
    ├── Grafana (port 3399) - Visualization
    ├── Alertmanager (port 9093) - Alert routing
    ├── Loki (port 3100) - Log aggregation
    ├── cAdvisor - Container metrics
    ├── Node Exporter - System metrics
    └── Promtail - Log shipping
    ↓
DGX Spark (100.88.112.5)
    └── DCGM Exporter (port 9400) - GPU metrics
```

## Setup Instructions

### 1. Configure Alert Notifications

Run the setup script:
```bash
chmod +x /home/newwaveclaw/docker/setup-alerts.sh
/home/newwaveclaw/docker/setup-alerts.sh
```

This will prompt you for:
- Telegram Bot Token (from @BotFather)
- Telegram Chat ID (from @userinfobot)
- Email address (optional)

### 2. Update Email Password (if using email)

Edit the alertmanager config:
```bash
nano /home/newwaveclaw/docker/observability/alertmanager/alertmanager.yml
```

Find `PLACEHOLDER_EMAIL_PASSWORD` and replace with your Gmail app password.

### 3. Restart Services

```bash
cd /home/newwaveclaw/docker/observability
sudo docker compose down
sudo docker compose up -d
```

### 4. Verify Monitoring

Check Grafana dashboard:
- URL: http://127.0.0.1:3399
- Username: admin
- Password: (from /home/newwaveclaw/docker/observability/.env)

Look for "All Systems Monitor" dashboard.

## Dashboard Sections

### System Overview
- Minisforum CPU usage (gauge)
- DGX Spark GPU utilization (stat)
- Agent-Canvas memory (stat)
- OpenHands error rate (stat)

### Container Metrics
- Container CPU usage (timeseries)
- Container memory usage (timeseries)

### Network & Requests
- Network traffic (RX/TX)
- HTTP requests by service

### DGX Spark GPU Metrics
- GPU utilization
- GPU memory usage
- GPU temperature

### Alerts
- Active alerts count
- Recent errors (from Loki)

## Alert Rules

| Alert | Condition | Severity | Notification |
|-------|-----------|----------|--------------|
| OpenHandsDown | Container down > 1m | critical | Telegram + Email |
| OpenHandsHighErrorRate | >10% errors > 5m | warning | Telegram + Email |
| LLMModelDown | DGX Spark down > 2m | critical | Telegram + Email |
| CloudflaredTunnelDown | Tunnel down > 1m | critical | Telegram + Email |
| HighMemoryUsage | >8GB process memory > 5m | warning | Telegram + Email |
| NodeDown | Node exporter down > 2m | warning | Telegram + Email |
| DiskSpaceLow | <10% disk > 5m | warning | Telegram + Email |
| HighCPU | >90% CPU > 10m | warning | Telegram + Email |

## Persistent Monitoring

### Minisforum
- Prometheus scrapes all services every 30s
- cAdvisor collects container metrics
- Node Exporter collects system metrics
- Promtail ships logs to Loki
- Cron job checks agent-canvas health every 5m

### DGX Spark
- DCGM Exporter runs as Docker container
- Collects GPU metrics (utilization, memory, temperature)
- Scraped by Prometheus on Minisforum

## Troubleshooting

### Alerts not sending
1. Check alertmanager logs: `sudo docker logs nss-alertmanager`
2. Verify Telegram bot token: message @BotFather
3. Test Telegram: `curl -X POST https://api.telegram.org/bot<TOKEN>/sendMessage -d "chat_id=<ID>&text=test"`

### Grafana dashboard empty
1. Wait 2-3 minutes for metrics to populate
2. Check Prometheus targets: http://127.0.0.1:9090/targets
3. Verify container scraping: look for "agent-canvas" and "dcg" jobs

### DGX Spark not showing
1. Verify DCGM exporter is running: `ssh 100.88.112.5 "docker ps | grep dcgm"`
2. Check firewall: port 9400 must be accessible from Minisforum
3. Test connection: `curl http://100.88.112.5:9400/metrics`

## File Locations

- Prometheus config: `/home/newwaveclaw/docker/observability/prometheus/prometheus.yml`
- Alertmanager config: `/home/newwaveclaw/docker/observability/alertmanager/alertmanager.yml`
- Grafana dashboards: `/home/newwaveclaw/docker/observability/grafana/provisioning/dashboards-data/`
- Monitoring logs: `/home/newwaveclaw/docker/monitoring.log`
- Alert setup script: `/home/newwaveclaw/docker/setup-alerts.sh`

## Customization

### Add new alert rule
Edit `/home/newwaveclaw/docker/observability/prometheus/alerts.yml` and add to appropriate group.

### Add new scrape target
Edit `/home/newwaveclaw/docker/observability/prometheus/prometheus.yml` and add new `scrape_config`.

### Customize dashboard
1. Open Grafana dashboard
2. Click "Edit" button
3. Modify panels
4. Click "Save"
