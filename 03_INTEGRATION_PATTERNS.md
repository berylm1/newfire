# Integration Patterns -- Agent Communication Architecture

## Overview

There are three patterns for integrating OpenClaw with agents (OpenCode, OpenHands). Choose the pattern that fits your needs, or implement multiple patterns for different use cases.

| Pattern                  | Complexity | Latency  | Use Case                          |
|--------------------------|------------|----------|-----------------------------------|
| Model Provider           | Simplest   | Lowest   | Direct LLM access via agent       |
| Webhook Task Delegation  | Medium     | Medium   | Async task management, most robust|
| ACP Agents               | Deepest    | Variable | Persistent agents, full lifecycle  |

You can use all three patterns simultaneously. They are not mutually exclusive.

---

## Pattern 1: Model Provider (Simplest)

In this pattern, OpenClaw treats OpenCode as a model backend -- similar to how it would treat Ollama or OpenRouter. When OpenClaw needs to perform a coding task, it routes the request to OpenCode's model endpoint.

### How It Works

```
User --> OpenClaw Gateway --> OpenCode (as model provider) --> Response back
                                  |
                                  +--> Uses its own LLM (Ollama, OpenRouter, etc.)
```

### Configuration

Edit `/etc/openclaw/openclaw.json` (or `~/.openclaw/openclaw.json`):

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "opencode/claude-opus-4-6",
        "fallback": "ollama/llama3.1:70b"
      }
    },
    "providers": {
      "opencode": {
        "type": "opencode",
        "endpoint": "http://localhost:3002/api/v1",
        "models": [
          {
            "id": "claude-opus-4-6",
            "displayName": "Claude Opus 4 via OpenCode",
            "contextWindow": 200000,
            "maxOutputTokens": 64000
          },
          {
            "id": "claude-sonnet-4-5",
            "displayName": "Claude Sonnet 4.5 via OpenCode",
            "contextWindow": 200000,
            "maxOutputTokens": 64000
          }
        ],
        "headers": {
          "Authorization": "Bearer ${OPENCODE_API_KEY}"
        },
        "timeout": 120000
      },
      "ollama": {
        "type": "ollama",
        "endpoint": "http://localhost:11434",
        "models": [
          {
            "id": "llama3.1:70b",
            "displayName": "Llama 3.1 70B (Local)",
            "contextWindow": 128000
          }
        ]
      }
    }
  }
}
```

### When to Use

- You want the **simplest integration** with minimal setup
- You want OpenClaw to use OpenCode's capabilities as a "smart model"
- You do not need task tracking, callbacks, or lifecycle management
- Good for: Quick coding questions, code generation, code review

### Limitations

- No task persistence or tracking
- No async callbacks
- OpenCode is treated as a stateless model endpoint
- No multi-turn agent sessions

---

## Pattern 2: Webhook-Based Task Delegation (Most Robust)

In this pattern, OpenClaw delegates tasks to OpenCode via HTTP webhooks. OpenCode processes the task asynchronously and calls back OpenClaw with the result. This is the **recommended production pattern**.

### How It Works

```
User --> OpenClaw Gateway --[HTTP POST]--> OpenCode Plugin (port 9090)
              ^                                   |
              |                                   v
              +---[HTTP POST callback]--- Task Result
```

1. OpenClaw sends a task to OpenCode via HTTP POST
2. OpenCode acknowledges immediately (202 Accepted)
3. OpenCode processes the task (may take minutes)
4. OpenCode calls back OpenClaw with the result via the `callbackUrl`

### Step 1: Install the OpenClaw Plugin in OpenCode

```bash
# Navigate to your OpenCode configuration directory
cd ~/.config/opencode

# Install the OpenClaw bridge plugin
npm install @laceletho/plugin-openclaw

# Or if using a global install:
npm install -g @laceletho/plugin-openclaw
```

### Step 2: Configure OpenCode with the Plugin

Edit `~/.config/opencode/opencode.json` (or wherever OpenCode's config lives):

```json
{
  "server": {
    "port": 3002,
    "host": "0.0.0.0"
  },
  "plugins": {
    "@laceletho/plugin-openclaw": {
      "enabled": true,
      "webhookPort": 9090,
      "webhookHost": "0.0.0.0",
      "webhookPath": "/tasks",
      "auth": {
        "type": "bearer",
        "token": "${OPENCLAW_WEBHOOK_SECRET}"
      },
      "callbackAuth": {
        "type": "bearer",
        "token": "${OPENCODE_CALLBACK_SECRET}"
      },
      "taskDefaults": {
        "timeout": 3600000,
        "maxRetries": 2,
        "sandbox": true
      },
      "logging": {
        "level": "info",
        "taskEvents": true
      }
    }
  },
  "model": {
    "provider": "openrouter",
    "model": "anthropic/claude-sonnet-4-5",
    "apiKey": "${OPENROUTER_API_KEY}"
  }
}
```

### Step 3: Configure OpenClaw to Send Webhooks

Edit `/etc/openclaw/openclaw.json`:

```json
{
  "agents": {
    "list": [
      {
        "name": "opencode-webhook",
        "type": "webhook",
        "displayName": "OpenCode (Webhook)",
        "description": "Coding agent via webhook delegation",
        "endpoint": "http://localhost:9090/tasks",
        "auth": {
          "type": "bearer",
          "token": "${OPENCLAW_WEBHOOK_SECRET}"
        },
        "callback": {
          "url": "http://localhost:18789/api/v1/tasks/callback",
          "auth": {
            "type": "bearer",
            "token": "${OPENCODE_CALLBACK_SECRET}"
          }
        },
        "capabilities": [
          "code-generation",
          "code-review",
          "debugging",
          "refactoring",
          "testing"
        ],
        "timeout": 3600000,
        "retries": 2,
        "healthCheck": {
          "url": "http://localhost:9090/health",
          "interval": 30000
        }
      },
      {
        "name": "openhands-webhook",
        "type": "webhook",
        "displayName": "OpenHands (Webhook)",
        "description": "Dev agent via webhook delegation",
        "endpoint": "http://localhost:3000/api/v1/tasks",
        "auth": {
          "type": "bearer",
          "token": "${OPENCLAW_WEBHOOK_SECRET}"
        },
        "callback": {
          "url": "http://localhost:18789/api/v1/tasks/callback",
          "auth": {
            "type": "bearer",
            "token": "${OPENCODE_CALLBACK_SECRET}"
          }
        },
        "capabilities": [
          "full-stack-development",
          "browser-testing",
          "deployment",
          "debugging"
        ],
        "timeout": 7200000,
        "retries": 1
      }
    ]
  }
}
```

### Task Payload Format

When OpenClaw sends a task to an agent, the payload looks like:

```json
{
  "taskId": "task_abc123def456",
  "prompt": "Refactor the user authentication module to use JWT tokens instead of session cookies. The codebase is in /workspace/myapp.",
  "context": {
    "repository": "https://github.com/user/myapp",
    "branch": "feature/jwt-auth",
    "files": [
      "src/auth/session.ts",
      "src/auth/middleware.ts"
    ]
  },
  "callbackUrl": "http://localhost:18789/api/v1/tasks/callback",
  "callbackConfig": {
    "auth": {
      "type": "bearer",
      "token": "OPENCODE_CALLBACK_SECRET_VALUE"
    },
    "headers": {
      "X-Task-ID": "task_abc123def456",
      "Content-Type": "application/json"
    }
  },
  "options": {
    "timeout": 3600000,
    "sandbox": true,
    "maxTokens": 64000
  }
}
```

### Callback Response Format

When the agent completes the task, it POSTs back to the `callbackUrl`:

```json
{
  "taskId": "task_abc123def456",
  "status": "completed",
  "result": {
    "summary": "Refactored authentication from session-based to JWT-based...",
    "filesModified": [
      "src/auth/jwt.ts",
      "src/auth/middleware.ts",
      "src/auth/session.ts"
    ],
    "diff": "...",
    "tokensUsed": {
      "input": 12500,
      "output": 8300
    }
  },
  "metadata": {
    "duration": 45000,
    "model": "anthropic/claude-sonnet-4-5",
    "provider": "openrouter"
  }
}
```

### Step 4: Set Environment Variables

```bash
# Generate secrets
OPENCLAW_WEBHOOK_SECRET=$(openssl rand -hex 32)
OPENCODE_CALLBACK_SECRET=$(openssl rand -hex 32)

# Add to the openclaw user's environment
sudo tee -a /home/openclaw/.env << EOF
OPENCLAW_WEBHOOK_SECRET=${OPENCLAW_WEBHOOK_SECRET}
OPENCODE_CALLBACK_SECRET=${OPENCODE_CALLBACK_SECRET}
EOF

# If using systemd, add to the service environment file
sudo tee -a /etc/openclaw/env << EOF
OPENCLAW_WEBHOOK_SECRET=${OPENCLAW_WEBHOOK_SECRET}
OPENCODE_CALLBACK_SECRET=${OPENCODE_CALLBACK_SECRET}
EOF

# Restart services to pick up new variables
sudo systemctl restart openclaw
```

### Step 5: Test the Webhook Flow

```bash
# Test the webhook endpoint directly
curl -X POST http://localhost:9090/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${OPENCLAW_WEBHOOK_SECRET}" \
  -d '{
    "taskId": "test_001",
    "prompt": "Write a Python function that calculates fibonacci numbers",
    "callbackUrl": "http://localhost:18789/api/v1/tasks/callback",
    "callbackConfig": {
      "auth": {
        "type": "bearer",
        "token": "'"${OPENCODE_CALLBACK_SECRET}"'"
      }
    }
  }'

# Expected: 202 Accepted with a task acknowledgment

# Check task status (if the agent supports it)
curl -s http://localhost:9090/tasks/test_001/status \
  -H "Authorization: Bearer ${OPENCLAW_WEBHOOK_SECRET}" | jq .
```

### When to Use

- **Production workloads** requiring reliability
- Tasks that take minutes to hours
- You need task tracking, retry logic, and audit trails
- Multi-agent workflows where tasks are dispatched to the best agent
- You want decoupled architecture (agents can be on different machines)

---

## Pattern 3: ACP Agents (Deepest Integration)

ACP (Agent Communication Protocol) provides the deepest integration. Agents are spawned as persistent processes that maintain state, can be paused/resumed, and communicate over a structured protocol.

### How It Works

```
User --> OpenClaw Gateway --> ACP Runtime --> Agent Process (persistent)
              ^                                      |
              |                                      v
              +---- ACP Protocol (bidirectional) ----+
                    (spawn, status, message, kill)
```

### Step 1: Configure ACP Runtimes

Edit `/etc/openclaw/openclaw.json`:

```json
{
  "acp": {
    "enabled": true,
    "backend": "acpx",
    "runtimes": {
      "acpx": {
        "type": "acpx",
        "socket": "/var/run/openclaw/acp.sock",
        "logDir": "/var/log/openclaw/acp/",
        "maxAgents": 20,
        "defaultMode": "persistent",
        "healthCheckInterval": 15000,
        "resources": {
          "defaultMemory": "2g",
          "defaultCpu": "1.0",
          "maxMemory": "8g",
          "maxCpu": "4.0"
        }
      }
    },
    "agents": {
      "opencode": {
        "runtime": "acpx",
        "image": "opencode:latest",
        "command": ["opencode", "serve", "--acp"],
        "mode": "persistent",
        "replicas": 1,
        "resources": {
          "memory": "2g",
          "cpu": "2.0"
        },
        "env": {
          "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}",
          "OPENCODE_MODE": "acp-agent"
        },
        "healthCheck": {
          "command": ["opencode", "health"],
          "interval": 30,
          "timeout": 10,
          "retries": 3
        }
      },
      "openhands": {
        "runtime": "acpx",
        "image": "openhands:latest",
        "command": ["openhands", "serve", "--acp"],
        "mode": "persistent",
        "replicas": 1,
        "resources": {
          "memory": "4g",
          "cpu": "2.0"
        },
        "env": {
          "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}",
          "OPENHANDS_MODE": "acp-agent"
        }
      }
    }
  },
  "agents": {
    "list": [
      {
        "name": "opencode-acp",
        "type": "acp",
        "displayName": "OpenCode (ACP Persistent)",
        "description": "Persistent coding agent via ACP protocol",
        "runtime": {
          "type": "acp",
          "acp": {
            "agent": "opencode",
            "backend": "acpx",
            "mode": "persistent"
          }
        },
        "capabilities": [
          "code-generation",
          "code-review",
          "debugging",
          "refactoring",
          "testing",
          "multi-turn-conversation"
        ],
        "threadManagement": {
          "mode": "auto",
          "maxThreads": 10,
          "idleTimeout": 3600
        }
      },
      {
        "name": "openhands-acp",
        "type": "acp",
        "displayName": "OpenHands (ACP Persistent)",
        "description": "Persistent dev agent via ACP protocol",
        "runtime": {
          "type": "acp",
          "acp": {
            "agent": "openhands",
            "backend": "acpx",
            "mode": "persistent"
          }
        },
        "capabilities": [
          "full-stack-development",
          "browser-testing",
          "deployment",
          "multi-turn-conversation"
        ],
        "threadManagement": {
          "mode": "auto",
          "maxThreads": 5,
          "idleTimeout": 7200
        }
      }
    ]
  }
}
```

### Step 2: Spawn ACP Agents

Use the OpenClaw CLI to spawn agents:

```bash
# Spawn OpenCode as a persistent ACP agent
# The --thread auto flag means OpenClaw manages thread/session IDs automatically
/acp spawn opencode --mode persistent --thread auto

# Expected output:
# Agent 'opencode' spawned successfully.
#   PID:      12345
#   Thread:   thread_abc123
#   Mode:     persistent
#   Status:   running
#   Endpoint: acp://localhost/agents/opencode/thread_abc123

# Spawn OpenHands
/acp spawn openhands --mode persistent --thread auto
```

Or via the OpenClaw API:

```bash
curl -X POST http://localhost:18789/api/v1/acp/spawn \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${OPENCLAW_API_KEY}" \
  -d '{
    "agent": "opencode",
    "mode": "persistent",
    "thread": "auto",
    "resources": {
      "memory": "2g",
      "cpu": "2.0"
    }
  }'
```

### Step 3: Check Agent Status

```bash
# Check status of all ACP agents
/acp status

# Expected output:
# ACP Agent Status
# +-----------+-----------+----------+---------+--------+-------+
# | Agent     | Thread    | Mode     | Status  | Memory | CPU   |
# +-----------+-----------+----------+---------+--------+-------+
# | opencode  | thrd_abc  | persist  | running | 1.2GB  | 0.3   |
# | openhands | thrd_def  | persist  | running | 2.1GB  | 0.5   |
# +-----------+-----------+----------+---------+--------+-------+

# Or via API:
curl -s http://localhost:18789/api/v1/acp/status \
  -H "Authorization: Bearer ${OPENCLAW_API_KEY}" | jq .
```

### Step 4: Send Messages to ACP Agents

```bash
# Send a task to the OpenCode ACP agent
curl -X POST http://localhost:18789/api/v1/acp/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${OPENCLAW_API_KEY}" \
  -d '{
    "agent": "opencode",
    "thread": "thrd_abc",
    "message": {
      "role": "user",
      "content": "Review the security of our authentication middleware and suggest improvements."
    }
  }'

# The response is streamed or returned when complete, depending on config
```

### Step 5: Manage Agent Lifecycle

```bash
# Pause an agent (saves state, frees resources)
/acp pause opencode --thread thrd_abc

# Resume a paused agent
/acp resume opencode --thread thrd_abc

# Kill an agent (terminates, loses state)
/acp kill opencode --thread thrd_abc

# List all threads for an agent
/acp threads opencode

# View agent logs
/acp logs opencode --thread thrd_abc --tail 50
```

### When to Use

- **Multi-turn conversations** where context must be preserved
- Long-running development sessions
- Agents that need to maintain state (file system, environment)
- You want full lifecycle control (spawn, pause, resume, kill)
- Tightly coupled workflows where agents interact with each other

### ACP vs Webhook Comparison

| Feature                  | Webhook (Pattern 2) | ACP (Pattern 3)     |
|--------------------------|---------------------|----------------------|
| State persistence        | Stateless           | Stateful             |
| Multi-turn conversation  | Manual              | Built-in             |
| Resource management      | Per-request         | Per-agent lifecycle  |
| Complexity               | Medium              | High                 |
| Cross-machine support    | Yes (HTTP)          | Yes (ACP over TCP)   |
| Pause/Resume             | No                  | Yes                  |
| Best for                 | One-shot tasks      | Development sessions |

---

## Recommended Setup

For most homelab use cases, start with **Pattern 2 (Webhooks)** and add **Pattern 3 (ACP)** when you need persistent agent sessions:

1. **Pattern 1** for quick model queries via OpenClaw
2. **Pattern 2** for production task delegation (automated workflows, CI/CD)
3. **Pattern 3** for interactive development sessions (pair programming with AI)

All three patterns can coexist in the same `openclaw.json` configuration.

---

**Next step**: Proceed to `04_DGX_SPARK_SETUP.md` to deploy the compute engine.
