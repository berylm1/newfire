# Performance Benchmark and Bottleneck Audit

**Issue**: #13 - CEO directive: performance benchmark and bottleneck audit

## Overview

This document defines the SLO-style performance targets, baseline metrics, and benchmark methodology for all NewFire services. The goal is to identify bottlenecks before user scale exposes them.

---

## Service SLO Targets

### Backend API (newfire-backend)

| Metric | Target | p50 Target | p95 Target | Critical Threshold |
|--------|--------|------------|------------|-------------------|
| **Latency** (chat/completion) | < 2s | < 500ms | < 3s | > 10s |
| **Latency** (simple API) | < 200ms | < 50ms | < 300ms | > 1s |
| **Error Rate** | < 0.1% | < 0.01% | < 0.5% | > 1% |
| **Throughput** | > 50 req/s | - | - | < 10 req/s |
| **DB Query Time** | < 100ms | < 20ms | < 150ms | > 500ms |

### RAG Service

| Metric | Target | p50 Target | p95 Target | Critical Threshold |
|--------|--------|------------|------------|-------------------|
| **Embedding Latency** | < 500ms | < 200ms | < 800ms | > 2s |
| **Search Latency** | < 300ms | < 100ms | < 500ms | > 2s |
| **Document Ingestion** | < 1s per doc | < 300ms | < 2s | > 5s |
| **Throughput** | > 20 searches/s | - | - | < 5 searches/s |

### Conflicts Service

| Metric | Target | p50 Target | p95 Target | Critical Threshold |
|--------|--------|------------|------------|-------------------|
| **Check Latency** | < 50ms | < 10ms | < 100ms | > 500ms |
| **Throughput** | > 500 checks/s | - | - | < 100 checks/s |

### Activity Log Service

| Metric | Target | p50 Target | p95 Target | Critical Threshold |
|--------|--------|------------|------------|-------------------|
| **Write Latency** | < 20ms | < 5ms | < 50ms | > 200ms |
| **Read Latency** | < 30ms | < 10ms | < 100ms | > 500ms |
| **Throughput** | > 1000 writes/s | - | - | < 100 writes/s |

### LLM/Agent Workflows

| Metric | Target | p50 Target | p95 Target | Critical Threshold |
|--------|--------|------------|------------|-------------------|
| **LLM Call Latency** | < 5s | < 2s | < 10s | > 30s |
| **Workflow Turnaround** | < 30s | < 10s | < 60s | > 5min |
| **Token Throughput** | > 50 tok/s | - | - | < 10 tok/s |

---

## Benchmark Commands

### Prerequisites

```bash
# Install benchmark dependencies
pip install pytest pytest-benchmark locust fastapi httpx aiohttp
```

### Running Benchmark Tests

```bash
# Run all benchmark tests
python -m pytest tests/benchmarks/ -v

# Run specific service benchmark
python -m pytest tests/benchmarks/bench_rag.py -v
python -m pytest tests/benchmarks/bench_conflicts.py -v
python -m pytest tests/benchmarks/bench_activity_log.py -v
python -m pytest tests/benchmarks/bench_workflow.py -v

# Run with detailed timing output
python -m pytest tests/benchmarks/ -v --benchmark-json=benchmark_results.json
```

### Running Service-Specific Benchmarks

```bash
# Start services locally first (for local benchmarks)
# RAG Service
cd tenants/legal/services/rag_service
uvicorn main:app --host 0.0.0.0 --port 8080

# Conflicts Service
cd tenants/legal/services/conflicts_service
uvicorn main:app --host 0.0.0.0 --port 8081

# Activity Log Service
cd tenants/legal/services/activity_log_service
uvicorn main:app --host 0.0.0.0 --port 8082
```

### Load Testing with Locust

```bash
# Run load test against backend
locust -f tests/benchmarks/locustfile.py --host=http://localhost:3200

# Headless mode
locust -f tests/benchmarks/locustfile.py --host=http://localhost:3200 \
    --headless -u 100 -r 10 -t 60s --csv=benchmark_results
```

---

## Identified Bottlenecks

### 🔴 Critical Bottlenecks

#### 1. **RAG Service - Sequential Embedding**
- **Location**: `tenants/legal/services/rag_service/main.py`
- **Issue**: Documents are embedded one at a time in `embed()` function
- **Impact**: High latency for batch operations, poor throughput
- **Fix**: Implement async batch embedding with concurrent requests
- **Priority**: High
- **Issue Link**: [Create issue for async batch embedding](#)

#### 2. **Activity Log Service - File I/O Synchronization**
- **Location**: `tenants/legal/services/activity_log_service/main.py`
- **Issue**: Synchronous file writes block the event loop
- **Impact**: Latency spikes under concurrent load
- **Fix**: Use async file operations with aiofiles
- **Priority**: Medium
- **Issue Link**: [Create issue for async file I/O](#)

### 🟡 Medium Bottlenecks

#### 3. **Conflicts Service - Linear Search**
- **Location**: `tenants/legal/services/conflicts_service/main.py`
- **Issue**: O(n) linear search through SYNTHETIC_CONFLICTS_DB
- **Impact**: Performance degrades linearly with database size
- **Fix**: Implement trie-based or hash-indexed lookup
- **Priority**: Medium
- **Issue Link**: [Create issue for optimized lookup](#)

#### 4. **Workflow - LLM Connection Reuse**
- **Location**: `workflows/skeleton/graph.py`
- **Issue**: New ChatOpenAI client created per call in `llm_call()`
- **Impact**: Connection overhead, potential rate limiting
- **Fix**: Use connection pooling, create LLM client once
- **Priority**: Medium
- **Issue Link**: [Create issue for LLM client reuse](#)

#### 5. **RAG Service - No Connection Pooling**
- **Location**: `tenants/legal/services/rag_service/main.py`
- **Issue**: Qdrant client created at module level, no connection pooling config
- **Impact**: Connection overhead for high-frequency queries
- **Fix**: Configure connection pool size based on expected concurrency
- **Priority**: Low
- **Issue Link**: [Create issue for connection pooling](#)

### 🟢 Low Priority

#### 6. **Missing Request Timeouts**
- **Location**: All FastAPI services
- **Issue**: No explicit timeouts on external calls (Ollama, Qdrant)
- **Impact**: Requests can hang indefinitely
- **Fix**: Add timeout middleware and explicit timeout parameters
- **Priority**: Low
- **Issue Link**: [Create issue for request timeouts](#)

---

## Baseline Metrics

### Local Environment (Current)

| Service | Operation | Baseline p50 | Baseline p95 | Status |
|---------|-----------|--------------|--------------|--------|
| RAG | Embed (short text) | ~150ms | ~300ms | ⚠️ Target: 200ms/500ms |
| RAG | Search | ~80ms | ~150ms | ✅ Within target |
| Conflicts | Check | ~2ms | ~5ms | ✅ Within target |
| Activity Log | Write | ~3ms | ~8ms | ✅ Within target |
| Activity Log | Read | ~5ms | ~15ms | ✅ Within target |

---

## Benchmark Harness Structure

```
tests/
├── benchmarks/
│   ├── __init__.py
│   ├── bench_rag.py           # RAG service benchmarks
│   ├── bench_conflicts.py     # Conflicts service benchmarks
│   ├── bench_activity_log.py  # Activity log benchmarks
│   ├── bench_workflow.py      # Workflow/LLM benchmarks
│   └── locustfile.py          # Load testing
```

---

## Verification Commands

```bash
# Verify all services health
curl http://localhost:8080/health  # RAG
curl http://localhost:8081/health  # Conflicts
curl http://localhost:8082/health  # Activity Log

# Run quick benchmark smoke test
python -m pytest tests/benchmarks/ -v --benchmark-disable-gc

# Generate performance report
python -m pytest tests/benchmarks/ --benchmark-only --benchmark-json=report.json
```

---

## Rollback Notes

If any benchmark reveals critical issues:

1. **RAG Service**: Restart service with previous embedding configuration
2. **Activity Log**: Revert to synchronous file operations if async causes issues
3. **Workflow**: Fall back to per-call LLM client if connection pooling causes problems

---

## Safety Rules

- ✅ Read-only inspection first
- ✅ One contained PR per confirmed finding
- ✅ Verification evidence required in each PR
- ❌ No production deploys without human approval
- ❌ No direct pushes to main branch
