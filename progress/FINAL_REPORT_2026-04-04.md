# AI Homelab Infrastructure Report
## April 4, 2026

**Prepared by**: Oluwajoba Malomo
**Project**: AI Homelab / Multi-Tenant AI Inference Platform

---

## Executive Summary

Built a production-ready, two-machine AI inference platform in a single day. The system serves multiple AI models locally on dedicated GPU hardware with cloud fallback, metered API access, and multi-agent orchestration. All infrastructure is accessible remotely via VPN from any location.

**Key Achievements:**
- Three-tier AI inference (local CPU, local GPU, cloud) with automatic fallback
- Metered API gateway with per-consumer authentication and rate limiting
- Multi-agent orchestration with smart model routing
- GPU-accelerated inference on NVIDIA DGX Spark (128 GB unified memory)
- Full monitoring stack (Prometheus + Grafana)
- Security hardening (firewall, fail2ban, API key auth, VPN-only access)

---

## Infrastructure Overview

### Hardware

| Machine | Role | Key Specs |
|---------|------|-----------|
| Minisforum X1 Pro 370 | Control Plane | AMD Ryzen AI 9 HX 370, 96 GB DDR5, 2 TB NVMe |
| NVIDIA DGX Spark | Compute Engine | GB10 Blackwell GPU, 128 GB unified memory, 4 TB NVMe |

### Architecture

```
                     INTERNET
                        |
                  [ Tailscale VPN ]
                        |
        +---------------+---------------+
        |                               |
   MINISFORUM                      DGX SPARK
   Control Plane                   Compute Engine
        |                               |
   OpenClaw (orchestrator)         Ollama (GPU models)
   OpenCode (coding agent)         OpenHands (dev agent)
   APISIX (API gateway)           NemoClaw (sandbox)
   Prometheus + Grafana            5 AI models loaded
        |                               |
        +--- OpenRouter (Cloud Fallback) ---+
```

### Services Running

**Minisforum (100.79.80.119)** - 5 containers + 1 systemd service:

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| OpenClaw Gateway | 18789 | Running | AI agent orchestrator |
| OpenCode | 3002 | Running | Coding agent worker |
| APISIX | 9080/9443 | Running | Metered API gateway |
| Prometheus | 9090 | Running | Metrics collection |
| Grafana | 3003 | Running | Monitoring dashboards |
| Ollama (CPU) | 11434 | Running | Lightweight model serving |

**DGX Spark (100.88.112.5)** - 2 containers + 1 systemd service:

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| OpenHands | 3000 | Running | GPU-accelerated dev agent |
| NemoClaw/OpenShell | 8080 | Running | Sandbox isolation |
| Ollama (GPU) | 11434 | Running | GPU model inference |

### AI Models Available

| Model | Size | Location | Use Case | Cost |
|-------|------|----------|----------|------|
| glm-4.7-flash | 19 GB | Minisforum CPU | Quick tasks, simple Q&A | Free |
| glm4:9b | 5.5 GB | DGX Spark GPU | Medium complexity | Free |
| deepseek-r1:32b-8k | 19 GB | DGX Spark GPU | Complex reasoning, coding | Free |
| deepseek-r1:70b-4k | 42 GB | DGX Spark GPU | Heavy reasoning | Free |
| Claude Sonnet 4.5 | Cloud | OpenRouter | Highest quality | $3/$15 per M tokens |
| DeepSeek R1 | Cloud | OpenRouter | Cloud reasoning | $0.55/$2.19 per M tokens |
| Nemotron Nano 30B | Cloud | OpenRouter | Free cloud fallback | Free |

---

## Smart Routing System

The platform automatically routes requests to the optimal model based on task complexity:

| Alias | Model | Tier | When Used |
|-------|-------|------|-----------|
| `fast` | glm-4.7-flash | Minisforum CPU | Simple questions, quick responses |
| `medium` | glm4:9b | DGX Spark GPU | Creative writing, analysis |
| `reasoning` | deepseek-r1:32b-8k | DGX Spark GPU | Complex coding, math, logic |
| `cloud` | DeepSeek R1 | OpenRouter | When local is unavailable |

**Automatic Fallback Chain:**
1. DGX Spark GPU (deepseek-r1:32b-8k) - primary
2. DGX Spark GPU (glm4:9b) - secondary
3. Minisforum CPU (glm-4.7-flash) - tertiary
4. OpenRouter Cloud (nemotron-3-nano-30b) - last resort

---

## Multi-Agent System

Three isolated agents configured in OpenClaw:

| Agent | Model | Workspace | Purpose |
|-------|-------|-----------|---------|
| main | deepseek-r1:32b-8k | default | Primary orchestrator |
| opencode-worker | deepseek-r1:32b-8k | workspace-opencode | Code generation, review, debugging |
| openhands-worker | glm4:9b | workspace-openhands | Full-stack dev, browser tasks |

---

## API Access & Metering

External applications access the platform through APISIX with API key authentication:

**Endpoint:** `http://<tailscale-ip>:9080/v1/chat/completions`

| Consumer | API Key | Rate Limit | Use Case |
|----------|---------|------------|----------|
| personal | homelab-personal-2026 | Unlimited | Owner access |
| app-a | app-a-research-2026 | 2 req/sec, burst 4 | Research pipeline |
| app-b | app-b-devops-2026 | 1 req/sec, burst 2 | DevOps automation |

**Security:**
- Requests without a valid API key are rejected (HTTP 401)
- Rate limiting prevents abuse (HTTP 429 when exceeded)
- All access requires Tailscale VPN connection

---

## Security Measures

| Layer | Measure | Status |
|-------|---------|--------|
| Network | Tailscale VPN (all remote access) | Active |
| Firewall | UFW on Minisforum (deny all, allow specific ports) | Active |
| SSH | fail2ban (auto-block brute force) | Active |
| SSH | Key-based authentication (DGX Spark) | Active |
| API | APISIX key-auth plugin | Active |
| API | Per-consumer rate limiting | Active |
| Sandbox | NemoClaw Landlock + seccomp + netns | Active |
| Updates | Unattended security updates | Active |
| Docker | Log rotation (10 MB cap) | Active |

---

## End-to-End Test Results

All 8 verification tests passed on April 4, 2026:

| # | Test | Result |
|---|------|--------|
| 1 | OpenClaw Gateway health check | PASS (200) |
| 2 | OpenCode worker responding | PASS (200) |
| 3 | DGX Spark GPU inference | PASS (200 + AI response) |
| 4 | Minisforum CPU inference | PASS (200 + AI response) |
| 5 | APISIX metered access (valid key) | PASS (200) |
| 6 | APISIX rejected access (no key) | PASS (401) |
| 7 | OpenRouter cloud inference | PASS (200) |
| 8 | OpenHands UI accessible | PASS (200) |

---

## Monitoring

| Dashboard | URL | Credentials |
|-----------|-----|-------------|
| Prometheus | http://100.79.80.119:9090 | None required |
| Grafana | http://100.79.80.119:3003 | admin / homelab2026 |
| OpenClaw Control UI | http://100.79.80.119:18789 | Token auth |
| OpenHands UI | http://100.88.112.5:3000 | None required |

All URLs require Tailscale VPN connection.

---

## Cost Analysis

| Component | One-Time Cost | Monthly Cost |
|-----------|--------------|-------------|
| Minisforum X1 Pro 370 | Hardware cost | ~$5 electricity |
| NVIDIA DGX Spark | Hardware cost | ~$10 electricity |
| Local GPU inference | $0 | $0 |
| OpenRouter (cloud fallback) | $0 | Usage-based (free tier available) |
| Tailscale | $0 | $0 (free tier) |

**Key insight:** All local inference is free after hardware investment. Cloud is only used as a fallback, minimizing ongoing costs.

---

## Next Steps

1. **Agent routing bindings** - Route specific channels/requests to specific agents automatically
2. **Webhook task delegation** - Async task handoff between OpenClaw and agent workers
3. **APISIX Prometheus metrics** - Complete monitoring pipeline with API usage dashboards
4. **OpenCode ARM64** - Build or find ARM-compatible image for DGX Spark
5. **Additional models** - Pull more specialized models for different use cases
6. **Grafana dashboards** - Build custom dashboards for GPU utilization, API usage, and cost tracking

---

*Report generated April 4, 2026. All systems verified operational.*
