# Multi-Tenant Architecture Plan

## Confirmed: NemoClaw Supports Multiple Sandboxes

Verified on April 4, 2026. `nemoclaw list` shows sandboxes, `nemoclaw onboard` creates new ones. Each sandbox gets full isolation (Landlock + seccomp + network namespace).

## Current State

```
NemoClaw on DGX Spark:
  Sandboxes:
    my-assistant * (default)
      model: glm4:9b
      provider: ollama-local
      GPU: yes
      policies: pypi, npm
```

## Target State (Multi-Tenant)

```
NemoClaw on DGX Spark:
  Sandboxes:
    system * (default, admin)
      model: deepseek-r1:32b-8k
      GPU: yes

    tenant-a (Customer A)
      model: deepseek-r1:32b-8k
      GPU: yes
      policies: pypi, npm
      isolation: Landlock + seccomp + netns

    tenant-b (Customer B)
      model: glm4:9b
      GPU: yes
      policies: pypi, npm
      isolation: Landlock + seccomp + netns
```

## How the Full Multi-Tenant Flow Works

```
Customer A (API key: app-a-research-2026)
  |
  +--[OpenZiti tunnel]--> APISIX (:9080)
                            |
                            +--[key-auth]--> identifies as "app-a"
                            +--[rate-limit]--> 2 req/sec
                            +--[route]--> DGX Spark Ollama
                                            |
                                            +--[NemoClaw sandbox: tenant-a]
                                                isolated GPU, isolated network
                                                isolated filesystem
```

## Layers of Isolation

| Layer | Technology | What It Isolates |
|-------|-----------|-----------------|
| Network access | OpenZiti | Only authorized clients can connect, zero open ports |
| API authentication | APISIX key-auth | Each tenant has unique API key |
| Rate limiting | APISIX limit-req | Per-tenant request quotas |
| Token metering | APISIX (future: Redis) | Per-tenant token usage tracking |
| Compute isolation | NemoClaw sandbox | Separate Landlock + seccomp + netns per tenant |
| GPU memory | NemoClaw (per-sandbox model) | Each tenant gets assigned models |
| Filesystem | NemoClaw sandbox | Separate workdir, read-only system paths |
| Process | NemoClaw seccomp | Restricted syscalls per sandbox |
| Auto-scaling | KEDA (future) | Scale workers per tenant demand |
| Orchestration | KubeClaw/K3s (future) | Pod-level isolation, resource quotas |

## Steps to Implement (Next Session)

1. Create a second sandbox for testing:
   ```bash
   nemoclaw onboard
   # Name it "tenant-test"
   # Assign a different model (e.g., glm4:9b)
   ```

2. Verify both sandboxes are isolated:
   ```bash
   nemoclaw list
   nemoclaw my-assistant status
   nemoclaw tenant-test status
   ```

3. Create a second APISIX route that maps to the new sandbox

4. Test that tenant-a API key reaches sandbox-a, tenant-b reaches sandbox-b

## Future: KEDA Auto-Scaling Per Tenant

```
KEDA watches:
  +-- Tenant A request rate > 5/sec?  --> Scale up tenant-a workers
  +-- Tenant B idle for 10 min?       --> Scale down tenant-b workers
  +-- GPU memory > 80%?               --> Route overflow to OpenRouter cloud
  +-- Business hours (8 AM-6 PM)?     --> Pre-scale to 3 workers per tenant
```

## Revenue Model

| Tier | Monthly Price | Includes | Rate Limit |
|------|-------------|----------|------------|
| Free | $0 | 10K tokens/day, free models only | 1 req/sec |
| Starter | $29 | 500K tokens/day, all local models | 5 req/sec |
| Pro | $99 | 2M tokens/day, all models + cloud | 20 req/sec |
| Enterprise | Custom | Dedicated sandbox, custom models | Custom |

All local inference is free to you after hardware cost. Cloud fallback (OpenRouter) is the only variable cost, and it only triggers when local is unavailable.
