# Engineering Audit — NewFire Stack

**Date:** 2026-07-19  
**Auditor:** OpenHands Agent  
**Branch:** `audit/robustness-2026-07-19`  
**Repository:** `berylm1/newfire`

---

## Executive Summary

NewFire is a multi-tenant AI infrastructure stack designed for legal and nonprofit use cases. It combines local LLM serving (Ollama/vLLM), LiteLLM routing, FastAPI microservices, Qdrant vector search, Cloudflare Tunnel ingress, and agent-based workflows (LangGraph agents per tenant feature). The architecture is pragmatic and modular but carries significant production-readiness gaps around secrets management, observability wiring, and deployment automation.

**Production-Readiness Score: 4/10**

The stack demonstrates solid architectural thinking — multi-tenancy, shared LLM config, service isolation, and agent orchestration are well conceived. However, critical production concerns remain: hardcoded credentials, no secrets management beyond `.env` files, incomplete observability, no Kubernetes manifests, and limited CI coverage. The fixes implemented in this audit address the highest-value, lowest-risk gaps.

---

## Per-Subsystem Findings

### 1. Orchestration & Workflow (Temporal / Workflow Engine)

**Status:** Not implemented  
**Risk:** Medium

The codebase uses LangGraph for agent workflows (per-tenant features like `daily_briefing`, `citation_checker`, `intake_conflict_check`). Each feature has its own `graph.py` defining a LangGraph agent with checkpointing to SQLite. There is no Temporal or distributed workflow engine.

**Findings:**
- LangGraph SQLite checkpoints (`langgraph-checkpoint-sqlite`) provide local durability but no distributed coordination
- No workflow retry, timeout, or saga compensation patterns
- `resume_approvals.py` shows awareness of resumption needs but is ad hoc

**Recommendation:** For production multi-step agent workflows, evaluate Temporal or LangGraph's built-in persistence with PostgreSQL. Not urgent for local dev.

---

### 2. Event Streaming (Kafka / Fluvio)

**Status:** Not implemented  
**Risk:** Low

No Kafka or Fluvio deployment. Inter-service communication happens via direct HTTP calls between FastAPI services. The `webhook_service` and `notify_service` provide inbound/outbound event handling as HTTP endpoints.

**Findings:**
- `webhook_service/main.py` stores events in JSON files — no persistent queue
- `activity_log_service` provides append-only event logging via HTTP
- No event fan-out, replay, or at-least-once delivery guarantees

**Recommendation:** Acceptable for current scope. If real-time event processing becomes critical, add NATS or Redis Streams as a lightweight alternative to Kafka.

---

### 3. Data Layer (Postgres, PgBouncer, TigerBeetle)

**Status:** Partial (Postgres referenced, not deployed in this repo)  
**Risk:** High

PostgreSQL is referenced throughout (DB_HOST, DB_USER, DB_PASSWORD env vars in docker-compose), but no migration files, PgBouncer config, or TigerBeetle ledger exist in this repository.

**Findings:**
- `newfire_backend_docker/docker-compose.yml` references DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME but no database service is defined in the compose file
- No migration framework (Alembic, Prisma, etc.) — schema management is external
- Most tenant services use JSON files for persistence (`sent_log.json`, etc.)
- Qdrant is used for vector storage but has no backup/restore config

**Recommendation:** Add Alembic migrations for the Postgres schema. Define the database service in docker-compose. Consider PgBouncer when scaling beyond single-instance Postgres.

---

### 4. Authentication & Authorization (Keycloak, Permify)

**Status:** JWT-based (JWT_SECRET in docker-compose)  
**Risk:** Medium

Authentication is JWT-based via the backend service (`JWT_SECRET` env var). No Keycloak deployment, Permify authorization model, or RBAC configuration exists in this repository.

**Findings:**
- `JWT_SECRET` is an env var with no rotation mechanism
- No API-level auth middleware on the tenant microservices
- `litellm_super_vllm_route.yaml` references consumer keys but no Keycloak OIDC integration
- APISIX consumer config (`apisix_consumer_sherifah.json`) shows per-consumer auth but is isolated to one deployment

**Recommendation:** For production, deploy Keycloak for OIDC-based auth and add auth middleware to tenant services. Consider Permify for fine-grained multi-tenant authorization.

---

### 5. Search & Observability (OpenSearch, Prometheus, Grafana, Jaeger, Loki)

**Status:** Not implemented  
**Risk:** High

No OpenSearch, Prometheus, Grafana, Jaeger, or Loki deployment exists in this repository.

**Findings:**
- FastAPI services have no metrics endpoints (`/metrics` not exposed)
- No structured logging (uses Python print/stderr)
- Docker logging driver is `json-file` with 10m/3-file rotation — adequate for container logs but no aggregation
- No distributed tracing (no OpenTelemetry instrumentation)
- No alerting or retention policies

**Recommendation:** Add Prometheus metrics endpoint to FastAPI services (`prometheus-fastapi-instrumentator`). Deploy Loki for log aggregation and Grafana for dashboards. Add OpenTelemetry tracing for cross-service observability.

---

### 6. API Gateway (APISIX)

**Status:** Config files exist, no declarative routing  
**Risk:** Medium

APISIX configuration exists (`apisix_support_20250913_121645.tgz`, `apisix-debug.sh`, route/consumer JSON files). Admin API URL is referenced in docker-compose.

**Findings:**
- `APISIX_ADMIN_URL` defaults to `http://172.17.0.1:9180` (hardcoded Docker gateway IP — **fixed** in docker-compose)
- Route and consumer configs are standalone JSON files, not version-controlled in a reproducible format
- No rate limiting config visible in repo (backend has `CLIENT_RATE_LIMIT_RPS/BURST/DAILY_QUOTA` env vars)
- No APISIX plugin declarative config (JWT auth, CORS, etc.)

**Recommendation:** Move APISIX routes to a version-controlled declarative format (YAML/JSON). Add CORS and rate-limiting plugins. Consider APISIX dashboard for management.

---

### 7. Secrets Management (Vault)

**Status:** Environment variables only  
**Risk:** **Critical**

No HashiCorp Vault or equivalent secrets management. All secrets are env vars passed to Docker containers.

**Findings:**
- `newfire_backend_docker/docker-compose.yml` passes `DB_PASSWORD`, `OPENROUTER_KEY`, `JWT_SECRET`, `OPENCLAW_TOKEN`, `QDRANT_API_KEY`, `APISIX_ADMIN_KEY` as env vars
- `litellm-config.yaml` (inferred from `nss_auto_router.py`) likely contains API keys
- `.env` files are referenced but no `.env.example` existed for the backend (fixed for nonprofit tenant)
- No secret rotation, audit trail, or encryption at rest

**Recommendation:** Deploy Vault or use Docker secrets for production. At minimum, add `.env.example` files documenting all required secrets. Never commit `.env` files to git.

---

### 8. Container/Sandbox Runtime (Dapr, Sandbox)

**Status:** Docker Compose only  
**Risk:** Low

No Dapr placement service or sandbox runtime. Deployment is via Docker Compose files.

**Findings:**
- `newfire_backend_docker/Dockerfile` and `docker-compose.yml` for backend
- `infra/dev-hub/Dockerfile` and `infra/codeep/Dockerfile` for dev tooling
- No container security scanning (Trivy, etc.)
- No resource limits (CPU/memory) on containers

**Recommendation:** Add resource limits to all services in docker-compose. Add Trivy scan to CI pipeline. Consider Dapr for service-to-service communication if scaling to distributed deployment.

---

### 9. Payments (Mojaloop)

**Status:** Not implemented  
**Risk:** N/A

No Mojaloop integration exists in this codebase.

**Recommendation:** Defer until payment processing is a requirement. When needed, follow Mojaloop's simulation environment guide for testing.

---

### 10. Agent Harnesses (OpenHands/OpenCode/OpenClaw)

**Status:** Partially implemented  
**Risk:** Medium

OpenClaw is referenced (`OPENCLAW_URL`, `OPENCLAW_TOKEN` in docker-compose). OpenHands integration exists via tool probing (`tool_probe_vllm.py`).

**Findings:**
- Agent harnesses are configured per-tenant but lack centralized config
- `tool_probe_vllm.py` validates vLLM endpoint compatibility with OpenHands
- `shared/llm_config.py` centralizes LLM endpoint config (**already implemented** in this audit)
- `shared/document_vision.py` provides vision model config
- `shared/whatsapp_intake_handler.py` integrates LLM with WhatsApp intake workflow
- No agent persistence beyond LangGraph SQLite checkpoints

**Recommendation:** Consolidate agent config into a shared registry. Add agent health monitoring and graceful shutdown. Consider persistent agent state in Postgres instead of SQLite.

---

### 11. Infrastructure-as-Code / Deployment

**Status:** Docker Compose + Cloudflare Tunnel  
**Risk:** Medium

Deployment is via Docker Compose files and Cloudflare Tunnel (`infra/cloudflared/config.yml`, `cloudflared-config-current.yml`).

**Findings:**
- `infra/cloudflared/config.yml` configures Cloudflare Tunnel for ingress
- `infra/codeep/` and `infra/dev-hub/` provide dev environment Dockerfiles
- No Kubernetes manifests, Helm charts, or Terraform
- `progress/` directory contains deployment artifacts (not version-controlled strategy)
- No CI/CD deployment pipeline (only lint+test in GitHub Actions)
- Hardcoded host paths in docker-compose (**fixed** in this audit)
- Hardcoded IPs (`172.17.0.1`, `100.88.112.5`) in docker-compose (**fixed** in this audit)

**Recommendation:** For production, add Kubernetes manifests or Nomad jobs. Add deployment stage to CI pipeline. Move Cloudflare Tunnel config to a secrets store.

---

### 12. Cross-Service Contracts

**Status:** Shared Python modules, informal contracts  
**Risk:** Medium

Tenant services communicate via HTTP with JSON payloads. No OpenAPI schema registry, versioning, or contract testing.

**Findings:**
- `shared/llm_config.py` provides centralized LLM configuration (**consolidated** in this audit)
- `shared/document_vision.py`, `shared/process_webhook_events.py`, `shared/resume_approvals.py` provide shared utilities
- Each service has its own `client.py` for calling other services
- No API versioning strategy
- `requirements.txt` files duplicate dependencies across services
- FastAPI auto-generates OpenAPI schemas but they're not shared or validated

**Recommendation:** Consolidate requirements into a shared `pyproject.toml` or `requirements-shared.txt`. Add OpenAPI schema export and contract testing. Consider Protocol Buffers for strongly-typed inter-service messages.

---

## What Was Implemented

| Fix | Files Changed | Commit |
|-----|--------------|--------|
| Centralize LLM config to `shared/llm_config.py` | 7 graph files + `llm_config.py` | Prior session |
| Production SMTP backend for notify_service | `tenants/legal/services/notify_service/backends.py` | Prior session |
| CI pipeline improvements (parallel lint+test, error handling, coverage check) | `.github/workflows/ci.yml` | `7ef94a6` |
| Docker-compose fixes (relative paths, env_file, host.docker.internal, healthcheck, defaults) | `newfire_backend_docker/docker-compose.yml` | `7ef94a6` |
| Nonprofit tenant `.env.example` | `tenants/nonprofit/.env.example` | `7ef94a6` |
| Tests for rag_service | `tenants/legal/services/rag_service/tests/test_rag_main.py` | `316411d` |
| Tests for citation_checker | `tenants/legal/citation_checker/tests/test_citation_checker.py` | `316411d` |

---

## What Remains as Recommendations

### High Priority
1. **Secrets management:** Deploy Vault or Docker secrets; add `.env.example` for backend
2. **Postgres deployment:** Add database service to docker-compose; implement Alembic migrations
3. **Observability:** Add Prometheus metrics, Loki log aggregation, Grafana dashboards
4. **API gateway config:** Declarative APISIX routes with CORS/rate-limiting plugins
5. **Container security:** Add resource limits and Trivy scanning to CI

### Medium Priority
6. **Agent persistence:** Migrate LangGraph checkpoints from SQLite to PostgreSQL
7. **Auth middleware:** Add JWT validation to tenant service endpoints
8. **Dependency consolidation:** Shared requirements or pyproject.toml
9. **Kubernetes manifests:** For production multi-node deployment
10. **APISIX dashboard:** For route/consumer management UI

### Lower Priority
11. **Workflow engine:** Evaluate Temporal for distributed agent orchestration
12. **Event streaming:** Add NATS/Redis Streams if real-time processing needed
13. **Permify authorization:** Fine-grained multi-tenant RBAC
14. **Mojaloop payments:** Defer until payment processing is required

---

## Production-Readiness Scorecard

| Category | Score | Notes |
|----------|-------|-------|
| LLM Infrastructure | 7/10 | Centralized config, LiteLLM+vLLM routing, multi-model support |
| Service Architecture | 6/10 | Good separation of concerns; missing auth middleware and observability |
| Data Management | 3/10 | JSON-file persistence, no migrations, no backups |
| Security | 3/10 | No secrets management, no RBAC, env vars for sensitive data |
| CI/CD | 5/10 | Lint+test pipeline exists; no deployment, no security scanning |
| Observability | 2/10 | No metrics, no structured logging, no tracing |
| Deployment | 4/10 | Docker Compose + Cloudflare Tunnel works; no K8s, no IaC |
| Testing | 5/10 | 17 test files exist; coverage gaps in rag_service and citation_checker (fixed) |

**Overall: 4/10** — Solid architectural foundation with significant production gaps in secrets, observability, data management, and deployment automation.

---

## Branch

All fixes committed to `audit/robustness-2026-07-19`:

```
git log --oneline audit/robustness-2026-07-19
```

Review and merge at your discretion.
