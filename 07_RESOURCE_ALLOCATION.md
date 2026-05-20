# Resource Allocation -- Capacity Planning and Optimization

## Minisforum X1 Pro 370 -- Container Capacity

### Hardware Specifications

| Resource | Total   | OS Reserved | Available for Containers |
|----------|---------|-------------|--------------------------|
| RAM      | 96 GB   | ~4-6 GB     | ~90 GB                   |
| CPU      | 12 cores (24 threads) AMD Ryzen AI 9 HX 370 | ~2 threads | ~22 threads |
| Storage  | 2 TB NVMe | ~50 GB (OS + base) | ~1.95 TB          |
| GPU      | Radeon 890M (integrated) | Shared | Not used for inference |

### Container Capacity Estimate

With 90 GB available RAM and 22 usable CPU threads, the Minisforum can run **35-50 containers** depending on workload profiles.

**Scaling Formula:**
```
Max Containers = (Total RAM - OS Reserved) / Avg Container Memory * Safety Factor

Conservative:  (96 - 6) / 2.5 * 0.7 = ~25 containers
Moderate:      (96 - 6) / 2.0 * 0.7 = ~31 containers
Aggressive:    (96 - 6) / 1.5 * 0.7 = ~42 containers

Safety Factor = 0.7 (leave 30% headroom for spikes, OS caches, swap avoidance)
```

### Recommended Container Breakdown

| Service Category         | Containers | RAM Each | RAM Total | CPU Limit | Priority |
|--------------------------|-----------|----------|-----------|-----------|----------|
| **OpenClaw Gateway**     | 1         | 2 GB     | 2 GB      | 1.0       | Critical |
| **Tenant Agents (light)**| 20-30     | 1-2 GB   | 20-60 GB  | 0.5-1.0   | Normal   |
| **OpenRouter Cache/Proxy** | 1       | 1 GB     | 1 GB      | 0.5       | Normal   |
| **NemoClaw Client**      | 1         | 1 GB     | 1 GB      | 0.5       | Normal   |
| **Monitoring Stack**     |           |          |           |           |          |
|   - Prometheus           | 1         | 2 GB     | 2 GB      | 1.0       | Low      |
|   - Grafana              | 1         | 1 GB     | 1 GB      | 0.5       | Low      |
|   - Redis (metering)     | 1         | 256 MB   | 256 MB    | 0.25      | Normal   |
|   - APISIX               | 1         | 512 MB   | 512 MB    | 1.0       | High     |
|   - etcd (APISIX)        | 1         | 512 MB   | 512 MB    | 0.5       | High     |
| **Database**             |           |          |           |           |          |
|   - PostgreSQL (OpenClaw)| 1         | 4 GB     | 4 GB      | 2.0       | Critical |
|   - pgBouncer (pool)     | 1         | 256 MB   | 256 MB    | 0.25      | Normal   |
| **Webhook Receivers**    | 2-3       | 1-2 GB   | 3-5 GB    | 0.5       | Normal   |
| **Ollama (CPU)**         | 1         | 4-8 GB   | 4-8 GB    | 4.0       | Normal   |
| **TOTAL**                | ~35-45    |          | **35-80 GB** | ~15-20 | |

### Memory Budget by Scenario

**Scenario A: Minimal (development/testing)**
```
OpenClaw Gateway:        2 GB
5 Tenant Agents:         5 GB (1 GB each)
APISIX + etcd:           1 GB
Redis:                   256 MB
Ollama (CPU, small):     4 GB
PostgreSQL:              2 GB
------------------------------------
TOTAL:                   ~14.3 GB
Remaining:               ~75 GB free
Containers:              ~10
```

**Scenario B: Moderate (daily use)**
```
OpenClaw Gateway:        2 GB
15 Tenant Agents:        22.5 GB (1.5 GB each)
APISIX + etcd:           1 GB
Redis:                   256 MB
Prometheus + Grafana:    3 GB
Ollama (CPU, medium):    8 GB
PostgreSQL + pgBouncer:  4.3 GB
Webhook Receivers (2):   3 GB
NemoClaw Client:         1 GB
OpenRouter Cache:        1 GB
------------------------------------
TOTAL:                   ~46 GB
Remaining:               ~44 GB free
Containers:              ~25
```

**Scenario C: Maximum (full production)**
```
OpenClaw Gateway:        2 GB
30 Tenant Agents:        45 GB (1.5 GB each)
APISIX + etcd:           1 GB
Redis:                   256 MB
Prometheus + Grafana:    3 GB
Ollama (CPU, 7B models): 8 GB
PostgreSQL + pgBouncer:  8.3 GB
Webhook Receivers (3):   5 GB
NemoClaw Client:         1 GB
OpenRouter Cache:        1 GB
------------------------------------
TOTAL:                   ~74.6 GB
Remaining:               ~15 GB free (buffer)
Containers:              ~42
```

---

## DGX Spark -- Capacity Planning

### Hardware Specifications

| Resource          | Total                  | Notes                              |
|-------------------|------------------------|------------------------------------|
| Unified Memory    | 128 GB (CPU+GPU shared)| No separate VRAM -- all unified    |
| GPU Compute       | 1 PFLOP FP4 / 209 TFLOPS FP16 | NVIDIA Blackwell architecture |
| CPU               | NVIDIA Grace (Arm)     | 10 cores                           |
| Storage           | 4 TB NVMe              |                                    |
| Interconnect      | NVLink-C2C             | CPU-GPU at 273 GB/s                |

### Model Capacity

The DGX Spark's 128 GB unified memory determines how many and how large models it can serve:

| Model Size (Parameters) | FP16 Memory | INT8 Memory | INT4 Memory | Fits? |
|--------------------------|-------------|-------------|-------------|-------|
| 7B                       | ~14 GB      | ~7 GB       | ~4 GB       | Yes (many) |
| 13B                      | ~26 GB      | ~13 GB      | ~7 GB       | Yes (several) |
| 30-34B                   | ~65 GB      | ~33 GB      | ~17 GB      | Yes (2-3) |
| 70B                      | ~140 GB     | ~70 GB      | ~35 GB      | Yes (INT8/INT4) |
| 200B                     | ~400 GB     | ~200 GB     | ~100 GB     | INT4 only |
| 405B (Llama 3.1)         | ~810 GB     | ~405 GB     | ~200 GB     | No (need dual DGX) |

**Rule of thumb**: A model requires roughly `2 * Parameters (in billions)` GB at FP16.

### Recommended Model Deployment

```
DGX Spark -- 128 GB Unified Memory
+----------------------------------------------------------+
|                                                          |
|  System + OS:                         8 GB               |
|                                                          |
|  Model 1: GLM-5 (FP16)               ~40 GB             |
|  Model 2: DeepSeek-R1 (FP16)         ~40 GB             |
|                                                          |
|  Agent Workers:                       ~8 GB              |
|    - OpenCode worker:   4 GB                             |
|    - OpenHands worker:  4 GB                             |
|                                                          |
|  Ollama (dynamic):                    ~20 GB             |
|    - Serves smaller models on demand                     |
|    - Auto-unloads inactive models                        |
|                                                          |
|  Buffer/Headroom:                     ~12 GB             |
|    - KV cache growth during inference                    |
|    - Temporary allocations                               |
|                                                          |
+----------------------------------------------------------+
   Total: ~128 GB
```

### Inference Performance Estimates

| Model | Quantization | Tokens/sec (generation) | Time to First Token | Concurrent Users |
|-------|-------------|------------------------|---------------------|------------------|
| GLM-5 (est. 30-40B) | FP16 | ~30-50 tok/s | ~200ms | 2-4 |
| DeepSeek-R1 (est. 30-40B) | FP16 | ~25-45 tok/s | ~250ms | 2-4 |
| Llama 3.1 70B | INT8 | ~15-25 tok/s | ~500ms | 1-2 |
| Llama 3.1 8B | FP16 | ~80-120 tok/s | ~50ms | 8-16 |
| CodeLlama 70B | INT8 | ~15-25 tok/s | ~500ms | 1-2 |

**Note**: These are estimates. Actual performance depends on context length, batch size, and concurrent load.

---

## Performance Optimizations

### Minisforum Optimizations

#### 1. Use Alpine-Based Images

```bash
# Prefer Alpine images for smaller footprint
# Instead of: ubuntu:22.04 (~75 MB)
# Use:        alpine:3.19  (~7 MB)

# Example: custom agent image
cat << 'DOCKERFILE' | docker build -t agent-alpine -
FROM alpine:3.19
RUN apk add --no-cache python3 py3-pip curl jq nodejs npm
RUN adduser -D -s /bin/sh agent
USER agent
WORKDIR /home/agent
DOCKERFILE
```

#### 2. Set Memory Limits on All Containers

```bash
# Always set memory limits to prevent any container from consuming all RAM
docker run -d \
  --name my-agent \
  --memory 2g \
  --memory-swap 2g \
  --memory-reservation 1g \
  --cpus 1.0 \
  --pids-limit 256 \
  my-agent:latest

# Or in Docker Compose:
# services:
#   my-agent:
#     deploy:
#       resources:
#         limits:
#           memory: 2g
#           cpus: '1.0'
#         reservations:
#           memory: 1g
#           cpus: '0.5'
```

#### 3. Configure Log Rotation

```bash
# Set Docker's default log driver to limit log size
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  },
  "storage-driver": "overlay2"
}
EOF

sudo systemctl restart docker
```

#### 4. Use tmpfs for Ephemeral Data

```bash
# Mount tmp directories as tmpfs (RAM-based, faster, auto-cleaned)
docker run -d \
  --name my-agent \
  --tmpfs /tmp:size=256m \
  --tmpfs /workspace:size=512m \
  my-agent:latest
```

#### 5. Enable Swap (Emergency Only)

```bash
# Create a swap file as emergency overflow (not for regular use)
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Set swappiness low (only use swap under pressure)
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### DGX Spark Optimizations

#### 1. Model Quantization

```bash
# Use INT8 quantization for 2x more models in memory
nvidia-nemoclaw model deploy llama3.1-70b \
  --namespace Tenant-AI-Research \
  --memory 70GB \
  --quantization int8  # 70 GB instead of 140 GB at FP16

# Use INT4 for maximum capacity (some quality tradeoff)
nvidia-nemoclaw model deploy llama3.1-70b \
  --namespace Tenant-AI-Research \
  --memory 35GB \
  --quantization int4  # 35 GB instead of 140 GB at FP16
```

#### 2. Ollama Model Loading Strategy

```bash
# Configure Ollama to keep only 2-3 models loaded
# Unload inactive models after 5 minutes
export OLLAMA_MAX_LOADED_MODELS=3
export OLLAMA_KEEP_ALIVE=5m

# Or set in systemd override:
sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_MAX_LOADED_MODELS=3"
Environment="OLLAMA_KEEP_ALIVE=5m"
Environment="OLLAMA_NUM_PARALLEL=4"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama
```

#### 3. KV Cache Optimization

```bash
# For NemoClaw-managed models, configure KV cache limits
nvidia-nemoclaw model update glm-5 \
  --namespace Tenant-AI-Research \
  --kv-cache-size 4GB \
  --max-context-length 32768

# This limits the KV cache growth, keeping memory predictable
```

---

## Monitoring Resource Usage

### Real-Time Container Stats

```bash
# On the Minisforum -- watch container resource usage
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.PIDs}}"

# Example output:
# NAME                CPU %     MEM USAGE / LIMIT   MEM %     PIDS
# openclaw-gateway    2.50%     1.2GiB / 2GiB       60.00%    45
# agent-tenant-1      0.80%     850MiB / 2GiB       41.50%    12
# agent-tenant-2      1.20%     920MiB / 2GiB       44.92%    15
# apisix              0.30%     180MiB / 512MiB     35.16%    8
# prometheus          1.50%     1.5GiB / 2GiB       75.00%    22
# postgres            3.00%     2.8GiB / 4GiB       70.00%    35
# ollama              15.00%    6.5GiB / 8GiB       81.25%    4
```

### System-Level Monitoring

```bash
# Overall memory usage
free -h

# Per-process memory (top consumers)
ps aux --sort=-%mem | head -20

# Disk usage
df -h /

# Docker disk usage
docker system df

# Network connections
ss -tulnp | grep -E '(18789|3000|3002|9080|11434)'
```

### DGX Spark GPU Monitoring

```bash
# On the DGX Spark
# Real-time GPU stats
nvidia-smi -l 1

# GPU memory per process
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv

# NemoClaw resource view
nvidia-nemoclaw resources show --watch

# Ollama model status
ollama ps
```

### Alert Thresholds

Set up alerts (via Prometheus/Grafana or simple cron scripts) for:

| Metric                    | Warning   | Critical  | Action                      |
|---------------------------|-----------|-----------|------------------------------|
| Minisforum RAM Usage      | > 70%     | > 85%     | Scale down agents            |
| Minisforum Disk Usage     | > 75%     | > 90%     | Clean logs, prune images     |
| DGX GPU Memory Usage      | > 80%     | > 95%     | Unload idle models           |
| Container Restart Count   | > 3/hour  | > 10/hour | Investigate OOM/crashes      |
| API Response Time (p95)   | > 2s      | > 10s     | Check model load, scale      |
| OpenRouter Daily Spend    | > $7.50   | > $9.00   | Review routing, check abuse  |

Simple alert script for cron:

```bash
#!/bin/bash
# Save as /usr/local/bin/resource-alert.sh
# Add to cron: */5 * * * * /usr/local/bin/resource-alert.sh

MEM_PERCENT=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
DISK_PERCENT=$(df / | awk 'NR==2 {print $5}' | tr -d '%')

if [ "$MEM_PERCENT" -gt 85 ]; then
  echo "CRITICAL: Memory at ${MEM_PERCENT}%" | \
    logger -t resource-alert -p user.crit
fi

if [ "$DISK_PERCENT" -gt 90 ]; then
  echo "CRITICAL: Disk at ${DISK_PERCENT}%" | \
    logger -t resource-alert -p user.crit
fi
```

---

## Capacity Scaling Path

As your homelab grows, here is the upgrade path:

### Near-Term (Software)
1. Optimize container sizes (Alpine images, lower memory limits)
2. Use model quantization (INT8/INT4) on DGX
3. Implement smart routing (local first, cloud fallback)
4. Set aggressive idle timeouts on Ollama models

### Medium-Term (Hardware)
1. Add RAM to Minisforum (if board supports it -- check motherboard max)
2. Add a second DGX Spark for 256 GB unified memory + 2 PFLOP FP4
3. Run 405B parameter models across dual DGX Sparks

### Long-Term (Architecture)
1. Add a dedicated NAS for model storage (shared NFS mount)
2. Kubernetes (K3s) for container orchestration across both machines
3. Dedicated monitoring node
4. HA (High Availability) setup with two Minisforum units

---

**Next step**: Proceed to `08_CHECKLIST.md` for the complete implementation checklist.
