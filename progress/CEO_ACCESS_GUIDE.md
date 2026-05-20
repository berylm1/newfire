# AI Homelab — CEO Access Guide

**Prepared by**: Oluwajoba Malomo
**Date**: April 4, 2026
**Classification**: Confidential — Do not share beyond authorized personnel

---




## What Is This?

A two-machine AI inference platform that serves large language models locally on dedicated hardware, with cloud fallback and metered API access. This system runs AI models on our own GPU hardware instead of paying per-request to cloud providers.

### Why It Matters

- **Cost savings**: Local GPU inference is free after hardware cost
- **Privacy**: Data stays on our hardware, never leaves the network
- **Control**: We manage the models, API keys, and access quotas
- **Availability**: Three-tier fallback ensures AI is always accessible

---

## System Overview

```
                    INTERNET
                       |
                 [ Tailscale VPN ]
                       |
       +---------------+---------------+
       |                               |
  MINISFORUM                      DGX SPARK
  Control Plane                   Compute Engine
  100.79.80.119                   100.88.112.5
       |                               |
  OpenClaw (orchestrator)         Ollama (GPU models)
  APISIX (API gateway)           NemoClaw (sandboxing)
  Ollama (lightweight CPU)       NVIDIA GB10 GPU
       |                               |
       +--- OpenRouter (Cloud Fallback) ---+
```

---



## How to Access

### Prerequisites

1. **Tailscale** must be installed on your device: https://tailscale.com/download
2. You must be added to the Tailscale network (ask Oluwajoba to authorize your device)
3. An SSH client (Terminal on Mac, or PuTTY on Windows)

### Step 1: Connect to Tailscale

Open Tailscale on your device and sign in. Once connected, you have access to both machines from anywhere.

### Step 2: SSH into the Machines

**Minisforum (Control Plane)**
```bash
ssh newwaveclaw@100.79.80.119
```
Password: *NewWave4113*

**DGX Spark (Compute Engine)**
```bash
ssh newwave-dgx@100.88.112.5
```password: Newwave392
Authentication: SSH key required *(Oluwajoba will add your key)*

### Step 3: Access the Web Dashboards

Once on Tailscale, open these URLs in your browser:

| Dashboard | URL | Authentication |
|-----------|-----|----------------|
| OpenClaw Control UI | `http://100.79.80.119:18789` | Token (see below) |
| OpenClaw (with token) | `http://100.79.80.119:18789/#token=abf1424463378953cec5624c816ffc121a13eaf7cea650ed` | Auto-authenticated |

---

## Using the AI API

### Direct Access (via APISIX Gateway)

Send AI inference requests through the metered API gateway:

```bash
curl -X POST http://100.79.80.119:9080/v1/chat/completions \
  -H "X-API-Key: homelab-personal-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1:32b-8k",
    "messages": [{"role": "user", "content": "Summarize the key points of our Q1 report"}],
    "max_tokens": 500
  }'
```

### Available Models

| Model | Where It Runs | Best For | Cost |
|-------|--------------|----------|------|
| `glm-4.7-flash` | Minisforum CPU | Quick questions, simple tasks | Free |
| `glm4:9b` | DGX Spark GPU | Medium complexity tasks | Free |
| `deepseek-r1:32b-8k` | DGX Spark GPU | Complex reasoning, analysis | Free |
| `anthropic/claude-sonnet-4-5` | OpenRouter Cloud | Highest quality responses | Paid |
| `nvidia/nemotron-3-nano-30b-a3b:free` | OpenRouter Cloud | Free cloud fallback | Free |

### API Key

Your personal API key for the APISIX gateway:

```
homelab-personal-2026
```

Include it in the `X-API-Key` header with every request. Requests without a valid key are rejected (HTTP 401).

---

## Checking System Health

### Quick Health Checks (from any Tailscale-connected device)

**Is the gateway up?**
```bash
curl -s http://100.79.80.119:18789/health
# Expected: {"ok":true,"status":"live"}
```

**Is the DGX Spark serving models?**
```bash
curl -s http://100.88.112.5:11434/api/tags
# Expected: JSON listing available models
```

**Test a model response:**
```bash
curl -s http://100.79.80.119:9080/v1/chat/completions \
  -H "X-API-Key: homelab-personal-2026" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-r1:32b-8k","messages":[{"role":"user","content":"Hello"}],"max_tokens":10}'
# Expected: JSON response with AI-generated text
```

### Detailed Health (SSH required)

**Minisforum:**
```bash
ssh newwaveclaw@100.79.80.119

# Check OpenClaw
sudo su - openclaw
openclaw daemon status
exit

# Check containers
docker ps

# Check firewall
sudo ufw status

# Check system resources
free -h
df -h
```

**DGX Spark:**
```bash
ssh newwave-dgx@100.88.112.5

# Check GPU
nvidia-smi

# Check models loaded
ollama ps

# Check NemoClaw sandbox
nemoclaw my-assistant status

# Check system resources
free -h
df -h
```

---

## Architecture Details

### Machines

| | Minisforum X1 Pro 370 | NVIDIA DGX Spark |
|---|---|---|
| **Role** | Control Plane / Orchestrator | Compute Engine / GPU Inference |
| **CPU** | AMD Ryzen AI 9 HX 370 (12c/24t) | NVIDIA GB10 Grace (Arm, 10c) |
| **RAM** | 96 GB DDR5 | 128 GB Unified (CPU+GPU) |
| **Storage** | 2 TB NVMe | 4 TB NVMe |
| **GPU** | Integrated (not used) | Blackwell GB10 (1 PFLOP FP4) |
| **OS** | Ubuntu 24.04 | Ubuntu 24.04 (DGX OS 7.5.0) |

### Software Running

**Minisforum:**
- OpenClaw 2026.4.2 — AI agent orchestrator and gateway
- APISIX 3.15.0 — API gateway with key auth and metering
- Ollama — serves glm-4.7-flash on CPU
- UFW firewall — restricts incoming connections
- fail2ban — blocks SSH brute force attempts

**DGX Spark:**
- NemoClaw 0.0.6 — sandbox and agent isolation manager
- Ollama — serves GPU-accelerated models (deepseek-r1:32b-8k, glm4:9b)
- Tailscale — VPN connectivity

### Security

- All external access requires Tailscale VPN connection
- API requests require a valid API key (401 rejection otherwise)
- SSH is protected by fail2ban (auto-blocks after failed attempts)
- UFW firewall restricts open ports to only what's needed
- DGX Spark firewall is inactive (relies on Tailscale network isolation)
- NemoClaw sandboxes run with Landlock + seccomp + network namespace isolation

---

## Setting Up CEO Access (Step-by-Step for Oluwajoba)

Follow these steps to give the CEO full access to the system.

### Step 1: Add CEO's Device to Tailscale

1. Have the CEO install Tailscale on their device: https://tailscale.com/download
2. They sign in — their device will appear in the Tailscale admin console
3. Approve their device in the Tailscale admin panel

### Step 2: Generate CEO's SSH Key (on CEO's machine)

The CEO runs this on their laptop/desktop:

```bash
ssh-keygen -t ed25519
# Press Enter for all prompts
```

Then send you the public key:

```bash
cat ~/.ssh/id_ed25519.pub
# Copy the entire output and send to Oluwajoba
```

### Step 3: Add CEO's SSH Key to Both Machines (Oluwajoba runs these)

**On the Minisforum:**
```bash
ssh newwaveclaw@100.79.80.119
echo "PASTE_CEO_PUBLIC_KEY_HERE" | sudo tee -a /home/newwaveclaw/.ssh/authorized_keys
```

**On the DGX Spark:**
```bash
ssh newwave-dgx@100.88.112.5
echo "PASTE_CEO_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
```

### Step 4: Set Up Passwordless Sudo for CEO (Optional)

If the CEO needs sudo access without passwords:

**On the Minisforum:**
```bash
echo "newwaveclaw ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/newwaveclaw
```

**On the DGX Spark:**
```bash
echo "newwave-dgx ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/newwave-dgx
```

Note: These are already configured for Oluwajoba's access. The CEO will use the same user accounts (`newwaveclaw` / `newwave-dgx`) since SSH key auth identifies who is connecting.

### Step 5: Create a Dedicated API Key for CEO (Optional)

If the CEO wants their own metered API key:

```bash
ssh newwaveclaw@100.79.80.119
export APISIX_KEY="fqGntGZRtgBoCdhBpDSkrrNhHbcPQHha"
curl -X PUT http://127.0.0.1:9180/apisix/admin/consumers/ceo \
  -H "X-API-KEY: $APISIX_KEY" \
  -H "Content-Type: application/json" \
  -d '{"username":"ceo","desc":"CEO Access","plugins":{"key-auth":{"key":"ceo-access-2026"}}}'
```

Then the CEO can use the API with:
```bash
curl -X POST http://100.79.80.119:9080/v1/chat/completions \
  -H "X-API-Key: ceo-access-2026" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-r1:32b-8k","messages":[{"role":"user","content":"Hello"}],"max_tokens":100}'
```

### Step 6: Verify CEO Access

Have the CEO test from their device:

```bash
# SSH into Minisforum
ssh newwaveclaw@100.79.80.119

# SSH into DGX Spark
ssh newwave-dgx@100.88.112.5

# Test API
curl -X POST http://100.79.80.119:9080/v1/chat/completions \
  -H "X-API-Key: ceo-access-2026" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-r1:32b-8k","messages":[{"role":"user","content":"Hello"}],"max_tokens":10}'
```

---

## Requesting Access for Other Team Members

To grant additional people access:

1. **Tailscale**: Add their device to the Tailscale network
2. **SSH Key**: Add their public SSH key to both machines (consider creating a separate user account for them)
3. **API Key**: Create a new APISIX consumer with rate limits specific to their role

Only Oluwajoba should perform these steps. Contact him to request access for new team members.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Can't reach any URL | Not connected to Tailscale | Open Tailscale app, sign in |
| SSH connection refused | Machine is off or Tailscale is down | Check if machine is powered on |
| API returns 401 | Wrong or missing API key | Check `X-API-Key` header |
| Model gives "not found" error | Model not loaded on that machine | SSH in and run `ollama list` |
| Slow responses | Large model loading into GPU memory | Wait 30-60 seconds, retry |
| Gateway health check fails | OpenClaw daemon stopped | SSH in, `sudo su - openclaw`, `openclaw daemon start` |
| APISIX returns 502 | DGX Spark Ollama is down | SSH into Spark, `sudo systemctl restart ollama` |

---

## Contact

For any access issues, system problems, or questions:

**Oluwajoba Malomo** — System Administrator
