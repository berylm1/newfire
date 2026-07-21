# OpenClaw Deployment Status

**Last Updated:** 2026-07-16
**Version:** OpenClaw v2026.4.14
**Status:** ✅ Running

## Overview

OpenClaw is a multi-agent orchestration system running on this machine. It manages multiple AI agents with different specializations, connects to various messaging platforms, and routes requests to appropriate LLM providers.

## Gateway Configuration

- **Status:** Running (PID varies)
- **Port:** 18789
- **Bind:** lan (0.0.0.0)
- **Auth Mode:** Token-based
- **Auth Token:** `c6b990633a7a47504cafa2a3cf80481f3d34f449d587c826`
- **Health Endpoint:** `http://127.0.0.1:18789/health` → Returns `{"ok":true,"status":"live"}`

## Model Providers

| Provider | Status | Base URL | Primary Model |
|----------|--------|----------|---------------|
| vLLM | ✅ Active | `http://100.88.112.5:8001/v1` | `vllm/qwen` (Qwen3.6-27B-FP8) |
| Ollama | ✅ Active | `http://100.88.112.5:11434` | `ollama/glm4:9b`, `ollama/deepseek-r1:32b` |
| OpenRouter | ✅ Active | `https://openrouter.ai/api/v1` | `deepseek/deepseek-r1`, `nvidia/nemotron-3-nano-30b-a3b:free` |

**Primary Model:** `vllm/qwen` (Qwen3.6-27B-FP8 via vLLM)
**Fallback Models:** `ollama/deepseek-r1:32b`

## Agents

| Agent ID | Name | Model | Workspace | Specialization |
|----------|------|-------|-----------|----------------|
| main | Main Agent | `ollama/qwen3-coder:30b` | Default | General purpose |
| opencode-worker | OpenCode Worker | `ollama/deepseek-r1:32b` | `/home/openclaw/.openclaw/workspace-opencode` | Code operations |
| openhands-worker | OpenHands Worker | `ollama/qwen3-coder:30b` | `/home/openclaw/.openclaw/workspace-openhands` | OpenHands integration |
| funmi-legal | Legal Handler | `ollama/deepseek-r1:32b` | `/home/openclaw/.openclaw/workspace-funmi-legal` | Legal intake |
| legal-intake-handler | WhatsApp Legal | `ollama/glm4:9b` | `/home/openclaw/.openclaw/workspace-legal-intake` | WhatsApp automation |

## Messaging Channels

| Channel | Status | Configuration |
|---------|--------|---------------|
| WhatsApp | ✅ Active | Account: `newfire-main`, enabled, allowlist policy |
| Slack | ✅ Active | Bot token configured, require mention |
| Telegram | ✅ Active | Bot token: `8866998906:AAFQ...` |

## Plugins

| Plugin | Status | Description |
|--------|--------|-------------|
| openclaw-webdav | ✅ Enabled | WebDAV storage integration |
| ollama | ✅ Enabled | Ollama model provider |
| openrouter | ✅ Enabled | OpenRouter model provider |
| mesibo | ✅ Enabled | WhatsApp Business API integration |
| slack | ✅ Enabled | Slack integration |
| memory-core | ✅ Enabled | Memory management |

## MCP Servers

- **newfire-rag:** `http://100.88.112.5:7333/sse` (SSE transport)

## File Locations

```
Config: /home/openclaw/.openclaw/openclaw.json
Logs: /tmp/openclaw-0/openclaw-*.log
Workspace: /home/openclaw/.openclaw/workspace
Extensions: /home/openclaw/.openclaw/extensions/
```

## Troubleshooting

### Common Issues

1. **Gateway not responding**
   ```bash
   # Check if gateway is running
   ps aux | grep openclaw-gateway | grep -v grep
   
   # Restart gateway
   sudo kill $(pgrep openclaw-gateway)
   sudo -u openclaw openclaw gateway run &
   ```

2. **Model connectivity issues**
   ```bash
   # Test vLLM directly
   curl http://100.88.112.5:8001/v1/models
   
   # Test Ollama directly
   curl http://100.88.112.5:11434/api/tags
   ```

3. **Configuration validation errors**
   - Check logs: `tail -f /tmp/openclaw-0/openclaw-$(date +%Y-%m-%d).log`
   - Validate config: `openclaw doctor`

### Recent Changes (2026-07-16)

- Added vLLM provider with Qwen3.6-27B-FP8 model
- Set primary model to `vllm/qwen`
- Configured Telegram channel integration
- Gateway restarted to apply changes

## Notes

- OpenClaw runs as user `openclaw` (not root)
- Gateway auth token must be included in API requests: `Authorization: Bearer <token>`
- Model changes require gateway restart to take effect
- WhatsApp channel uses mesibo plugin with app ID `com.newfire.ai`
