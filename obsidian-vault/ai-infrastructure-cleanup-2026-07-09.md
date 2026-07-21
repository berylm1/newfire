# AI Infrastructure Cleanup — July 9, 2026

## Summary
Beryl asked to focus Ghana (DGX Spark) on pure AI inference, removing non-essential services.

## Actions Taken

### Ghana (DGX Spark — 100.88.112.5)

**Removed:**
- `qdrant-newfire` — moved to America `legal-qdrant`
- `whisper-asr` — freed ~2GB RAM
- `nss-router` — not needed for direct LiteLLM → model routing

**Kept:**
- `litellm` (port 4000) — AI model router, OpenHands needs it
- `openshell-cluster-nemoclaw` (port 8080) — NVIDIA OpenShell, infrastructure testing
- `llama.cpp` servers:
  - `qwen3.6` on port 8090 (35B params, 26GB)
  - `ornith` on port 8000 (35B params)

**Note:** K3s (Kubernetes) is now gone — only 2 Docker containers running on Ghana.

### America (Minisforum — 100.79.80.119)

**Moved to:**
- `legal-qdrant` — received Qdrant data from Ghana (still empty, no collections)

**Relevant containers now:**
- `legal-qdrant` — running on America, port 6333 (via 127.0.0.1)
- `legal-qdrant` data location: `/home/openclaw/legal-tenant/qdrant_storage`

## Current Ghana State (Post-Cleanup)
- **2 containers**: litellm + openshell
- **2 AI models**: Qwen3.6 (port 8090) + Ornith (port 8000)
- **GPU**: NVIDIA GB10 at 95% utilization, 78°C, 82W
- **RAM**: ~63GB used / 119GB total
- **Disk**: 1.2TB / 3.7TB used

## OpenHands Agent-Canvas Configuration
- **Model**: `openai/qwen3.6`
- **Base URL**: `http://100.88.112.5:8090/v1` (Qwen3.6 via LiteLLM)
- **Context**: 260K tokens
- **Max iterations**: 2000
- **Critic mode**: `finish_and_message`
- **MCP servers**: GitHub Copilot, fetch, memory, time
- **Condenser**: enabled (LLM summarizing, max 150 tokens)

## Next Steps (Pending Beryl's Decision)
1. Verify OpenHands can still reach Qwen3.6/Ornith via LiteLLM
2. Decide if K3s should be reinstalled for OpenShell
3. Move Qdrant collections to legal-qdrant on America if needed
