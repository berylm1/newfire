# APISIX Metering -- API Gateway for Third-Party DGX Access

## Purpose

Apache APISIX provides a production-grade API gateway in front of the DGX Spark inference endpoints. This enables:

- **Token-based metering**: Track and limit per-consumer token usage
- **API key management**: Issue and revoke keys for third-party consumers
- **Rate limiting**: Per-consumer and per-model request limits
- **GPU hour metering**: Track training workload usage
- **Observability**: Prometheus metrics for dashboards and alerting

This setup lets you safely expose DGX Spark inference to friends, collaborators, or applications while tracking usage and enforcing quotas.

---

## Phase 1: Install APISIX on Minisforum

### Step 1.1: Install APISIX via Docker

```bash
# SSH into the Minisforum
ssh newwaveclaw@192.168.1.157

# Run the APISIX quickstart (Docker-based)
curl -sL https://run.api7.ai/apisix/quickstart | sh
```

This starts two containers:
- `apisix`: The gateway on ports 9080 (HTTP) and 9443 (HTTPS)
- `etcd`: The configuration store on port 2379

### Step 1.2: Verify APISIX is Running

```bash
# Check containers
docker ps | grep apisix

# Test the admin API
curl -s http://127.0.0.1:9180/apisix/admin/routes \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" | jq .

# Test the gateway
curl -s http://127.0.0.1:9080/ -I
# Should return a 404 (no routes configured yet) -- that is expected
```

### Step 1.3: Change the Admin API Key

The default admin key is well-known. Change it immediately:

```bash
# Generate a secure admin key
NEW_ADMIN_KEY=$(openssl rand -hex 32)
echo "New APISIX admin key: $NEW_ADMIN_KEY"
echo "Save this key securely!"

# Edit the APISIX config
# If installed via quickstart, the config is at:
docker exec -it apisix cat /usr/local/apisix/conf/config.yaml

# Update the admin key in the config
# Find the deployment.admin.admin_key section and update:
docker exec -it apisix sh -c "
sed -i 's/edd1c9f034335f136f87ad84b625c8f1/${NEW_ADMIN_KEY}/' \
  /usr/local/apisix/conf/config.yaml
"

# Reload APISIX
docker exec -it apisix apisix reload

# Test with the new key
curl -s http://127.0.0.1:9180/apisix/admin/routes \
  -H "X-API-KEY: ${NEW_ADMIN_KEY}" | jq .
```

For subsequent commands, we use `$APISIX_ADMIN_KEY` as a placeholder:
```bash
export APISIX_ADMIN_KEY="${NEW_ADMIN_KEY}"
```

---

## Phase 2: Token-Based Metering for Inference

### Step 2.1: Create the DGX Inference Route

This route proxies inference requests to the DGX Spark and applies AI-specific plugins for token metering.

```bash
# Create the metered inference route
curl -X PUT http://127.0.0.1:9180/apisix/admin/routes/dgx-inference-metered \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "/v1/chat/completions",
    "name": "dgx-inference-metered",
    "desc": "Metered access to DGX Spark inference",
    "methods": ["POST"],
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "192.168.1.158:8001": 3,
        "192.168.1.158:8002": 3,
        "192.168.1.158:11434": 1
      },
      "timeout": {
        "connect": 5,
        "send": 120,
        "read": 120
      },
      "retries": 2
    },
    "plugins": {
      "key-auth": {
        "header": "X-API-Key",
        "query": "api_key"
      },
      "ai-proxy": {
        "provider": "openai",
        "model": {
          "source": "header",
          "header": "X-Model"
        },
        "auth": {
          "source": "consumer"
        }
      },
      "ai-rate-limiting": {
        "limit_strategy": "token",
        "token_counting": {
          "enabled": true,
          "method": "response_usage",
          "fallback": "tiktoken"
        },
        "consumer_limits": true,
        "rejected_code": 429,
        "rejected_msg": "Token limit exceeded. Please try again later."
      },
      "response-rewrite": {
        "headers": {
          "set": {
            "X-Metered-By": "apisix-homelab",
            "X-Rate-Limit-Remaining": "$ai_rate_limit_remaining"
          }
        }
      }
    }
  }'
```

### Step 2.2: Configure Per-Consumer Token Limits

Each consumer (App A, App B, etc.) gets their own token budget:

```bash
# Create Consumer: App A (1 million tokens per day)
curl -X PUT http://127.0.0.1:9180/apisix/admin/consumers/app-a \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "app-a",
    "desc": "Application A - AI Research Pipeline",
    "plugins": {
      "key-auth": {
        "key": "'"$(openssl rand -hex 24)"'"
      },
      "ai-rate-limiting": {
        "tokens_per_day": 1000000,
        "tokens_per_hour": 200000,
        "tokens_per_minute": 50000,
        "requests_per_minute": 30
      }
    }
  }'

# Create Consumer: App B (500K tokens per day)
curl -X PUT http://127.0.0.1:9180/apisix/admin/consumers/app-b \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "app-b",
    "desc": "Application B - DevOps Automation",
    "plugins": {
      "key-auth": {
        "key": "'"$(openssl rand -hex 24)"'"
      },
      "ai-rate-limiting": {
        "tokens_per_day": 500000,
        "tokens_per_hour": 100000,
        "tokens_per_minute": 25000,
        "requests_per_minute": 20
      }
    }
  }'

# Create Consumer: Personal (unlimited, for your own use)
curl -X PUT http://127.0.0.1:9180/apisix/admin/consumers/personal \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "personal",
    "desc": "Personal use - homelab owner",
    "plugins": {
      "key-auth": {
        "key": "'"$(openssl rand -hex 24)"'"
      },
      "ai-rate-limiting": {
        "tokens_per_day": 10000000,
        "tokens_per_hour": 5000000,
        "tokens_per_minute": 500000,
        "requests_per_minute": 120
      }
    }
  }'
```

---

## Phase 3: Retrieve and Manage Consumer API Keys

### Step 3.1: List All Consumers

```bash
curl -s http://127.0.0.1:9180/apisix/admin/consumers \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" | jq '.list[] | {
    username: .value.username,
    description: .value.desc,
    key: .value.plugins["key-auth"].key
  }'
```

### Step 3.2: Share API Keys with Consumers

Provide each consumer with:
1. Their API key
2. The endpoint URL
3. Usage instructions

```
-----------------------------------
Consumer: App A
Endpoint: http://192.168.1.157:9080/v1/chat/completions
  (or via Tailscale: http://100.79.80.119:9080/v1/chat/completions)
API Key:  <their key from above>

Limits:
  - 1,000,000 tokens/day
  - 200,000 tokens/hour
  - 30 requests/minute

Usage example:
  curl -X POST http://192.168.1.157:9080/v1/chat/completions \
    -H "X-API-Key: <their-key>" \
    -H "Content-Type: application/json" \
    -d '{"model": "deepseek-r1", "messages": [{"role": "user", "content": "Hello"}]}'
-----------------------------------
```

### Step 3.3: Revoke a Consumer Key

```bash
# To revoke App B's access:
curl -X DELETE http://127.0.0.1:9180/apisix/admin/consumers/app-b \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}"

# Or rotate the key without deleting the consumer:
NEW_KEY=$(openssl rand -hex 24)
curl -X PATCH http://127.0.0.1:9180/apisix/admin/consumers/app-b \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "plugins": {
      "key-auth": {
        "key": "'"${NEW_KEY}"'"
      }
    }
  }'
echo "New key for App B: ${NEW_KEY}"
```

---

## Phase 4: Training Workload Metering (GPU Hours)

For consumers that need GPU time for fine-tuning or training, track usage in GPU-hours via Redis and APISIX's serverless function.

### Step 4.1: Install Redis

```bash
# On the Minisforum
docker run -d \
  --name redis-metering \
  --restart unless-stopped \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Step 4.2: Create the Training Workload Route

```bash
curl -X PUT http://127.0.0.1:9180/apisix/admin/routes/dgx-training-metered \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "/v1/training/*",
    "name": "dgx-training-metered",
    "desc": "Metered access to DGX Spark training/fine-tuning",
    "methods": ["POST", "GET", "DELETE"],
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "192.168.1.158:8080": 1
      },
      "timeout": {
        "connect": 5,
        "send": 30,
        "read": 3600
      }
    },
    "plugins": {
      "key-auth": {
        "header": "X-API-Key"
      },
      "serverless-pre-function": {
        "phase": "access",
        "functions": [
          "return function(conf, ctx)\n  local redis = require(\"resty.redis\")\n  local red = redis:new()\n  red:set_timeout(1000)\n  local ok, err = red:connect(\"127.0.0.1\", 6379)\n  if not ok then\n    core.log.error(\"Redis connection failed: \", err)\n    return\n  end\n\n  local consumer = ctx.var.consumer_name or \"unknown\"\n  local key = \"gpu_hours:\" .. consumer .. \":\" .. os.date(\"%Y-%m\")\n\n  -- Record start time\n  ctx.gpu_start_time = ngx.now()\n\n  -- Check if consumer has exceeded monthly GPU hours\n  local used, err = red:get(key)\n  if used and tonumber(used) then\n    local limit = 100 -- default 100 GPU-hours/month\n    if tonumber(used) >= limit then\n      return 429, '{\"error\": \"Monthly GPU hour limit exceeded\"}'\n    end\n  end\n\n  red:set_keepalive(10000, 100)\nend"
        ]
      },
      "serverless-post-function": {
        "phase": "log",
        "functions": [
          "return function(conf, ctx)\n  local redis = require(\"resty.redis\")\n  local red = redis:new()\n  red:set_timeout(1000)\n  local ok, err = red:connect(\"127.0.0.1\", 6379)\n  if not ok then return end\n\n  local consumer = ctx.var.consumer_name or \"unknown\"\n  local key = \"gpu_hours:\" .. consumer .. \":\" .. os.date(\"%Y-%m\")\n\n  -- Calculate GPU hours used (time elapsed in hours)\n  local elapsed = (ngx.now() - (ctx.gpu_start_time or ngx.now())) / 3600\n\n  -- Increment the counter\n  red:incrbyfloat(key, elapsed)\n  -- Set expiry to 90 days (keep 3 months of history)\n  red:expire(key, 7776000)\n\n  red:set_keepalive(10000, 100)\nend"
        ]
      }
    }
  }'
```

### Step 4.3: Query GPU Hour Usage

```bash
# Check a consumer's GPU hours used this month
docker exec redis-metering redis-cli GET "gpu_hours:app-a:$(date +%Y-%m)"

# Check all consumers
docker exec redis-metering redis-cli KEYS "gpu_hours:*"

# Get all values
for key in $(docker exec redis-metering redis-cli KEYS "gpu_hours:*" | tr -d '\r'); do
  value=$(docker exec redis-metering redis-cli GET "$key" | tr -d '\r')
  echo "$key: ${value} GPU-hours"
done
```

---

## Phase 5: Observability with Prometheus

### Step 5.1: Enable the Prometheus Plugin Globally

```bash
# Enable Prometheus metrics collection
curl -X PUT http://127.0.0.1:9180/apisix/admin/global_rules/prometheus-metrics \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "plugins": {
      "prometheus": {
        "prefer_name": true,
        "default_buckets": [0.1, 0.3, 0.5, 1, 2, 5, 10, 30, 60, 120]
      }
    }
  }'
```

### Step 5.2: Verify Metrics Endpoint

```bash
# APISIX exposes metrics on port 9091 by default
curl -s http://127.0.0.1:9091/apisix/prometheus/metrics | head -50

# Key metrics to look for:
# apisix_http_status         -- HTTP status code distribution
# apisix_bandwidth           -- Bytes in/out
# apisix_http_latency_bucket -- Request latency distribution
# apisix_node_info           -- APISIX node information
```

### Step 5.3: Deploy Prometheus (Optional)

If you want a full monitoring stack:

```bash
# Create Prometheus config
mkdir -p ~/monitoring
cat > ~/monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'apisix'
    metrics_path: '/apisix/prometheus/metrics'
    static_configs:
      - targets: ['host.docker.internal:9091']
        labels:
          service: 'apisix-gateway'

  - job_name: 'openclaw'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['host.docker.internal:18789']
        labels:
          service: 'openclaw-gateway'

  - job_name: 'dgx-spark'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['192.168.1.158:9100']
        labels:
          service: 'dgx-spark'
          role: 'compute-engine'
EOF

# Run Prometheus
docker run -d \
  --name prometheus \
  --restart unless-stopped \
  -p 9090:9090 \
  -v ~/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro \
  --add-host host.docker.internal:host-gateway \
  prom/prometheus:latest

# Run Grafana (optional, for dashboards)
docker run -d \
  --name grafana \
  --restart unless-stopped \
  -p 3003:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=changeme \
  --add-host host.docker.internal:host-gateway \
  grafana/grafana:latest

# Access:
# Prometheus: http://192.168.1.157:9090
# Grafana:    http://192.168.1.157:3003 (admin/changeme)
```

### Step 5.4: Example Prometheus Queries

```promql
# Total requests per consumer per day
sum by (consumer_name) (increase(apisix_http_status{route="dgx-inference-metered"}[24h]))

# Average latency per model
histogram_quantile(0.95, sum by (le, route) (rate(apisix_http_latency_bucket[5m])))

# Tokens per consumer (if using ai-rate-limiting metrics)
sum by (consumer_name) (increase(apisix_ai_tokens_total[24h]))

# Error rate
sum(rate(apisix_http_status{code=~"5.."}[5m])) / sum(rate(apisix_http_status[5m])) * 100
```

---

## Testing the Full Metering Pipeline

### Test 1: Basic Metered Inference

```bash
# Get App A's API key (from Phase 3)
APP_A_KEY="<app-a-key-from-above>"

# Send a metered inference request
curl -X POST http://192.168.1.157:9080/v1/chat/completions \
  -H "X-API-Key: ${APP_A_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Explain the theory of relativity in 3 sentences."}
    ],
    "max_tokens": 200
  }'

# Check response headers for metering info
curl -v -X POST http://192.168.1.157:9080/v1/chat/completions \
  -H "X-API-Key: ${APP_A_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50
  }' 2>&1 | grep -E "X-Metered|X-Rate"
```

### Test 2: Rate Limit Enforcement

```bash
# Rapidly send requests to trigger rate limiting
for i in $(seq 1 35); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://192.168.1.157:9080/v1/chat/completions \
    -H "X-API-Key: ${APP_A_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"model": "deepseek-r1", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 10}')
  echo "Request $i: HTTP $STATUS"
done

# After ~30 requests/minute, you should see HTTP 429 responses
```

### Test 3: Unauthorized Access

```bash
# Test without an API key (should be rejected)
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://192.168.1.157:9080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-r1", "messages": [{"role": "user", "content": "Hello"}]}'
# Expected: 401

# Test with an invalid key
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://192.168.1.157:9080/v1/chat/completions \
  -H "X-API-Key: invalid-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-r1", "messages": [{"role": "user", "content": "Hello"}]}'
# Expected: 401
```

---

## APISIX Route Summary

After completing all phases:

| Route                    | URI                      | Auth     | Metering        | Upstream         |
|--------------------------|--------------------------|----------|-----------------|------------------|
| dgx-inference-metered    | /v1/chat/completions     | API Key  | Token-based     | DGX models       |
| dgx-training-metered     | /v1/training/*           | API Key  | GPU-hour-based  | DGX NemoClaw     |

| Consumer  | Description          | Token Limit/Day | GPU Hours/Month |
|-----------|----------------------|-----------------|-----------------|
| personal  | Homelab owner        | 10M             | Unlimited       |
| app-a     | AI Research Pipeline | 1M              | 100             |
| app-b     | DevOps Automation    | 500K            | 50              |

---

**Next step**: Proceed to `07_RESOURCE_ALLOCATION.md` for capacity planning.
