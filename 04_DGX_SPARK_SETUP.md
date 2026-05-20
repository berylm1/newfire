# DGX Spark Full Setup -- Compute Engine Deployment

## Prerequisites

Before starting this guide, you must have completed:

- `01_DGX_SPARK_RECOVERY.md` -- DGX Spark is recovered, SSH is working, Tailscale is installed
- `02_MINISFORUM_UPGRADE.md` -- Minisforum has OpenClaw properly installed

Verify connectivity before proceeding:

```bash
# From Minisforum
ssh newwaveclaw@192.168.1.158
nvidia-smi  # Should show the GB10 GPU with 128GB unified memory
exit
```

---

## Phase 1: Initialize NemoClaw on DGX Spark

NemoClaw is NVIDIA's tenant isolation and model management layer. It allows you to partition the DGX Spark's resources into isolated namespaces (tenants).

### Step 1.1: Install NemoClaw (if not pre-installed)

```bash
# SSH into the DGX Spark
ssh newwaveclaw@192.168.1.158

# Check if NemoClaw is already installed (DGX OS may include it)
which nvidia-nemoclaw
nvidia-nemoclaw --version

# If not installed, install from NVIDIA's repository
sudo apt update
sudo apt install -y nvidia-nemoclaw

# Or if it comes as a container:
docker pull nvcr.io/nvidia/nemoclaw:latest
```

### Step 1.2: Initialize the Cluster

```bash
# Initialize NemoClaw with a cluster name
nvidia-nemoclaw init --cluster-name home-lab

# Expected output:
# NemoClaw cluster 'home-lab' initialized successfully.
# Cluster ID:    cl_abc123
# GPU Memory:    128 GB (unified)
# Compute:       1 PFLOP FP4
# Storage:       4 TB NVMe
# Status:        READY
#
# Default namespace 'system' created.
# Admin token saved to: ~/.nemoclaw/admin-token
```

### Step 1.3: Verify the Cluster

```bash
# Check cluster status
nvidia-nemoclaw cluster status

# Expected output:
# Cluster: home-lab
# Status:  HEALTHY
# Nodes:   1 (local)
# GPU:     NVIDIA GB10 Superchip
# Memory:
#   Total:     128 GB
#   Available: 120 GB (8 GB reserved for system)
#   Used:      0 GB
# Namespaces: 1 (system)

# Check available GPU resources
nvidia-nemoclaw resources show
```

### Step 1.4: Configure NemoClaw Network

```bash
# Allow access from the Minisforum control plane
nvidia-nemoclaw config set api.listen "0.0.0.0:8080"
nvidia-nemoclaw config set api.allowedOrigins "192.168.1.157,100.79.80.119"

# Set up authentication token for external access
NEMOCLAW_TOKEN=$(nvidia-nemoclaw token create --name minisforum-control --role admin)
echo "NemoClaw token: $NEMOCLAW_TOKEN"
echo "Save this token -- you will need it on the Minisforum."

# Restart NemoClaw to apply changes
nvidia-nemoclaw restart
```

---

## Phase 2: Connect Minisforum to DGX Spark

### Step 2.1: Register DGX as Compute Backend

```bash
# On the Minisforum (192.168.1.157)
ssh newwaveclaw@192.168.1.157

# Run the onboard command to connect to the DGX Spark's NemoClaw
openclaw onboard \
  --backend nvidia-nemoclaw \
  --cluster-address 192.168.1.158:8080 \
  --cluster-token "${NEMOCLAW_TOKEN}"
```

This command will:
1. Test connectivity to the DGX Spark's NemoClaw API
2. Register the DGX Spark as a compute backend in OpenClaw
3. Configure routing rules for GPU workloads
4. Set up health checking

### Step 2.2: Verify the Connection

```bash
# Check backend status from OpenClaw
openclaw backends list

# Expected output:
# BACKEND            TYPE              STATUS    GPU MEMORY    ENDPOINT
# local-docker       docker            healthy   -             unix:///var/run/docker.sock
# dgx-spark          nvidia-nemoclaw   healthy   120 GB free   192.168.1.158:8080

# Test GPU access from the Minisforum
openclaw exec --backend dgx-spark -- nvidia-smi
```

### Step 2.3: Update OpenClaw Configuration

Edit `/etc/openclaw/openclaw.json` on the Minisforum to add the backend:

```json
{
  "backends": {
    "local": {
      "type": "docker",
      "endpoint": "unix:///var/run/docker.sock",
      "role": "control-plane",
      "capabilities": ["orchestration", "lightweight-agents", "api-gateway"]
    },
    "dgx-spark": {
      "type": "nvidia-nemoclaw",
      "endpoint": "http://192.168.1.158:8080",
      "token": "${NEMOCLAW_TOKEN}",
      "role": "compute-engine",
      "capabilities": ["gpu-inference", "large-models", "heavy-agents"],
      "healthCheck": {
        "interval": 30000,
        "timeout": 5000,
        "unhealthyThreshold": 3
      },
      "routing": {
        "preferForModels": ["*:70b", "*:405b", "deepseek-*", "glm-*"],
        "preferForTasks": ["inference", "training", "fine-tuning"]
      }
    }
  }
}
```

---

## Phase 3: Define Tenants and Deploy Models

### Step 3.1: Create Tenant Namespaces

```bash
# SSH into the DGX Spark
ssh newwaveclaw@192.168.1.158

# Create the AI Research tenant namespace
nvidia-nemoclaw namespace create Tenant-AI-Research \
  --memory-limit 50GB \
  --description "AI research workloads -- large language models"

# Create the DevOps tenant namespace
nvidia-nemoclaw namespace create Tenant-DevOps \
  --memory-limit 50GB \
  --description "DevOps automation -- code generation and deployment"

# Verify namespaces
nvidia-nemoclaw namespace list

# Expected output:
# NAMESPACE              MEMORY LIMIT    MEMORY USED    STATUS    MODELS
# system                 8 GB            2 GB           active    0
# Tenant-AI-Research     50 GB           0 GB           active    0
# Tenant-DevOps          50 GB           0 GB           active    0
# (unallocated)          20 GB           -              -         -
```

### Step 3.2: Deploy GLM-5 in AI Research Namespace

```bash
# Deploy the GLM-5 model to the AI Research namespace
nvidia-nemoclaw model deploy glm-5 \
  --namespace Tenant-AI-Research \
  --memory 40GB \
  --replicas 1 \
  --port 8001 \
  --quantization fp16

# Monitor deployment progress
nvidia-nemoclaw model status glm-5 --namespace Tenant-AI-Research --watch

# Expected output (after download and initialization):
# MODEL    NAMESPACE              STATUS     MEMORY    PORT    LATENCY
# glm-5    Tenant-AI-Research     running    38.2 GB   8001    ~150ms
```

### Step 3.3: Deploy DeepSeek-R1 in DevOps Namespace

```bash
# Deploy DeepSeek-R1 to the DevOps namespace
nvidia-nemoclaw model deploy deepseek-r1 \
  --namespace Tenant-DevOps \
  --memory 40GB \
  --replicas 1 \
  --port 8002 \
  --quantization fp16

# Monitor deployment
nvidia-nemoclaw model status deepseek-r1 --namespace Tenant-DevOps --watch

# Expected output:
# MODEL         NAMESPACE         STATUS     MEMORY    PORT    LATENCY
# deepseek-r1   Tenant-DevOps     running    39.5 GB   8002    ~200ms
```

### Step 3.4: Verify All Model Deployments

```bash
# List all deployed models
nvidia-nemoclaw model list --all-namespaces

# Expected output:
# MODEL         NAMESPACE              STATUS     MEMORY     PORT    REQUESTS
# glm-5         Tenant-AI-Research     running    38.2 GB    8001    0
# deepseek-r1   Tenant-DevOps          running    39.5 GB    8002    0

# Check overall resource utilization
nvidia-nemoclaw resources show

# Expected output:
# GPU Memory Allocation:
#   System reserved:     8.0 GB
#   Tenant-AI-Research:  38.2 GB / 50 GB (glm-5)
#   Tenant-DevOps:       39.5 GB / 50 GB (deepseek-r1)
#   Free:                42.3 GB
#
# Compute utilization:   ~5% (idle)
# Storage:               150 GB / 4 TB used

# Test model inference directly
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-5",
    "messages": [{"role": "user", "content": "Hello, what model are you?"}],
    "max_tokens": 100
  }'
```

---

## Phase 4: Deploy Agent Workers on DGX Spark

Now deploy OpenCode and OpenHands workers on the DGX Spark, running within the tenant namespaces so they have direct access to the GPU models.

### Step 4.1: Deploy OpenCode Worker in DevOps Namespace

```bash
# On the DGX Spark
nvidia-nemoclaw worker deploy opencode \
  --namespace Tenant-DevOps \
  --image opencode:latest \
  --memory 4GB \
  --cpu 2.0 \
  --port 3002 \
  --env "MODEL_ENDPOINT=http://localhost:8002" \
  --env "MODEL_NAME=deepseek-r1" \
  --env "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}" \
  --labels "role=coding-agent,tier=gpu"

# Alternatively, using Docker directly:
docker run -d \
  --name opencode-dgx \
  --gpus all \
  --memory 4g \
  --cpus 2.0 \
  -p 3002:3002 \
  -e MODEL_ENDPOINT=http://localhost:8002 \
  -e MODEL_NAME=deepseek-r1 \
  -e OPENROUTER_API_KEY=${OPENROUTER_API_KEY} \
  --restart unless-stopped \
  opencode:latest
```

### Step 4.2: Deploy OpenHands Worker in AI Research Namespace

```bash
nvidia-nemoclaw worker deploy openhands \
  --namespace Tenant-AI-Research \
  --image openhands:latest \
  --memory 4GB \
  --cpu 2.0 \
  --port 3000 \
  --env "MODEL_ENDPOINT=http://localhost:8001" \
  --env "MODEL_NAME=glm-5" \
  --env "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}" \
  --labels "role=dev-agent,tier=gpu"

# Or with Docker:
docker run -d \
  --name openhands-dgx \
  --gpus all \
  --memory 4g \
  --cpus 2.0 \
  -p 3000:3000 \
  -e MODEL_ENDPOINT=http://localhost:8001 \
  -e MODEL_NAME=glm-5 \
  -e OPENROUTER_API_KEY=${OPENROUTER_API_KEY} \
  --restart unless-stopped \
  openhands:latest
```

### Step 4.3: Verify Workers

```bash
# List all workers
nvidia-nemoclaw worker list --all-namespaces

# Expected output:
# WORKER      NAMESPACE              STATUS     MEMORY    CPU    PORT    UPTIME
# opencode    Tenant-DevOps          running    3.1 GB    0.5    3002    2m
# openhands   Tenant-AI-Research     running    3.4 GB    0.7    3000    1m

# Test workers from Minisforum
# From the Minisforum:
curl -s http://192.168.1.158:3002/health | jq .
curl -s http://192.168.1.158:3000/health | jq .
```

### Step 4.4: Connect DGX Workers to OpenClaw via ACP

Back on the Minisforum, configure OpenClaw to use the DGX Spark workers via ACP:

Edit `/etc/openclaw/openclaw.json` on the Minisforum:

```json
{
  "acp": {
    "agents": {
      "opencode-dgx": {
        "runtime": "acpx",
        "remote": true,
        "endpoint": "http://192.168.1.158:3002",
        "mode": "persistent",
        "resources": {
          "memory": "4g",
          "cpu": "2.0",
          "gpu": true
        },
        "env": {
          "MODEL_BACKEND": "dgx-local"
        },
        "labels": {
          "location": "dgx-spark",
          "tier": "gpu",
          "namespace": "Tenant-DevOps"
        }
      },
      "openhands-dgx": {
        "runtime": "acpx",
        "remote": true,
        "endpoint": "http://192.168.1.158:3000",
        "mode": "persistent",
        "resources": {
          "memory": "4g",
          "cpu": "2.0",
          "gpu": true
        },
        "labels": {
          "location": "dgx-spark",
          "tier": "gpu",
          "namespace": "Tenant-AI-Research"
        }
      }
    }
  },
  "agents": {
    "list": [
      {
        "name": "opencode-dgx",
        "type": "acp",
        "displayName": "OpenCode (DGX Spark GPU)",
        "description": "GPU-accelerated coding agent on DGX Spark with DeepSeek-R1",
        "runtime": {
          "type": "acp",
          "acp": {
            "agent": "opencode-dgx",
            "backend": "acpx",
            "mode": "persistent"
          }
        },
        "routing": {
          "preferFor": [
            "large-codebase-analysis",
            "complex-refactoring",
            "training-data-generation"
          ]
        }
      },
      {
        "name": "openhands-dgx",
        "type": "acp",
        "displayName": "OpenHands (DGX Spark GPU)",
        "description": "GPU-accelerated dev agent on DGX Spark with GLM-5",
        "runtime": {
          "type": "acp",
          "acp": {
            "agent": "openhands-dgx",
            "backend": "acpx",
            "mode": "persistent"
          }
        },
        "routing": {
          "preferFor": [
            "full-stack-development",
            "browser-heavy-tasks",
            "deployment-pipelines"
          ]
        }
      }
    ]
  }
}
```

### Step 4.5: Spawn and Test DGX Agents

```bash
# On the Minisforum, spawn DGX-based agents
/acp spawn opencode-dgx --mode persistent --thread auto
/acp spawn openhands-dgx --mode persistent --thread auto

# Check status
/acp status

# Expected output:
# ACP Agent Status
# +----------------+-----------+----------+---------+--------+-------+----------+
# | Agent          | Thread    | Mode     | Status  | Memory | CPU   | Location |
# +----------------+-----------+----------+---------+--------+-------+----------+
# | opencode       | thrd_abc  | persist  | running | 1.2GB  | 0.3   | local    |
# | openhands      | thrd_def  | persist  | running | 2.1GB  | 0.5   | local    |
# | opencode-dgx   | thrd_ghi  | persist  | running | 3.1GB  | 0.5   | dgx      |
# | openhands-dgx  | thrd_jkl  | persist  | running | 3.4GB  | 0.7   | dgx      |
# +----------------+-----------+----------+---------+--------+-------+----------+
```

---

## Phase 5: Install and Configure Ollama on DGX Spark

For maximum flexibility, also install Ollama on the DGX Spark for serving smaller models with GPU acceleration.

```bash
# On the DGX Spark
curl -fsSL https://ollama.com/install.sh | sh

# Configure Ollama to use GPU and listen on all interfaces
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_NUM_PARALLEL=4"
Environment="OLLAMA_MAX_LOADED_MODELS=3"
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ollama

# Pull commonly used models (GPU-accelerated)
ollama pull llama3.1:70b
ollama pull codellama:70b
ollama pull deepseek-coder-v2:33b

# Verify GPU is being used
ollama ps
# Should show GPU layers being utilized

# Test from Minisforum
curl -s http://192.168.1.158:11434/api/tags | jq '.models[].name'
```

---

## Phase 6: Configure Smart Model Routing

Set up OpenClaw on the Minisforum to intelligently route model requests:

```json
{
  "routing": {
    "strategy": "smart",
    "rules": [
      {
        "name": "gpu-large-models",
        "description": "Route large model requests to DGX Spark",
        "condition": {
          "or": [
            { "model.size": { "gte": "30b" } },
            { "model.name": { "match": "deepseek-*|glm-*|llama*:70b" } }
          ]
        },
        "backend": "dgx-spark",
        "fallback": "openrouter"
      },
      {
        "name": "cpu-small-models",
        "description": "Route small model requests to local Minisforum Ollama",
        "condition": {
          "model.size": { "lt": "30b" }
        },
        "backend": "local-ollama",
        "fallback": "dgx-spark"
      },
      {
        "name": "cloud-fallback",
        "description": "Use OpenRouter when local resources are exhausted",
        "condition": {
          "or": [
            { "backend.dgx-spark.status": "unhealthy" },
            { "backend.dgx-spark.memory.available": { "lt": "10GB" } }
          ]
        },
        "backend": "openrouter",
        "fallback": null
      }
    ],
    "defaults": {
      "timeout": 60000,
      "retries": 2,
      "retryDelay": 1000
    }
  }
}
```

---

## DGX Spark Resource Summary (After Full Setup)

```
NVIDIA DGX Spark -- 128 GB Unified Memory
+--------------------------------------------------------+
|                                                        |
|  System Reserved:     8 GB                             |
|                                                        |
|  Tenant-AI-Research: 50 GB allocated                   |
|    - GLM-5:          38.2 GB                           |
|    - OpenHands:      3.4 GB                            |
|    - Free:           8.4 GB                            |
|                                                        |
|  Tenant-DevOps:     50 GB allocated                    |
|    - DeepSeek-R1:    39.5 GB                           |
|    - OpenCode:       3.1 GB                            |
|    - Free:           7.4 GB                            |
|                                                        |
|  Unallocated:       20 GB                              |
|    - Ollama:         ~15 GB (dynamic)                  |
|    - System buffer:  ~5 GB                             |
|                                                        |
+--------------------------------------------------------+
```

---

## Troubleshooting

### NemoClaw init fails
```bash
# Check NVIDIA driver is working
nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# Reinstall nvidia-container-toolkit if needed
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Model deployment hangs
```bash
# Check NemoClaw logs
nvidia-nemoclaw logs --tail 100

# Check available memory
nvidia-nemoclaw resources show

# If memory is insufficient, reduce model quantization
nvidia-nemoclaw model deploy deepseek-r1 \
  --namespace Tenant-DevOps \
  --memory 30GB \
  --quantization int8  # Use int8 instead of fp16
```

### Minisforum cannot reach DGX NemoClaw API
```bash
# From Minisforum, test connectivity
curl -v http://192.168.1.158:8080/health

# Check DGX firewall
ssh newwaveclaw@192.168.1.158
sudo ufw status
sudo ufw allow 8080/tcp comment "NemoClaw API"

# Check NemoClaw is listening
sudo ss -tlnp | grep 8080
```

### Agent workers crash on startup
```bash
# Check worker logs
nvidia-nemoclaw worker logs opencode --namespace Tenant-DevOps --tail 50

# Or Docker logs if using Docker directly
docker logs opencode-dgx --tail 50

# Common issue: model endpoint not ready yet
# Solution: wait for model deployment to complete before starting workers
```

---

**Next step**: Proceed to `05_OPENROUTER_INTEGRATION.md` to configure cloud LLM fallback.
