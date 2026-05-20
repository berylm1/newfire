# OpenRouter Integration -- Unified Cloud LLM Gateway

## What is OpenRouter?

OpenRouter is a unified API gateway that provides access to 200+ LLM models from multiple providers (Anthropic, OpenAI, Google, xAI, Meta, DeepSeek, etc.) through a single API key and endpoint. It handles:

- Model routing and load balancing
- Provider failover
- Rate limit management
- Cost tracking
- Free-tier model access

**API Endpoint**: `https://openrouter.ai/api/v1`

## Prerequisites

1. Create an OpenRouter account at https://openrouter.ai
2. Generate an API key from https://openrouter.ai/settings/keys
3. Add credits (or use free-tier models for testing)

```bash
# Store the API key securely
export OPENROUTER_API_KEY="sk-or-v1-XXXXXXXXXXXXXXXXXXXXXXXX"

# Test the key works
curl -s https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" | jq '.data | length'
# Should return a number (200+)
```

---

## Integration 1: OpenClaw + OpenRouter

### Step 1: Onboard OpenRouter as a Provider

```bash
# On the Minisforum
ssh newwaveclaw@192.168.1.157

# Run the onboard command with OpenRouter as the token provider
openclaw onboard \
  --auth-choice apiKey \
  --token-provider openrouter \
  --token "$OPENROUTER_API_KEY"
```

### Step 2: Configure OpenRouter in openclaw.json

Edit `/etc/openclaw/openclaw.json`:

```json
{
  "providers": {
    "openrouter": {
      "type": "openrouter",
      "endpoint": "https://openrouter.ai/api/v1",
      "apiKey": "${OPENROUTER_API_KEY}",
      "defaultHeaders": {
        "HTTP-Referer": "http://homelab.local",
        "X-Title": "AI Homelab"
      },
      "models": {
        "defaults": {
          "temperature": 0.7,
          "maxTokens": 4096
        },
        "available": [
          {
            "id": "openrouter/anthropic/claude-sonnet-4-5",
            "displayName": "Claude Sonnet 4.5 (via OpenRouter)",
            "contextWindow": 200000,
            "maxOutputTokens": 64000,
            "pricing": {
              "input": 3.0,
              "output": 15.0
            }
          },
          {
            "id": "openrouter/anthropic/claude-opus-4",
            "displayName": "Claude Opus 4 (via OpenRouter)",
            "contextWindow": 200000,
            "maxOutputTokens": 32000,
            "pricing": {
              "input": 15.0,
              "output": 75.0
            }
          },
          {
            "id": "openrouter/google/gemini-2.5-pro",
            "displayName": "Gemini 2.5 Pro (via OpenRouter)",
            "contextWindow": 1000000,
            "maxOutputTokens": 65536
          },
          {
            "id": "openrouter/deepseek/deepseek-r1",
            "displayName": "DeepSeek R1 (via OpenRouter)",
            "contextWindow": 128000,
            "maxOutputTokens": 32000
          },
          {
            "id": "openrouter/x-ai/grok-4",
            "displayName": "Grok 4 (via OpenRouter)",
            "contextWindow": 131072,
            "maxOutputTokens": 32000
          }
        ]
      },
      "rateLimiting": {
        "requestsPerMinute": 60,
        "tokensPerMinute": 100000,
        "dailyBudget": 10.00
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "ollama/llama3.1:70b",
        "fallback": "openrouter/anthropic/claude-sonnet-4-5"
      }
    }
  }
}
```

### Step 3: Provider Pinning

OpenRouter routes requests to the cheapest/fastest provider by default. You can pin to specific infrastructure providers for consistency:

```json
{
  "providers": {
    "openrouter": {
      "providerPinning": {
        "enabled": true,
        "only": ["deepinfra", "inceptron", "nebius"],
        "comment": "Pin to these infrastructure providers for lower latency and cost"
      }
    }
  }
}
```

To use provider pinning in API calls:

```bash
# Specify provider preferences in the request
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic/claude-sonnet-4-5",
    "messages": [{"role": "user", "content": "Hello"}],
    "provider": {
      "only": ["deepinfra", "inceptron", "nebius"],
      "allow_fallbacks": true
    }
  }'
```

In `openclaw.json`, configure this globally:

```json
{
  "providers": {
    "openrouter": {
      "requestDefaults": {
        "provider": {
          "only": ["deepinfra", "inceptron", "nebius"],
          "allow_fallbacks": true,
          "order": ["throughput"]
        }
      }
    }
  }
}
```

### Step 4: Multi-Key Support for Load Balancing

For high-throughput workloads, use multiple API keys to distribute requests and avoid rate limits:

```json
{
  "providers": {
    "openrouter": {
      "loadBalancing": {
        "strategy": "round-robin",
        "keys": [
          {
            "name": "primary",
            "apiKey": "${OPENROUTER_API_KEY_1}",
            "weight": 3,
            "budgetLimit": 50.00
          },
          {
            "name": "secondary",
            "apiKey": "${OPENROUTER_API_KEY_2}",
            "weight": 2,
            "budgetLimit": 30.00
          },
          {
            "name": "free-tier",
            "apiKey": "${OPENROUTER_API_KEY_3}",
            "weight": 1,
            "budgetLimit": 0,
            "modelsOnly": ["*:free"]
          }
        ],
        "failover": {
          "enabled": true,
          "onRateLimit": true,
          "onBudgetExhausted": true
        }
      }
    }
  }
}
```

Set the environment variables:

```bash
# Add multiple keys to the environment file
sudo tee -a /etc/openclaw/env << 'EOF'
OPENROUTER_API_KEY_1=sk-or-v1-primary-key-here
OPENROUTER_API_KEY_2=sk-or-v1-secondary-key-here
OPENROUTER_API_KEY_3=sk-or-v1-free-tier-key-here
EOF

sudo systemctl restart openclaw
```

---

## Integration 2: OpenCode + OpenRouter

### Step 1: Configure OpenCode to Use OpenRouter

```bash
# Use the ocode CLI to configure OpenRouter as the model provider
ocode openrouter --model x-ai/grok-4-fast:free
```

Or configure manually in `~/.config/opencode/opencode.json`:

```json
{
  "model": {
    "provider": "openrouter",
    "endpoint": "https://openrouter.ai/api/v1",
    "apiKey": "${OPENROUTER_API_KEY}",
    "model": "x-ai/grok-4-fast:free",
    "headers": {
      "HTTP-Referer": "http://homelab.local",
      "X-Title": "AI Homelab - OpenCode"
    }
  },
  "modelPresets": {
    "fast-free": {
      "provider": "openrouter",
      "model": "x-ai/grok-4-fast:free",
      "description": "Fast free model for quick tasks"
    },
    "smart-paid": {
      "provider": "openrouter",
      "model": "anthropic/claude-sonnet-4-5",
      "description": "Smart paid model for complex tasks"
    },
    "reasoning": {
      "provider": "openrouter",
      "model": "deepseek/deepseek-r1",
      "description": "Reasoning model for complex problems"
    },
    "local-gpu": {
      "provider": "ollama",
      "endpoint": "http://192.168.1.158:11434",
      "model": "llama3.1:70b",
      "description": "Local GPU model on DGX Spark"
    }
  }
}
```

### Step 2: Test OpenCode with OpenRouter

```bash
# Test with the free model
ocode chat --model openrouter/x-ai/grok-4-fast:free "Write a Python hello world"

# Test with a paid model
ocode chat --model openrouter/anthropic/claude-sonnet-4-5 "Explain async/await in Python"

# Switch between presets
ocode chat --preset fast-free "Quick question about git"
ocode chat --preset smart-paid "Design a microservices architecture"
```

---

## Integration 3: Smart Routing (Local First, Cloud Fallback)

The most powerful setup: try local DGX models first, fall back to OpenRouter cloud if local is unavailable or overloaded.

### Configure Smart Routing in openclaw.json

```json
{
  "routing": {
    "strategy": "tiered",
    "tiers": [
      {
        "name": "local-dgx",
        "priority": 1,
        "description": "Try DGX Spark GPU models first (free, fast, private)",
        "providers": ["dgx-nemoclaw", "dgx-ollama"],
        "conditions": {
          "health": "healthy",
          "memoryAvailable": { "gte": "5GB" },
          "queueDepth": { "lte": 10 }
        },
        "models": {
          "deepseek-r1": "dgx-nemoclaw/deepseek-r1",
          "glm-5": "dgx-nemoclaw/glm-5",
          "llama3.1:70b": "dgx-ollama/llama3.1:70b",
          "codellama:70b": "dgx-ollama/codellama:70b"
        }
      },
      {
        "name": "local-cpu",
        "priority": 2,
        "description": "Fall back to Minisforum CPU models (free, slower)",
        "providers": ["local-ollama"],
        "conditions": {
          "health": "healthy"
        },
        "models": {
          "llama3.1:8b": "local-ollama/llama3.1:8b",
          "codellama:7b": "local-ollama/codellama:7b"
        }
      },
      {
        "name": "cloud-openrouter",
        "priority": 3,
        "description": "Fall back to OpenRouter cloud (paid, always available)",
        "providers": ["openrouter"],
        "conditions": {
          "always": true
        },
        "models": {
          "claude-sonnet-4-5": "openrouter/anthropic/claude-sonnet-4-5",
          "claude-opus-4": "openrouter/anthropic/claude-opus-4",
          "grok-4": "openrouter/x-ai/grok-4",
          "deepseek-r1": "openrouter/deepseek/deepseek-r1"
        }
      }
    ],
    "modelAliases": {
      "default": "deepseek-r1",
      "code": "codellama:70b",
      "reasoning": "deepseek-r1",
      "creative": "claude-sonnet-4-5",
      "fast": "llama3.1:8b"
    },
    "fallbackBehavior": {
      "onLocalUnavailable": "cloud-openrouter",
      "onLocalOverloaded": "cloud-openrouter",
      "onCloudRateLimit": "local-cpu",
      "onAllFailed": {
        "action": "queue",
        "retryAfter": 60
      }
    }
  }
}
```

### How Smart Routing Works

```
User Request: "Generate a REST API for user management"
  |
  v
OpenClaw Routing Engine
  |
  +--[1] Check DGX Spark (local-dgx tier)
  |      Is healthy? Memory available? Queue not full?
  |      YES --> Route to DGX DeepSeek-R1 (free, GPU-fast)
  |      NO  --> Fall through
  |
  +--[2] Check Minisforum Ollama (local-cpu tier)
  |      Is healthy? Has the requested model?
  |      YES --> Route to local Ollama (free, CPU-slower)
  |      NO  --> Fall through
  |
  +--[3] Route to OpenRouter (cloud tier)
         Always available (if API key has credits)
         Route to claude-sonnet-4-5 via OpenRouter (paid)
```

### Test Smart Routing

```bash
# This should route to DGX first, then fall back
curl -X POST http://localhost:18789/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${OPENCLAW_API_KEY}" \
  -d '{
    "model": "default",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Check which tier was used (look at response headers)
curl -v -X POST http://localhost:18789/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${OPENCLAW_API_KEY}" \
  -d '{
    "model": "default",
    "messages": [{"role": "user", "content": "Hello"}]
  }' 2>&1 | grep "X-Route"

# Expected: X-Route-Tier: local-dgx  (or cloud-openrouter if DGX is down)
```

---

## Cost Management

### Set Daily Budgets

```json
{
  "providers": {
    "openrouter": {
      "costManagement": {
        "dailyBudget": 10.00,
        "monthlyBudget": 200.00,
        "alertThresholds": [0.50, 0.80, 0.95],
        "onBudgetExhausted": "fallback-to-local",
        "tracking": {
          "byModel": true,
          "byAgent": true,
          "byTenant": true,
          "logPath": "/var/log/openclaw/costs/"
        }
      }
    }
  }
}
```

### Monitor Costs

```bash
# Check current spend via OpenRouter API
curl -s https://openrouter.ai/api/v1/auth/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" | jq .

# Check spend in OpenClaw
openclaw costs show --period today
openclaw costs show --period month --by-model

# Expected output:
# Cost Report (Today)
# MODEL                          REQUESTS   TOKENS      COST
# anthropic/claude-sonnet-4-5    45         125,000     $0.94
# deepseek/deepseek-r1           12         45,000      $0.13
# x-ai/grok-4-fast:free          200        500,000     $0.00
# ---------------------------------------------------- ------
# TOTAL                          257        670,000     $1.07
```

---

## Free-Tier Models for Development

OpenRouter offers several free models. Use these for development and testing:

```json
{
  "freeModels": [
    "x-ai/grok-4-fast:free",
    "google/gemma-2-9b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free"
  ]
}
```

```bash
# Test with a free model (no credits needed)
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "x-ai/grok-4-fast:free",
    "messages": [{"role": "user", "content": "What is 2+2?"}]
  }'
```

---

## Environment Variables Summary

Add all OpenRouter-related variables to `/etc/openclaw/env`:

```bash
sudo tee -a /etc/openclaw/env << 'EOF'
# OpenRouter Configuration
OPENROUTER_API_KEY=sk-or-v1-your-primary-key-here
OPENROUTER_API_KEY_1=sk-or-v1-your-primary-key-here
OPENROUTER_API_KEY_2=sk-or-v1-your-secondary-key-here
OPENROUTER_API_KEY_3=sk-or-v1-your-free-tier-key-here
OPENROUTER_DAILY_BUDGET=10.00
OPENROUTER_MONTHLY_BUDGET=200.00
EOF

# Restart to load new variables
sudo systemctl restart openclaw
```

---

**Next step**: Proceed to `06_APISIX_METERING.md` to set up API gateway metering.
