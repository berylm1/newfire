# Context Prompt for DeepSeek

Copy everything below this line and paste into DeepSeek:

---

I'm building a two-machine AI homelab and need help configuring the integration patterns between my orchestrator and agent workers. Here's my full context:

## Hardware

**Machine 1: Minisforum X1 Pro 370 (Control Plane)**
- AMD Ryzen AI 9 HX 370, 96 GB DDR5, 2 TB NVMe
- Ubuntu 24.04.4 LTS (x86_64)
- Tailscale IP: 100.79.80.119
- Username: newwaveclaw

**Machine 2: NVIDIA DGX Spark (Compute Engine)**
- NVIDIA GB10 Grace Superchip (ARM), 128 GB unified memory, 4 TB NVMe
- Ubuntu 24.04.4 LTS, DGX OS 7.5.0 (aarch64)
- NVIDIA Driver 580.142, CUDA 13.0
- Tailscale IP: 100.88.112.5
- Username: newwave-dgx

## What's Currently Running

**Minisforum (Control Plane):**
- OpenClaw 2026.4.2 gateway on port 18789 (bind=lan, listening on 0.0.0.0)
- OpenClaw gateway token: [REDACTED-ROTATED]
- OpenCode (opencode:local) serving on port 3002 (command: `opencode serve --hostname 0.0.0.0 --port 3002`)
- Ollama on port 11434 with model glm-4.7-flash (CPU inference)
- APISIX 3.15.0 on port 9080 (metered API gateway with key-auth, admin key: fqGntGZRtgBoCdhBpDSkrrNhHbcPQHha on port 9180)
- Prometheus on port 9090
- Grafana on port 3003 (admin/homelab2026)
- UFW firewall active, fail2ban protecting SSH
- OpenClaw running as system user `openclaw` (UID 999) with systemd service

**DGX Spark (Compute Engine):**
- NemoClaw v0.0.6 with sandbox "my-assistant" (Landlock + seccomp + netns)
- OpenShell cluster on port 8080 (gRPC)
- OpenHands 0.44 serving on port 3000 (Docker container with --gpus all)
- Ollama on port 11434 (listening on 0.0.0.0) with models:
  - deepseek-r1:32b-8k (19 GB, Q4_K_M, 8K context) - reasoning model
  - glm4:9b (5.5 GB, Q4_0) - general model
  - deepseek-r1:70b (42 GB, stored but too large for full context without 4K variant)

**Cloud Fallback:**
- OpenRouter configured in OpenClaw with models: Claude Sonnet 4.5, DeepSeek R1, Nemotron Nano 30B (free)
- API key: [REDACTED-REVOKED]

## Current OpenClaw Config

The config is at /home/openclaw/.openclaw/openclaw.json on the Minisforum:

```json
{
  "agents": {
    "defaults": {
      "workspace": "/home/openclaw/.openclaw/workspace"
    }
  },
  "gateway": {
    "mode": "local",
    "auth": {
      "mode": "token",
      "token": "[REDACTED-ROTATED]"
    },
    "port": 18789,
    "bind": "lan",
    "tailscale": {
      "mode": "off",
      "resetOnExit": false
    },
    "controlUi": {
      "allowInsecureAuth": true
    },
    "nodes": {
      "denyCommands": [
        "camera.snap", "camera.clip", "screen.record",
        "contacts.add", "calendar.add", "reminders.add",
        "sms.send", "sms.search"
      ]
    }
  },
  "session": {
    "dmScope": "per-channel-peer"
  },
  "tools": {
    "profile": "coding"
  },
  "models": {
    "mode": "merge",
    "providers": {
      "ollama": {
        "baseUrl": "http://127.0.0.1:11434",
        "api": "ollama",
        "apiKey": "OLLAMA_API_KEY",
        "models": [
          {
            "id": "glm-4.7-flash",
            "name": "glm-4.7-flash",
            "reasoning": false,
            "input": ["text"],
            "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
            "contextWindow": 128000,
            "maxTokens": 8192
          }
        ]
      },
      "openrouter": {
        "baseUrl": "https://openrouter.ai/api/v1",
        "api": "openai-responses",
        "apiKey": "[REDACTED-REVOKED]",
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
            "id": "deepseek/deepseek-r1",
            "name": "DeepSeek R1 (Cloud)",
            "reasoning": true,
            "input": ["text"],
            "cost": { "input": 0.55, "output": 2.19, "cacheRead": 0, "cacheWrite": 0 },
            "contextWindow": 128000,
            "maxTokens": 32000
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
      },
      "dgx-ollama": {
        "baseUrl": "http://100.88.112.5:11434",
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
    }
  },
  "auth": {
    "profiles": {
      "ollama:default": {
        "provider": "ollama",
        "mode": "api_key"
      }
    }
  },
  "wizard": {
    "lastRunAt": "2026-04-04T13:30:30.164Z",
    "lastRunVersion": "2026.4.2",
    "lastRunCommand": "onboard",
    "lastRunMode": "local"
  },
  "meta": {
    "lastTouchedVersion": "2026.4.2",
    "lastTouchedAt": "2026-04-04T14:04:45.605Z"
  }
}
```

## OpenClaw CLI Capabilities

Running `openclaw --help` shows these relevant commands:
- `agents *` - Manage isolated agents (workspaces, auth, routing)
- `acp *` - Agent Control Protocol tools
- `webhooks *` - Webhook helpers and integrations
- `sessions *` - List stored conversation sessions
- `tasks *` - Inspect durable background task state
- `plugins *` - Manage OpenClaw plugins and extensions
- `models *` - Discover, scan, and configure models

Currently only one agent exists: `main` (default) with no routing rules.

## What I Need Help With

1. **Multi-Agent Integration**: Configure OpenClaw to use OpenCode (port 3002 on Minisforum) and OpenHands (port 3000 on DGX Spark at 100.88.112.5) as worker agents. I need:
   - A coding agent (OpenCode) for code generation, review, debugging
   - A dev agent (OpenHands) for full-stack development, browser tasks, deployment

2. **Smart Routing**: Configure OpenClaw to automatically route requests to the right model tier:
   - Light tasks → glm-4.7-flash on Minisforum CPU (free, fast)
   - Medium tasks → glm4:9b on DGX Spark GPU (free, fast)
   - Heavy reasoning → deepseek-r1:32b-8k on DGX Spark GPU (free, powerful)
   - Cloud fallback → OpenRouter (paid, always available)

3. **Task Delegation**: Set up webhook or ACP-based task delegation so OpenClaw can send coding tasks to OpenCode and dev tasks to OpenHands, with callbacks.

Please provide the exact OpenClaw commands and config changes needed. I need real commands that work with OpenClaw 2026.4.2, not hypothetical plugins. The system user is `openclaw` and I edit config by writing JSON files on my Mac and SCP'ing them to the Minisforum at /home/openclaw/.openclaw/openclaw.json (SSH terminal mangles multi-line pastes).

## Important Notes
- The npm package `@laceletho/plugin-openclaw` does NOT exist. Do not reference it.
- OpenClaw config validation is strict. The `api` field must be one of: openai-completions, openai-responses, openai-codex-responses, anthropic-messages, google-generative-ai, github-copilot, bedrock-converse-stream, ollama, azure-openai-responses
- The `gateway.bind` field uses mode names (lan, loopback, custom, tailnet, auto), not raw IPs
- All provider fields (baseUrl, api, apiKey, models array) must be set together
- The openclaw system user has no sudo password. System packages must be installed as newwaveclaw first.
