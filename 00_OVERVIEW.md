# AI Homelab Architecture Overview

## Architecture Diagram

```
                          INTERNET
                             |
                      [ Tailscale VPN ]
                             |
         +---------+---------+---------+---------+
         |                                       |
  +------+------+                       +--------+--------+
  | MINISFORUM  |                       |  NVIDIA DGX     |
  | X1 Pro 370  |  <--- LAN (1Gbps) -->|  Spark          |
  | CONTROL     |   192.168.1.157 <->   |  COMPUTE        |
  | PLANE       |   192.168.1.158       |  ENGINE         |
  +------+------+                       +--------+--------+
         |                                       |
         |  +----------------------------------+ |
         |  |  Services (Docker / Systemd)     | |
         |  +----------------------------------+ |
         |                                       |
  +------+------+                       +--------+--------+
  | OpenClaw GW |                       | NemoClaw        |
  | :18789      |  --- ACP/Webhook ---> | (Tenant Mgmt)   |
  |             |                       |                  |
  | OpenHands   |                       | Ollama (GPU)    |
  | :3000       |                       | :11434          |
  |             |                       |                  |
  | OpenCode    |                       | Model Workers   |
  | :3002       |                       | GLM-5, DS-R1    |
  |             |                       |                  |
  | Ollama(CPU) |                       | OpenCode Agent  |
  | :11434      |                       | OpenHands Agent |
  |             |                       |                  |
  | APISIX      |                       |                  |
  | :9080/:9443 |                       |                  |
  +-------------+                       +-----------------+
         |
         +--- OpenRouter (Cloud LLM Gateway) ---> Anthropic, xAI, DeepSeek, etc.
```

## Hardware Role Assignment

| Attribute              | Minisforum X1 Pro 370         | NVIDIA DGX Spark              |
|------------------------|-------------------------------|-------------------------------|
| **Role**               | Control Plane / Orchestrator  | Compute Engine / GPU Inference|
| **CPU**                | AMD Ryzen AI 9 HX 370        | NVIDIA GB10 Grace Superchip   |
| **RAM**                | 96 GB DDR5                    | 128 GB Unified (CPU+GPU)      |
| **Storage**            | 2 TB NVMe SSD                | 4 TB NVMe                     |
| **GPU**                | Integrated (Radeon 890M)      | Blackwell GPU (1 PFLOP FP4)   |
| **LAN IP**             | 192.168.1.157                 | 192.168.1.158                 |
| **Tailscale IP**       | 100.79.80.119                 | TBD (after setup)             |
| **OS**                 | Ubuntu Linux (running)        | DGX OS (needs recovery)       |
| **User**               | newwaveclaw                   | TBD (after recovery)          |
| **Primary Services**   | OpenClaw, APISIX, Agents (lightweight), OpenRouter proxy | NemoClaw, Ollama (GPU), Large model inference, Agent workers |

## Software Stack Summary

| Software          | Purpose                              | Runs On        | Port(s)    |
|-------------------|--------------------------------------|----------------|------------|
| **OpenClaw**      | Multi-agent orchestrator / gateway   | Minisforum     | 18789      |
| **OpenCode**      | AI coding agent                      | Both           | 3002       |
| **OpenHands**     | AI dev agent (browser-based)         | Both           | 3000       |
| **Ollama**        | Local LLM serving                    | Both           | 11434      |
| **OpenRouter**    | Unified cloud LLM gateway            | Cloud (API)    | N/A        |
| **NemoClaw**      | Tenant isolation / model management  | DGX Spark      | varies     |
| **APISIX**        | API gateway with metering            | Minisforum     | 9080/9443  |

## Network Layout

### LAN Topology
```
Router (192.168.1.1)
  |
  +-- 192.168.1.157  Minisforum X1 Pro 370 (Control Plane)
  |
  +-- 192.168.1.158  NVIDIA DGX Spark (Compute Engine)
```

### Tailscale Overlay Network
```
100.79.80.119   Minisforum (enrolled)
100.x.x.x      DGX Spark (to be enrolled after recovery)
```

### Port Map (Minisforum)
| Port  | Service              | Protocol | Access         |
|-------|----------------------|----------|----------------|
| 22    | SSH                  | TCP      | LAN + Tailscale|
| 3000  | OpenHands            | TCP      | LAN + Tailscale|
| 3002  | OpenCode             | TCP      | LAN + Tailscale|
| 9080  | APISIX (HTTP)        | TCP      | LAN + Tailscale|
| 9090  | Webhook receiver     | TCP      | Internal       |
| 9443  | APISIX (HTTPS)       | TCP      | LAN + Tailscale|
| 11434 | Ollama               | TCP      | Internal       |
| 18789 | OpenClaw Gateway     | TCP      | LAN + Tailscale|

### Port Map (DGX Spark -- after setup)
| Port  | Service              | Protocol | Access         |
|-------|----------------------|----------|----------------|
| 22    | SSH                  | TCP      | LAN + Tailscale|
| 11434 | Ollama (GPU)         | TCP      | Internal       |
| 8080  | NemoClaw API         | TCP      | Internal       |

## Current State vs Target State

### Current State (Minisforum only)
```
[Minisforum 192.168.1.157]
  Docker containers (basic):
    - openclaw-gw        :18789  (running)
    - openhands-app      :3000   (running)
    - opencode-app       :3002   (running)
    - ollama             :11434  (running)

[DGX Spark 192.168.1.158]
    - LOCKED OUT (needs password reset via USB recovery)
    - No services running
```

### Target State (Full Homelab)
```
[Minisforum 192.168.1.157 -- Control Plane]
  OpenClaw (Ansible-managed, systemd):
    - openclaw-gateway   :18789  (orchestrator)
    - openhands-agent    :3000   (lightweight, sandbox-ready)
    - opencode-agent     :3002   (lightweight, sandbox-ready)
    - ollama             :11434  (CPU fallback models)
  APISIX:
    - api-gateway        :9080/:9443 (metering + auth)
  Security:
    - UFW firewall (ports restricted)
    - fail2ban (SSH protection)
  Integration:
    - OpenRouter (cloud LLM fallback)
    - ACP bridge to DGX Spark

[DGX Spark 192.168.1.158 -- Compute Engine]
  NemoClaw (tenant isolation):
    - Tenant-AI-Research namespace:
        - GLM-5 model (40GB VRAM)
        - OpenCode worker (ACP)
    - Tenant-DevOps namespace:
        - DeepSeek-R1 model (40GB VRAM)
        - OpenHands worker (ACP)
  Ollama (GPU-accelerated):
    - Large model serving
  Tailscale:
    - Mesh connectivity to Minisforum
```

## Setup Sequence

Follow the guides in numerical order:

1. `01_DGX_SPARK_RECOVERY.md` -- Factory reset DGX Spark (get access back)
2. `02_MINISFORUM_UPGRADE.md` -- Upgrade Minisforum from Docker to proper OpenClaw
3. `03_INTEGRATION_PATTERNS.md` -- Choose and configure agent integration
4. `04_DGX_SPARK_SETUP.md` -- Full DGX Spark deployment with NemoClaw
5. `05_OPENROUTER_INTEGRATION.md` -- Cloud LLM fallback via OpenRouter
6. `06_APISIX_METERING.md` -- API gateway with token/GPU metering
7. `07_RESOURCE_ALLOCATION.md` -- Capacity planning and optimization
8. `08_CHECKLIST.md` -- Printable step-by-step checklist

**Estimated total setup time:** 4-6 hours (assuming DGX recovery image is pre-downloaded).
