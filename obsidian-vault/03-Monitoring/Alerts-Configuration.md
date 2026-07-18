# Alerts Configuration

## Alert Manager

**Service:** nss-alertmanager  
**Port:** 9093  
**Status:** ✅ Running

## Alert Rules

**File:** `/home/newwaveclaw/docker/observability/prometheus/alerts.yml`

### Rule Groups

#### system_alerts

**HighCPUUsage**
- **Expression:** `100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80`
- **Duration:** 5m
- **Severity:** warning
- **Summary:** "High CPU usage on {{ $labels.instance }}"
- **Description:** "CPU usage is above 80% (current value: {{ $value }}%)"

**HighGPUPerformance**
- **Expression:** `(dcgpUnreasonableUtilizationGauge / 100) > 0.8`
- **Duration:** 5m
- **Severity:** warning
- **Summary:** "High GPU utilization on DGX Spark"
- **Description:** "GPU utilization is above 80%"

**HighMemoryUsage**
- **Expression:** `(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85`
- **Duration:** 5m
- **Severity:** warning
- **Summary:** "High memory usage on {{ $labels.instance }}"
- **Description:** "Memory usage is above 85%"

**ContainerCPUUsage**
- **Expression:** `rate(container_cpu_usage_seconds_total[5m]) * 100 > 80`
- **Duration:** 5m
- **Severity:** warning
- **Summary:** "High CPU usage for container {{ $labels.name }}"
- **Description:** "Container {{ $labels.name }} CPU usage is above 80%"

**ContainerMemoryUsage**
- **Expression:** `(container_memory_usage_bytes / container_memory_max_usage_bytes) * 100 > 85`
- **Duration:** 5m
- **Severity:** warning
- **Summary:** "High memory usage for container {{ $labels.name }}"
- **Description:** "Container {{ $labels.name }} memory usage is above 85%"

## Notification Channels

### Current Configuration
- **Alertmanager:** Running with default config
- **Notifications:** Not yet configured (no email/Slack/webhook)

### Recommended Notifications

#### Email (SMTP)
```yaml
# In alertmanager.yml
route:
  receiver: 'email-notifications'

receivers:
  - name: 'email-notifications'
    email_configs:
      - to: 'your-email@example.com'
        from: 'alerts@newfire.app'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'your-email@gmail.com'
        auth_password: 'your-app-password'
```

#### Slack
```yaml
route:
  receiver: 'slack-notifications'

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.description }}'
```

#### Webhook (for AI agent)
```yaml
route:
  receiver: 'webhook-notifications'

receivers:
  - name: 'webhook-notifications'
    webhook_configs:
      - url: 'http://localhost:8080/alerts'
        send_resolved: true
```

## Testing Alerts

### Manual Alert Test
```bash
# Send test alert via Prometheus API
curl -X POST http://localhost:9090/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "TestAlert",
          "severity": "warning"
        },
        "annotations": {
          "summary": "Test alert",
          "description": "This is a test alert"
        }
      }
    ]
  }'
```

### Check Alert State
```bash
# Check firing alerts
curl http://localhost:9090/api/v1/alerts

# Check alertmanager state
curl http://localhost:9093/api/v2/status
```

## Alert Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| **critical** | Service down, data loss risk | Immediate |
| **warning** | High resource usage, degradation | Within 1 hour |
| **info** | Informational, capacity planning | Next business day |

## Current Alert Status

**Last Updated:** 2026-07-01

| Alert | State | Since | Instance |
|-------|-------|-------|----------|
| HighCPUUsage | - | - | - |
| HighGPUPerformance | - | - | - |
| HighMemoryUsage | - | - | - |
| ContainerCPUUsage | - | - | - |
| ContainerMemoryUsage | - | - | - |

(_- = No active alerts_

## TODO

- [ ] Configure email notifications
- [ ] Configure Slack notifications
- [ ] Set up webhook for AI agent
- [ ] Test alert delivery
- [ ] Document incident response procedures
- [ ] Set up alert routing by severity
