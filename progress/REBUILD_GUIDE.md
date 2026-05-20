# AI Homelab Rebuild Guide

A step-by-step guide to rebuild the entire AI homelab from scratch. Follow this guide top to bottom. Each step has the exact commands and the "why" behind them.

**Time estimate:** 2-3 hours (assuming both machines have their OS installed)
**Prerequisites:** Minisforum running Ubuntu 24.04, DGX Spark running DGX OS, both connected to same router via Ethernet/WiFi

---

## Phase 1: Network Access (30 min)

**Goal:** SSH into both machines from your Mac, from anywhere.

### Why Tailscale?
Your Mac, Minisforum, and DGX Spark may be on different networks (WiFi, hotspot, etc.). Tailscale creates a VPN overlay so they can always reach each other using fixed IPs.

### 1.1 Install Tailscale on Both Machines

On each machine (keyboard/monitor if SSH not yet available):
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# Opens a URL in browser. Log in to your Tailscale account. Approve the device.
tailscale ip -4
# Note this IP. Format: 100.x.x.x
```

### 1.2 Generate SSH Key on Your Mac

```bash
ssh-keygen -t ed25519
# Press Enter for all prompts (default location, no passphrase)
```

### 1.3 Copy SSH Key to Both Machines

```bash
ssh-copy-id <minisforum-user>@<minisforum-tailscale-ip>
ssh-copy-id <spark-user>@<spark-tailscale-ip>
```

This asks for the password one last time. After this, SSH is passwordless.

### 1.4 Set Up Passwordless Sudo

On each machine:
```bash
echo "<username> ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/<username>
```

### 1.5 Set Up Cross-Machine SSH Keys

From the Minisforum:
```bash
ssh-keygen -t ed25519
ssh-copy-id <spark-user>@<spark-tailscale-ip>
```

This lets the Minisforum SSH into the Spark without a password (needed for the architecture).

### 1.6 Verify Everything

From your Mac:
```bash
ssh <minisforum-user>@<minisforum-tailscale-ip> "hostname && sudo whoami"
ssh <spark-user>@<spark-tailscale-ip> "hostname && sudo whoami"
ssh <minisforum-user>@<minisforum-tailscale-ip> "ssh <spark-user>@<spark-tailscale-ip> hostname"
```

All three should work with no password prompts.

---

## Phase 2: DGX Spark Setup (30 min)

**Goal:** GPU verified, Docker working, Ollama serving models.

### 2.1 Verify GPU

```bash
nvidia-smi
# Should show NVIDIA GB10 GPU with driver and CUDA version
```

### 2.2 Verify Docker with GPU Access

```bash
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
# Should show the same GPU info inside the container
```

If Docker permission denied:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### 2.3 Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2.4 Configure Ollama for Network Access

This is critical. Without this, only the Spark itself can reach Ollama.

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
echo '[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_NUM_PARALLEL=4"
Environment="OLLAMA_MAX_LOADED_MODELS=3"' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl enable --now ollama
```

**Why 0.0.0.0?** Default is localhost only. 0.0.0.0 means "listen on all interfaces" so the Minisforum can reach it via Tailscale.

### 2.5 Pull Models

```bash
ollama pull glm4:9b           # 5.5 GB, fast, general purpose
ollama pull deepseek-r1:32b   # 19 GB, powerful reasoning
```

### 2.6 Create Context-Limited Variants

**Why?** Large models with default context (524K tokens) allocate huge KV caches that exceed the GPU memory. Limiting context to 8K keeps memory usage reasonable.

```bash
echo 'FROM deepseek-r1:32b
PARAMETER num_ctx 8192' > /tmp/Modelfile
ollama create deepseek-r1:32b-8k -f /tmp/Modelfile
```

### 2.7 Verify Models Work

```bash
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-r1:32b-8k","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":20}'
# Should return a JSON response with the answer
```

### 2.8 Install NemoClaw

```bash
# Install Node.js 22
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# Clone and install NemoClaw
cd ~
git clone https://github.com/NVIDIA/NemoClaw.git
cd NemoClaw
npm install
sudo npm install -g .
nemoclaw --version
```

### 2.9 Run NemoClaw Onboarding

```bash
nemoclaw onboard
# Accept license
# Inference: Choose "Local Ollama" (option 7)
# Model: Choose glm4:9b (small, loads fast)
# Brave Search: No
# Sandbox name: my-assistant
# Presets: pypi, npm
```

### 2.10 Deploy OpenHands

```bash
docker pull ghcr.io/all-hands-ai/openhands:0.44
docker run -d --name openhands-dgx --gpus all -p 3000:3000 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -e LLM_MODEL=deepseek-r1:32b-8k \
  -e LLM_API_KEY=ollama \
  --add-host host.docker.internal:host-gateway \
  --restart unless-stopped \
  ghcr.io/all-hands-ai/openhands:0.44
```

**Why host.docker.internal?** Containers can't use localhost to reach the host. This special DNS name resolves to the host machine.

---

## Phase 3: Minisforum Setup (45 min)

**Goal:** OpenClaw installed, gateway running, firewall configured.

### 3.1 Fix NodeSource Conflict (if it exists)

```bash
ls /etc/apt/sources.list.d/ | grep -i node
# If you see BOTH nodesource.list AND nodesource.sources, remove one:
sudo rm /etc/apt/sources.list.d/nodesource.sources
sudo apt update
```

### 3.2 Install OpenClaw via Ansible

```bash
curl -fsSL https://raw.githubusercontent.com/openclaw/openclaw-ansible/main/install.sh | bash
```

**What this installs:** OpenClaw binary, openclaw system user (UID 999), Docker, UFW firewall, fail2ban, Node.js, pnpm

### 3.3 Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl start ollama
ollama pull glm-4.7-flash    # 19 GB, lightweight CPU model
```

**Why a separate model here?** The Minisforum has no real GPU. glm-4.7-flash runs on CPU for quick, lightweight tasks. Heavy tasks go to the DGX Spark.

### 3.4 Run OpenClaw Onboarding

```bash
sudo su - openclaw
openclaw onboard --install-daemon
```

**Choices:**
- Setup mode: QuickStart
- Model provider: Ollama
- Ollama mode: Local (not Cloud + Local)
- Default model: Keep current
- Channel: Skip for now
- Web search: Skip for now
- Skills: No
- Hooks: Skip for now
- Hatch: Choose "Hatch in TUI", then Ctrl+C to exit after it starts

### 3.5 Change Gateway Bind to LAN

By default, OpenClaw only listens on localhost. The DGX Spark needs to reach it.

```bash
openclaw config set gateway.bind "lan"
openclaw daemon restart
```

**Why "lan" not "0.0.0.0"?** OpenClaw uses mode names, not raw IPs. "lan" = listen on all interfaces.

### 3.6 Configure Firewall

```bash
exit  # Back to regular user
sudo ufw allow 18789/tcp comment "OpenClaw Gateway"
sudo ufw allow 3000/tcp comment "OpenHands Agent UI"
sudo ufw allow 3002/tcp comment "OpenCode Agent UI"
sudo ufw allow in on tailscale0
sudo ufw allow from <spark-tailscale-ip> comment "DGX Spark Tailscale"
sudo ufw allow 9080/tcp comment "APISIX HTTP"
sudo ufw allow 9443/tcp comment "APISIX HTTPS"
```

### 3.7 Deploy OpenCode

```bash
docker run -d --name opencode-app --restart unless-stopped -p 3002:3002 \
  -e OLLAMA_BASE_URL=http://<spark-tailscale-ip>:11434 \
  -e LLM_MODEL=deepseek-r1:32b-8k \
  opencode:local serve --hostname 0.0.0.0 --port 3002
```

**Why "serve" args?** OpenCode is a TUI by default. The "serve" command makes it a web service that can receive tasks from OpenClaw.

**Note:** If you don't have the opencode:local image, you'll need to build it or pull it from wherever it was originally sourced.

---

## Phase 4: Connect the Machines (15 min)

**Goal:** Minisforum's OpenClaw knows about DGX Spark's models.

### 4.1 Verify Cross-Machine Connectivity

From the Minisforum:
```bash
curl -s http://<spark-tailscale-ip>:11434/api/tags
# Should list all models on the DGX Spark
```

### 4.2 Edit OpenClaw Config

The config is at `/home/openclaw/.openclaw/openclaw.json`. SSH terminal mangles multi-line pastes, so write files on your Mac and SCP them.

Add the `dgx-ollama` provider inside `models.providers`:

```json
"dgx-ollama": {
  "baseUrl": "http://<spark-tailscale-ip>:11434",
  "api": "ollama",
  "apiKey": "OLLAMA_API_KEY",
  "models": [
    {
      "id": "deepseek-r1:32b-8k",
      "name": "deepseek-r1:32b-8k",
      "reasoning": true,
      "input": ["text"],
      "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
      "contextWindow": 8192,
      "maxTokens": 8192
    },
    {
      "id": "glm4:9b",
      "name": "glm4:9b",
      "reasoning": false,
      "input": ["text"],
      "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
      "contextWindow": 128000,
      "maxTokens": 8192
    }
  ]
}
```

### 4.3 Upload Config

```bash
# From Mac
scp openclaw.json <minisforum-user>@<minisforum-tailscale-ip>:/tmp/openclaw.json

# On Minisforum
sudo cp /tmp/openclaw.json /home/openclaw/.openclaw/openclaw.json
sudo chown openclaw:openclaw /home/openclaw/.openclaw/openclaw.json
sudo su - openclaw
openclaw daemon restart
```

### 4.4 Verify

```bash
curl -s http://127.0.0.1:18789/health
# {"ok":true,"status":"live"}
```

---

## Phase 5: Add OpenRouter Cloud Fallback (10 min)

**Goal:** When local models are down or busy, requests go to the cloud.

### 5.1 Get an API Key

Go to https://openrouter.ai/settings/keys and create one.

### 5.2 Add to Config

Add the `openrouter` provider inside `models.providers`:

```json
"openrouter": {
  "baseUrl": "https://openrouter.ai/api/v1",
  "api": "openai-responses",
  "apiKey": "<your-openrouter-key>",
  "models": [
    {
      "id": "anthropic/claude-sonnet-4-5",
      "name": "Claude Sonnet 4.5",
      "reasoning": false,
      "input": ["text"],
      "cost": { "input": 3, "output": 15, "cacheRead": 0, "cacheWrite": 0 },
      "contextWindow": 200000,
      "maxTokens": 64000
    },
    {
      "id": "nvidia/nemotron-3-nano-30b-a3b:free",
      "name": "Nemotron Nano 30B (Free)",
      "reasoning": false,
      "input": ["text"],
      "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
      "contextWindow": 131072,
      "maxTokens": 32000
    }
  ]
}
```

**Key note:** The `api` field MUST be `openai-responses` (not `openai`). OpenClaw validates this strictly.

### 5.3 Upload and Restart

Same SCP + restart process as Phase 4.

---

## Phase 6: Smart Routing (10 min)

**Goal:** Model aliases for easy use, automatic fallback chain.

### 6.1 Add Aliases

As the openclaw user:
```bash
openclaw models aliases add fast ollama/glm-4.7-flash
openclaw models aliases add medium dgx-ollama/glm4:9b
openclaw models aliases add reasoning dgx-ollama/deepseek-r1:32b-8k
openclaw models aliases add cloud openrouter/deepseek/deepseek-r1
```

### 6.2 Add Fallback Chain

```bash
openclaw models fallbacks add dgx-ollama/deepseek-r1:32b-8k
openclaw models fallbacks add dgx-ollama/glm4:9b
openclaw models fallbacks add ollama/glm-4.7-flash
openclaw models fallbacks add openrouter/nvidia/nemotron-3-nano-30b-a3b:free
```

**Why this order?** Free GPU first, then free CPU, then free cloud. Paid cloud is available via aliases but not in the auto-fallback.

### 6.3 Set Default Model

```bash
openclaw models set dgx-ollama/deepseek-r1:32b-8k
```

### 6.4 Add Agent Workers

```bash
openclaw agents add opencode-worker \
  --workspace /home/openclaw/.openclaw/workspace-opencode \
  --model dgx-ollama/deepseek-r1:32b-8k

openclaw agents add openhands-worker \
  --workspace /home/openclaw/.openclaw/workspace-openhands \
  --model dgx-ollama/glm4:9b

openclaw daemon restart
```

---

## Phase 7: APISIX API Gateway (20 min)

**Goal:** Metered API access with authentication and rate limiting.

### 7.1 Install APISIX

```bash
curl -sL https://run.api7.ai/apisix/quickstart | sh
```

**If APISIX fails to start** (can't reach etcd), get the config and fix it:
```bash
docker cp apisix-quickstart:/usr/local/apisix/conf/config.yaml /tmp/apisix-config.yaml

# Change allow_admin to allow host access
sed -i 's/- 127.0.0.0\/24/- 0.0.0.0\/0/' /tmp/apisix-config.yaml

# Recreate with fixed config
docker stop apisix-quickstart && docker rm apisix-quickstart
docker run -d --name apisix-quickstart \
  --network apisix-quickstart-net \
  -p 9080:9080 -p 9443:9443 -p 9180:9180 -p 9091:9091 \
  -v /tmp/apisix-config.yaml:/usr/local/apisix/conf/config.yaml:ro \
  --ulimit nofile=65536:65536 \
  apache/apisix:3.15.0-ubuntu
```

### 7.2 Find the Admin Key

```bash
grep -A2 "admin_key:" /tmp/apisix-config.yaml
# The key value is what you use for X-API-KEY header
```

### 7.3 Change Admin Key to Secure One

```bash
NEW_KEY=$(openssl rand -hex 32)
echo "New admin key: $NEW_KEY"
sed -i "s/<old-key>/$NEW_KEY/" /tmp/apisix-config.yaml
# Recreate the container with the new config (same docker run command as above)
```

### 7.4 Create the Inference Route

```bash
export APISIX_KEY="<your-admin-key>"
curl -X PUT http://127.0.0.1:9180/apisix/admin/routes/dgx-inference \
  -H "X-API-KEY: $APISIX_KEY" \
  -H "Content-Type: application/json" \
  -d '{"uri":"/v1/chat/completions","name":"dgx-inference-metered","methods":["POST"],"upstream":{"type":"roundrobin","nodes":{"<spark-tailscale-ip>:11434":1},"timeout":{"connect":5,"send":120,"read":120}},"plugins":{"key-auth":{"header":"X-API-Key"},"response-rewrite":{"headers":{"set":{"X-Metered-By":"apisix-homelab"}}}}}'
```

### 7.5 Create Consumers

```bash
# Personal (unlimited)
curl -X PUT http://127.0.0.1:9180/apisix/admin/consumers/personal \
  -H "X-API-KEY: $APISIX_KEY" -H "Content-Type: application/json" \
  -d '{"username":"personal","desc":"Homelab owner","plugins":{"key-auth":{"key":"homelab-personal-2026"}}}'

# App A (rate limited)
curl -X PUT http://127.0.0.1:9180/apisix/admin/consumers/app-a \
  -H "X-API-KEY: $APISIX_KEY" -H "Content-Type: application/json" \
  -d '{"username":"app-a","desc":"App A","plugins":{"key-auth":{"key":"app-a-research-2026"},"limit-req":{"rate":2,"burst":4,"rejected_code":429,"key":"consumer_name"}}}'
```

---

## Phase 8: Monitoring + Hardening (15 min)

### 8.1 Prometheus + Grafana

Write a prometheus.yml config and SCP it to ~/monitoring/ on the Minisforum:

```yaml
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

```bash
docker run -d --name prometheus --restart unless-stopped -p 9090:9090 \
  -v ~/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro \
  --add-host host.docker.internal:host-gateway prom/prometheus:latest

docker run -d --name grafana --restart unless-stopped -p 3003:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=homelab2026 \
  --add-host host.docker.internal:host-gateway grafana/grafana:latest
```

In Grafana (http://<minisforum-ip>:3003, admin/homelab2026):
- Connections > Data Sources > Add Prometheus
- URL: http://host.docker.internal:9090
- Save & Test

### 8.2 Docker Log Rotation (Both Machines)

```bash
echo '{"log-driver":"json-file","log-opts":{"max-size":"10m","max-file":"3"}}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker
```

**Why?** Without this, Docker logs grow forever and eventually fill your disk.

---

## Phase 9: Verification (10 min)

Run these 8 tests. All should pass:

| # | Test | Command | Expected |
|---|------|---------|----------|
| 1 | OpenClaw health | `curl -s http://127.0.0.1:18789/health` | `{"ok":true,"status":"live"}` |
| 2 | OpenCode worker | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3002` | 200 |
| 3 | DGX GPU inference | `curl -s http://<spark-ip>:11434/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"deepseek-r1:32b-8k","messages":[{"role":"user","content":"Hi"}],"max_tokens":10}'` | 200 + response |
| 4 | CPU inference | `curl -s http://127.0.0.1:11434/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"glm-4.7-flash","messages":[{"role":"user","content":"Hi"}],"max_tokens":10}'` | 200 + response |
| 5 | APISIX with key | `curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:9080/v1/chat/completions -H "X-API-Key: homelab-personal-2026" -H "Content-Type: application/json" -d '{"model":"glm4:9b","messages":[{"role":"user","content":"Hi"}],"max_tokens":5}'` | 200 |
| 6 | APISIX no key | Same as above without X-API-Key header | 401 |
| 7 | OpenRouter cloud | `curl -s -o /dev/null -w "%{http_code}" https://openrouter.ai/api/v1/chat/completions -H "Authorization: Bearer <key>" -H "Content-Type: application/json" -d '{"model":"nvidia/nemotron-3-nano-30b-a3b:free","messages":[{"role":"user","content":"Hi"}],"max_tokens":5}'` | 200 |
| 8 | OpenHands UI | `curl -s -o /dev/null -w "%{http_code}" http://<spark-ip>:3000` | 200 |

---

## Common Problems and Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| SSH password keeps failing | Wrong username (newwave-dgx vs newwave-gdx) | Check exact username with `whoami` on the machine |
| SSH terminal mangles pastes | Long lines wrap and break | Write files on Mac, SCP them over |
| `apt update` fails with Signed-By conflict | Duplicate NodeSource repo files | `sudo rm /etc/apt/sources.list.d/nodesource.sources` |
| openclaw user can't sudo | System user has no password | Install packages as regular user first, then `sudo su - openclaw` |
| Ollama model OOM crash | KV cache too large (default 524K context) | Create model variant with `PARAMETER num_ctx 8192` |
| OpenClaw config validation error | Missing required fields or wrong enum value | All provider fields must be set together. `api` must be exact enum value. |
| OpenClaw rejects `gateway.bind "0.0.0.0"` | Legacy format | Use `"lan"` instead |
| APISIX admin returns 403 | Wrong admin key or IP not allowed | Check config.yaml for actual key. Set `allow_admin: ["0.0.0.0/0"]` |
| OpenCode container runs but port unreachable | Missing `serve` command args | Add `serve --hostname 0.0.0.0 --port 3002` after the image name |
| x86 Docker image on DGX Spark | ARM vs x86 mismatch | DGX Spark is ARM64. x86 images show `exec format error`. |
| Docker containers gone after restart | Containers not set to `--restart unless-stopped` | Recreate with restart policy, or `docker start <name>` |

---

## Architecture Summary

```
Mac (anywhere via Tailscale)
  |
  +-- Minisforum (CONTROL PLANE)
  |     OpenClaw Gateway    :18789  [orchestrator, 3 agents]
  |     OpenCode            :3002   [coding agent, serve mode]
  |     APISIX              :9080   [metered API gateway]
  |     Ollama (CPU)        :11434  [glm-4.7-flash]
  |     Prometheus          :9090   [metrics]
  |     Grafana             :3003   [dashboards]
  |     UFW + fail2ban              [security]
  |
  +-- DGX Spark (COMPUTE ENGINE)
  |     OpenHands           :3000   [dev agent, GPU]
  |     NemoClaw            :8080   [sandbox manager]
  |     Ollama (GPU)        :11434  [deepseek-r1:32b-8k, glm4:9b]
  |
  +-- OpenRouter (CLOUD FALLBACK)
        Claude, DeepSeek, Nemotron (free)
```
