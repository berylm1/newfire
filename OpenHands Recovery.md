---
title: OpenHands Recovery
date: 2026-06-22
tags: [openhands, homelab, ghana, america, vllm, ollama, debugging, performance]
status: resolved
machine_america: newwaveclaw@america (Minisforum X1 Pro)
machine_ghana: newwave-dgx@ghana (DGX Spark GB10)
session: 2026-06-22 to 2026-06-23
---

# OpenHands Recovery

Recovery and performance optimization session for the OpenHands agent-canvas deployment on the NewFire homelab. Use this note as context for any AI agent managing this infrastructure to avoid repeating the same diagnosis work.

## System Architecture (as-found)

```
Mac (local) --> Tailscale --> america (Minisforum X1 Pro 370)
                                  └── openhands-app (Docker, host network, port 8000)
                                        └── frontend + agent server (ports 18000, 18001)
                                        └── Chromium headless (remote debug :35143)
                                        └── OpenVSCode server (port 8001 in container)

                          --> Tailscale --> ghana (DGX Spark GB10, Tailscale IP 100.88.112.5)
                                              └── vllm-qwen-coder (Docker, port 8001)
                                              └── Ollama service (port 11434)
```

OpenHands uses **host networking** on america. Port 8000 is the unified entry point proxied by `static-server.mjs`. The agent server runs internally on `127.0.0.1:18000`. The container's Tailscale IP on the host network is `100.79.80.119`.

## Authentication

The OpenHands API uses a session API key passed as `X-Session-API-Key` header (not Bearer token).

```
Key location (on america, requires sudo):
/var/lib/docker/volumes/openhands-data/_data/agent-canvas/api-key.txt

Value: 0a5180831d41062f5e7abf8dd3f2bbb2965d64f48276e2c809eeaf85f5de37ec
```

> NOTE: `session_api_key` as a query param is deprecated per 2026-06-22 logs. The header form `X-Session-API-Key` is the current working method.

## LLM Profiles (as of 2026-06-22)

All profiles live at: `/var/lib/docker/volumes/openhands-data/_data/profiles/`

| Profile file | Model | Endpoint | Status |
|---|---|---|---|
| `qwen2.5-coder-7b-vLLM.json` | qwen2.5-coder-7b | ghana:8001 (vLLM) | WORKING |
| `qwen7b-vLLM.json` | qwen-coder-7b | ghana:8001 (vLLM) | WORKING |
| `Qwen30B-ollama.json` | qwen3-coder:30b | ghana:11434 (Ollama) | WORKING |
| `qwen3-coder-30b.json` | qwen3-coder-30b-64k:latest | ghana:11434 (Ollama) | FIXED (was pointing to dead port 8000) |
| `qwen3-coder-64k-ollama.json` | qwen3-coder-30b-64k:latest | ghana:11434 (Ollama) | FIXED (was missing api_key field) |
| `gemma4-26B-ollama.json` | gemma4-26b-64k | ghana:11434 (Ollama) | WORKING |
| `deepseek-r1-ollama.json` | deepseek-r1-70b-64k | ghana:11434 (Ollama) | WORKING (slow, 70B) |

### Fixes Applied 2026-06-22

**Fix 1 - Dead vLLM port:** `qwen3-coder-30b.json` was pointing to `http://100.88.112.5:8000/v1`. The vLLM instance on port 8000 is not running. Changed `base_url` to `http://100.88.112.5:11434/v1` and model to `qwen3-coder-30b-64k:latest`.

**Fix 2 - Missing api_key:** `qwen3-coder-64k-ollama.json` had no `api_key` field. LiteLLM's OpenAI client requires the field to exist even if Ollama doesn't enforce it. Added `"api_key": "ollama"`.

## Active Services on Ghana (2026-06-22)

### vLLM (port 8001)
- Container: `vllm-qwen-coder`
- Image: `vllm/vllm-openai:v0.20.0`
- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- Served as: `qwen2.5-coder-7b`
- Restart: `always`

```bash
# Recreate command (optimized):
docker run -d \
  --name vllm-qwen-coder \
  --gpus all \
  --ipc host \
  --shm-size 4g \
  --restart always \
  -v /home/newwave-dgx/.cache/huggingface:/root/.cache/huggingface \
  -p 8001:8001 \
  vllm/vllm-openai:v0.20.0 \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --served-model-name qwen2.5-coder-7b \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.20 \
  --enable-auto-tool-choice \
  --enable-prefix-caching \
  --enable-chunked-prefill \
  --tool-call-parser hermes \
  --kv-cache-dtype fp8 \
  --uvicorn-log-level warning \
  --host 0.0.0.0 \
  --port 8001
```

### Ollama (port 11434)
- Service: `ollama serve` running as `ollama` user
- Primary model for code tasks: `qwen3-coder-30b-64k:latest` (Q4_K_M, 30.5B MoE)
- Many models available, check with `curl http://localhost:11434/v1/models`

## Critical Performance Bug Found and Fixed

### Root Cause: vLLM Over-allocating Unified Memory

The DGX Spark GB10 uses **unified LPDDR5X memory** where there is no separate VRAM. All 128 GB is shared between CPU and GPU via C2C interconnect with ATS enabled.

**Before (broken state):**
- `--gpu-memory-utilization 0.85` on 128 GB = **100 GB reserved** by vLLM for KV cache
- A 7B model at fp8 only needs ~14 GB total (model + realistic KV cache)
- Ollama's 30B model was squeezed into the remaining ~12 GB
- System RAM: 118 GB used, **954 MB free**, 8.5 GB swap in use
- 30B model was paging constantly

**After (fixed):**
- `--gpu-memory-utilization 0.20` = **25.6 GB for vLLM** (still ~2x more than the 7B ever needs)
- Ollama 30B now has ~90 GB available, loads fully without paging
- System RAM: 42-73 GB used (depending on load), 46 GB available, 3.2 GB swap

### Performance Results

| Model | Before fix | After fix | Factor |
|---|---|---|---|
| Qwen3-Coder-30B (Ollama) | 0.15 tok/s (model swapping) | **36 tok/s steady state** | 240x |
| Qwen2.5-Coder-7B (vLLM) | ~1 tok/s (TTFT slow) | 11 tok/s | baseline |

**Rule for future:** On unified memory hardware (GB10, Apple M-series, etc.), always compute actual model memory need before setting utilization. Formula: `gpu_memory_utilization = (model_GB + target_kv_cache_GB) / total_system_GB`. For the 7B on 128 GB, 0.20 is generous. For running a 30B alongside it, cap the 7B at 0.20 max.

## OpenHands Browser Issue (Diagnosed)

The Chromium browser **is working** and it successfully navigates external URLs and returns page content. The issue with browser preview for local dev apps comes down to workflow, not a software bug.

**The correct workflow for browser preview of a local dev server:**

1. Agent must start the dev server explicitly with a background terminal command
2. Server must bind to `0.0.0.0` (not just localhost) for external access; localhost works for Chromium inside the container since it shares the host network
3. Agent must navigate the browser to `http://localhost:<PORT>` after confirming the server is running
4. Use this follow-up prompt if the agent writes code but doesn't preview it:

```
Start the dev server in the background (bind to 0.0.0.0 if there is a host flag),
show me the port from terminal output, then open the browser to that URL and take a screenshot.
```

**Why the user sees no visual:** The agent was calling `BrowserGetStateAction` with `include_screenshot: False`. The text content of pages is returned, but the visual browser panel only shows what is rendered live in Chromium. If no dev server is running, Chromium shows an error page.

## GitHub Integration

OpenHands is connected to GitHub via Copilot MCP:
```
URL: https://api.githubcopilot.com/mcp/
Header: Authorization (encrypted in settings.json)
```

Settings file: `/var/lib/docker/volumes/openhands-data/_data/settings.json`

## Full Benchmark: Financial Switch Prompt

### Prompt Given
> Design and implement the Next Generation payment switch for central banking / large financial institutions. Stack: Go + Python, Mojaloop, TigerBeetle, Kafka, Temporal, Dapr, APISIX, OpenAppSec, Keycloak, OpenCTI, Wazuh, OpenSearch, Fluvio, Redis, Kubecost, Postgres, Kubernetes, Lakehouse with Delta Lake / Parquet / Flink / Spark / DataFusion / Ray / Sedona. Task: architecture doc + core Go ISO 8583 router.

### Run 1 - Text-only baseline (no tools)

Conversation ID: `1f2413fc-f049-409a-8ab3-0d082c28966f`
Model: `qwen3-coder-30b-64k:latest` via Ollama on ghana:11434
Tools: none (API payload had empty tools list)

| Metric | Value |
|---|---|
| Total completion tokens | 9,133 |
| Total prompt tokens | 54,887 |
| Total LLM time | 376.9 s |
| Average tok/s | **24.2 tok/s** |
| Total agent turns | 9 |
| Files created | 0 |
| Final status | finished |

Faster per-turn because the agent only output text. No tool calls meant no round-trip overhead. This is the ceiling for raw token throughput on this model.

### Run 2 - Full tool use (terminal + file_editor + browser_tool_set)

Conversation ID: `4ae94a64-ea92-4139-b391-d1c2b54b4e68`
Model: `qwen3-coder-30b-64k:latest` via Ollama on ghana:11434
Tools: terminal, file_editor, task_tracker, browser_tool_set (all 4 enabled in API payload)
Date: 2026-06-23

| Metric | Value |
|---|---|
| Total completion tokens | 6,423 |
| Total prompt tokens | 469,857 (growing context with tool results each turn) |
| Total LLM time | 302.5 s |
| Average tok/s | **21.2 tok/s** |
| Total agent turns | 32 |
| Files created | 10 |
| Final status | finished |

**Files created in `/workspace/project/`:**
- `ARCHITECTURE.md` - full system architecture document
- `README.md` - project overview with component list
- `cmd/router/main.go` - Go ISO 8583 transaction router entry point
- `cmd/router/go.mod`
- `internal/iso8583/parser.go` - ISO 8583 message parser with MTI, PAN, amount, currency fields
- `internal/iso8583/go.mod`
- `pkg/fraud/README.md`, `pkg/messaging/README.md`, `pkg/settlement/README.md`, `pkg/switch/README.md`
- `show_structure.py` - Python project tree visualization

**Tool use confirmed:** terminal commands ran (mkdir, find, ls, which python3), file_editor wrote all 10 files. Browser was registered but not called since there was no running web server to navigate to - the browser tool is useful for dev server previews, not static code files.

**Known container limitation discovered:** Go runtime is NOT installed in the OpenHands container. The agent adapted by skipping `go mod tidy` / `go build` and created a Python script to display the project structure instead. The Go source files are syntactically correct but cannot be compiled inside the container without installing Go first.

**Fix to install Go in container (one-time):**
```bash
# On america, exec into the running container
docker exec -u root openhands-app bash -c "apt-get update && apt-get install -y golang-go"
# Or in the agent's terminal session:
# apt-get update && apt-get install -y golang-go
```

**Interpretation:** 32 agent turns at 21.2 tok/s with 10 files created in ~5 minutes. The token throughput dips slightly vs Run 1 because each tool call appends tool results to the context (469K prompt tokens total vs 54K), which increases prefill time. For a demo, expect 5-6 minutes wall-clock for a complex multi-file Go + architecture task.

**Demo recommendation:** For a live demo, pre-install Go in the container and use the 30B model. The agent will write, compile, and run Go code end-to-end.

## Known Issues (Open)

### 0. Go Runtime Not Installed in OpenHands Container
`go` is not on the PATH inside the agent-canvas container. Any agent generating Go code will hit `bash: go: command not found` when trying to build or `go mod tidy`. Fix: `docker exec -u root openhands-app apt-get install -y golang-go`. This only needs to be done once (the container persists data via the openhands-data volume, but the binary is in the container layer itself, so it resets on container recreation). Long-term fix: add Go to the agent-canvas Dockerfile or add a startup hook.

### 1. LLM Timeout on Long Requests (Non-critical)
Some conversations using `deepseek-r1-70b-64k` hit 900s generation time against a 300s timeout setting. The 70B dense model is slow for long completions. Workaround: use qwen3-coder-30b-64k for code tasks and reserve deepseek-r1 for reasoning tasks where you can accept longer wait times or raise the timeout in the profile.

### 2. Git Repo in /projects is Empty
The `/projects` volume mounted inside the OpenHands container has an empty git repo with no commits. This causes repeated `fatal: Needed a single revision` errors in the agent server logs when it tries to diff changes. Not blocking but generates log noise. Fix: make an initial commit in the workspace after starting a project.

### 3. OpenHands Conversation Title Not in Storage
The title shown in the OpenHands UI (e.g., "features: Implement new feature with test cov...") is generated client-side from the first message and is not stored server-side in the event files. Searching for a conversation by title requires reading `events/event-00001-*.json` and extracting `llm_message.content[].text`.

### 4. API Polling Format
The `/api/conversations/{id}/events` endpoint returns 422 if called without required query params. Correct format:
```
GET /api/conversations/{id}/events?limit=10
Header: X-Session-API-Key: <key>
```

## Useful Commands

```bash
# Check OpenHands container health
ssh newwaveclaw@america "curl -s http://localhost:8000/health"

# Check which models ghana's Ollama has loaded
ssh newwave-dgx@ghana "curl -s http://localhost:11434/api/ps | python3 -m json.tool"

# Check GPU memory split on ghana
ssh newwave-dgx@ghana "nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader"

# Quick tok/s test on vLLM 7B
ssh newwave-dgx@ghana "time curl -s http://localhost:8001/v1/completions -X POST \
  -H 'Content-Type: application/json' \
  -d '{\"model\":\"qwen2.5-coder-7b\",\"prompt\":\"hello world in Python\",\"max_tokens\":50}' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[\"usage\"])'"

# Quick tok/s test on Ollama 30B
ssh newwave-dgx@ghana "curl -s http://localhost:11434/v1/completions -X POST \
  -H 'Content-Type: application/json' \
  -d '{\"model\":\"qwen3-coder-30b-64k:latest\",\"prompt\":\"hello world in Go\",\"max_tokens\":50}' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[\"usage\"])'"

# Restart vLLM with correct settings (stop first, then run the docker run command above)
ssh newwave-dgx@ghana "docker stop vllm-qwen-coder && docker rm vllm-qwen-coder"

# List all OpenHands conversations
ssh newwaveclaw@america "curl -s 'http://localhost:8000/api/conversations/search' \
  -H 'X-Session-API-Key: 0a5180831d41062f5e7abf8dd3f2bbb2965d64f48276e2c809eeaf85f5de37ec' \
  | python3 -m json.tool | grep '\"id\"'"
```

## Context for AI Agents

If you are an AI agent reading this note to manage context or avoid rate limiting, here is the priority stack:

1. **For fast code tasks (small files, single functions):** Use `qwen2.5-coder-7b` on vLLM (ghana:8001). Fastest TTFT, ~11 tok/s, tool-calling enabled.
2. **For complex multi-file projects, architecture, or full-stack tasks:** Use `qwen3-coder-30b-64k:latest` on Ollama (ghana:11434). 24-36 tok/s in practice, 30.5B MoE (activates ~2.7B per token), handles 64K context.
3. **For reasoning and planning tasks:** Use `deepseek-r1-70b-64k` on Ollama. Slow (70B dense) but best logical reasoning. Set timeout above 600s in the profile.
4. **Browser preview:** Always start the dev server before navigating. Chromium runs headlessly inside the OpenHands container on america.
5. **GitHub:** Copilot MCP is connected. Git operations inside the workspace expect commits to exist, so make an initial commit at project start.
6. **Rate limits:** All models are self-hosted on ghana so there are no external API rate limits. The only constraint is unified memory, since running multiple simultaneous long-context requests on the 30B model will contend for KV cache space.
