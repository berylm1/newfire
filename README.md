# NewFire

NewFire is a two-machine AI homelab that hosts the NewFire AI platform. It pairs a Minisforum X1 Pro 370 (control plane) with an NVIDIA DGX Spark (GPU compute) to run local LLMs, agent orchestrators, and tenant-aware API metering for production workloads.

Target launch: **May 1, 2026.**

## Architecture at a Glance

| Role | Machine | Specs | Primary Services |
|------|---------|-------|------------------|
| Control Plane | Minisforum X1 Pro 370 | Ryzen AI 9 HX 370, 96 GB DDR5, 2 TB NVMe | OpenClaw, APISIX, OpenHands, OpenCode, Ollama (CPU) |
| Compute Engine | NVIDIA DGX Spark | GB10 Grace Blackwell, 128 GB unified, 4 TB NVMe | NemoClaw, Ollama (GPU), vLLM, model workers |

The two nodes connect over 1 Gbps LAN (192.168.1.157 and 192.168.1.158) and are remoted via Tailscale plus a self-hosted zrok2 + OpenZiti overlay. OpenRouter is wired in as a fallback cloud LLM gateway.

See `AI_Homelab_Architecture.png` / `.svg` / `.pdf` for the full diagram.

## Documentation

The numbered docs in this repo walk through the build in order:

1. [`00_OVERVIEW.md`](00_OVERVIEW.md) Architecture overview, hardware roles, software stack, network layout
2. [`01_DGX_SPARK_RECOVERY.md`](01_DGX_SPARK_RECOVERY.md) Recovery procedure for the DGX Spark node
3. [`02_MINISFORUM_UPGRADE.md`](02_MINISFORUM_UPGRADE.md) Minisforum upgrade and hardening steps
4. [`03_INTEGRATION_PATTERNS.md`](03_INTEGRATION_PATTERNS.md) Cross-node integration patterns (ACP, webhooks, message bus)
5. [`04_DGX_SPARK_SETUP.md`](04_DGX_SPARK_SETUP.md) Fresh setup for the DGX Spark
6. [`05_OPENROUTER_INTEGRATION.md`](05_OPENROUTER_INTEGRATION.md) OpenRouter proxy and key management
7. [`06_APISIX_METERING.md`](06_APISIX_METERING.md) APISIX gateway with per-tenant metering
8. [`07_RESOURCE_ALLOCATION.md`](07_RESOURCE_ALLOCATION.md) CPU, RAM, and VRAM budgets per service
9. [`08_CHECKLIST.md`](08_CHECKLIST.md) Pre-launch checklist

Supporting material:

- `NewFire_Gap_Map.svg`, `NewFire_Gap_Graph.svg` Eight-layer framework gap map (data and no-code builder are the largest current gaps)
- `blueprint/` Canonical AI Operating System blueprint (8 layers, 5 agents, 7 maturity levels)
- `progress/` Per-initiative progress logs that resume across sessions
- `scripts/` Operational scripts for both nodes
- `newfire_backend_docker/` Backend service that coordinates Paperclip, OpenClaw, APISIX, and NemoClaw with smart routing
- `newfire-db-backup-20260417.sql` Database snapshot from 2026-04-17

## Software Stack

| Component | Purpose | Host | Port |
|-----------|---------|------|------|
| OpenClaw | Multi-agent orchestrator and gateway | Minisforum | 18789 |
| OpenHands | Browser-based AI dev agent | Both | 3000 |
| OpenCode | AI coding agent | Both | 3002 / 3030 |
| Ollama | Local LLM serving | Both | 11434 |
| vLLM | High-throughput GPU inference | DGX Spark | varies |
| NemoClaw | Tenant isolation and model management | DGX Spark | varies |
| APISIX | API gateway with metering | Minisforum | 9080 / 9443 |
| SIE | Embeddings and reranking (bge-m3, bge-reranker-v2-m3) | Minisforum | 8089 |
| OpenRouter | Cloud LLM fallback gateway | Cloud | n/a |

## Current Status

The platform is live at **newfire.app** with four real tenants onboarded. Active workstreams include the NewFire Sandbox Service (NSS) for isolated agent runtimes, OpenClaw v1 as the coordinator surface, and vLLM tuning on the GB10 for the qwen3-coder-30b NVFP4 build.

## Security

Every service is fronted by Tailscale or zrok2 + OpenZiti. No service is exposed on the public internet without an authenticated tunnel. Backups are encrypted, tenant data is scoped, and the immigration-law tenant runs against local-only models.

## License

Not yet specified. All material in this repository is proprietary to the NewFire project until a license is added.
