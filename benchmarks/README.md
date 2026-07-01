# NewFire Benchmark Harness

A local/staging-only performance benchmark harness for the NewFire platform, including the backend API and OpenClaw multi-agent orchestrator.

## ⚠️ IMPORTANT: Production Warning

**DO NOT RUN THESE BENCHMARKS AGAINST PRODUCTION WITHOUT EXPLICIT APPROVAL**

These scripts generate significant concurrent load and can:
- Impact production performance
- Trigger rate limiting
- Cause unintended side effects
- Consume API quotas

Always use **local** or **staging** environments for benchmarking.

## Overview

This benchmark suite uses [autocannon](https://github.com/mcollina/autocannon) for HTTP load testing. It covers:

### Backend Endpoints
| Endpoint | Purpose | Benchmark Script |
|----------|---------|------------------|
| `/health` | Health check for load balancers | `health-benchmark.js` |
| `/metrics` | Prometheus metrics | `metrics-benchmark.js` |
| `/login` | JWT authentication | `auth-benchmark.js` |
| `/webhooks/inbox` | HMAC-validated webhooks | `webhooks-benchmark.js` |
| `/chat` | AI chat completions | `chat-benchmark.js` |

### OpenClaw Endpoints
| Endpoint | Purpose | Benchmark Script |
|----------|---------|------------------|
| `/health` | OpenClaw health check | `openclaw-benchmark.js` |
| `/api/agent/run` | Agent task execution | `openclaw-benchmark.js` |
| `/api/agent/delegate` | Multi-agent delegation | `openclaw-benchmark.js` |

## Prerequisites

```bash
# Node.js >= 18 required
node --version

# Install dependencies
cd benchmarks
npm install
```

## Quick Start

### 1. Configure Environment

Copy and edit the environment configuration:

```bash
cp config/env.example.js config/env.js
# Edit config/env.js with your staging URLs and credentials
```

Environment variables can also be set directly:
```bash
export BENCHMARK_ENV=staging
export STAGING_BACKEND_URL=https://staging.newfire.app/backend
export BENCHMARK_USER=your-test@example.com
export BENCHMARK_PASSWORD=your-test-password
```

### 2. Run Individual Benchmarks

```bash
# Health endpoint (lightweight, safe for most environments)
npm run benchmark:health -- http://localhost:3200/health

# Metrics endpoint
npm run benchmark:metrics -- http://localhost:3200/metrics

# Authentication
npm run benchmark:auth -- http://localhost:3200

# Webhooks
npm run benchmark:webhooks -- http://localhost:3200

# Chat API
npm run benchmark:chat -- http://localhost:3200

# OpenClaw (all modes)
npm run benchmark:openclaw -- http://localhost:18789
npm run benchmark:openclaw -- http://localhost:18789 health   # health only
npm run benchmark:openclaw -- http://localhost:18789 agent    # agent execution only
npm run benchmark:openclaw -- http://localhost:18789 delegate  # delegation only
```

### 3. Run All Benchmarks

```bash
npm run benchmark:all
```

## Output Format

Each benchmark produces output with the following metrics:

### Latency Metrics (milliseconds)
| Metric | Description |
|--------|-------------|
| p50 | 50th percentile latency |
| p75 | 75th percentile latency |
| p90 | 90th percentile latency |
| p95 | 95th percentile latency |
| p99 | 99th percentile latency |
| p999 | 99.9th percentile latency |
| mean | Average latency |
| stdDev | Standard deviation |

### Request Metrics
| Metric | Description |
|--------|-------------|
| Total | Total requests completed |
| RPS | Requests per second |
| Errors | Number of failed requests |

### Error Rate
| Metric | Description |
|--------|-------------|
| Count | Number of non-2xx responses |
| Rate | Percentage of failed requests |

## Example Output

```
============================================================
Benchmark: Health Endpoint
============================================================

📊 Latency (ms):
  p50:  2ms
  p75:  3ms
  p90:  4ms
  p95:  5ms
  p99:  8ms
  p999: 12ms
  mean: 2.5ms

📈 Requests:
  Total:  12450
  RPS:    415.00

⚠️  Errors:
  Count:  0
  Rate:   0.00%

📦 Throughput: 1.25 MB/s

✅ Threshold Checks:
   p50 Latency: 2ms (threshold: 100ms) - ✅ PASS
   p95 Latency: 5ms (threshold: 500ms) - ✅ PASS
   Error Rate:  0.00% (threshold: 1.0%) - ✅ PASS
```

## Threshold Configuration

Default thresholds are defined in `config/env.example.js`:

```javascript
export const thresholds = {
  // Latency thresholds in milliseconds
  latency: {
    p50: 100,    // 100ms for p50
    p95: 500,    // 500ms for p95
    p99: 1000    // 1s for p99
  },
  // Error rate threshold (percentage)
  errorRate: 1.0,  // 1% max
  // Requests per second minimum
  rps: 50,         // 50 RPS minimum
  // Throughput (bytes per second)
  throughput: 1000000  // 1 MB/s minimum
};
```

Adjust these based on your performance requirements.

## Benchmark Settings

Default settings (configurable in `config/env.example.js`):

| Setting | Default | Description |
|---------|---------|-------------|
| duration | 30s | Test duration |
| connections | 10 | Concurrent connections |
| pipelining | 1 | HTTP pipelining factor |
| warmupRequests | 10 | Initial warmup requests |
| timeout | 30s | Request timeout |

## Storing Results

Save benchmark results for comparison:

```bash
# Run and save JSON output
autocannon -j http://localhost:3200/health > results/health-$(date +%Y%m%d).json

# Generate comparison report
node scripts/parse-results.js --report results/*.json > reports/benchmark-$(date +%Y%m%d).md
```

## Architecture Notes

### Backend Architecture
- Express.js on port 3200
- JWT authentication
- PostgreSQL database
- Qdrant vector storage
- OpenRouter/OpenClaw/Ollama routing

### OpenClaw Architecture
- Multi-agent orchestrator on port 18789
- Agent task execution
- Tool orchestration
- Streaming responses via SSE

## Mock/Stub Flows

For testing without actual LLM calls:

1. **Chat Stub Mode**: Set `model: 'stub-model'` in chat requests
2. **OpenClaw Stub**: Configure `OPENCLAW_STUB_MODE=true`
3. **Auth Stub**: Use test JWTs (benchmark scripts include test token generation)

## Interpreting Results

### Good Performance
- Health/Metrics: p95 < 100ms, Error Rate < 0.1%
- Auth: p95 < 500ms, Error Rate < 1%
- Chat: p95 < 5000ms (LLM inference overhead), Error Rate < 2%
- OpenClaw: p95 < 10000ms (agent execution overhead), Error Rate < 5%

### Performance Degradation Signs
- p99 > 2x p95
- Increasing error rate over time
- Memory growth during test
- Connection timeouts

### Optimization Targets
1. Database query optimization (indexes, connection pooling)
2. Cache frequently accessed data
3. Reduce middleware overhead
4. Optimize LLM routing decisions
5. Implement rate limiting

## Troubleshooting

### Connection Refused
- Ensure the target service is running
- Check firewall/network settings
- Verify correct port numbers

### High Error Rates
- Check authentication credentials
- Verify HMAC signatures for webhooks
- Ensure rate limits not exceeded

### Timeouts
- Increase timeout setting
- Check backend processing time
- Verify database connectivity

## Contributing

When adding new benchmarks:
1. Follow the existing script structure
2. Include documentation in this README
3. Add threshold checks for relevant metrics
4. Include mock/stub options for testing without real services

## License

Proprietary - NewFire Project
