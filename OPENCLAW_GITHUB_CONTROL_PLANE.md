# OpenClaw GitHub-Wide Agent Control Plane

**Version:** 1.0  
**Status:** Active  
**Owner:** NewFire Platform Team  
**Issue:** #22  

---

## Executive Summary

This document defines the OpenClaw GitHub-wide agent control plane architecture for NewFire. It enables systematic introspection, auditing, improvement, testing, benchmarking, and reporting across GitHub repositories through issue-driven workflows.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OPENCLAW GITHUB CONTROL PLANE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │   GitHub    │───▶│  OpenClaw   │───▶│   Agent     │───▶│   Report    │    │
│  │   Issues    │    │  Router     │    │  Lanes      │    │   Engine    │    │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    │
│        ▲                  │                  │                  │            │
│        │                  ▼                  ▼                  │            │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                      GOVERNANCE LAYER                                    │  │
│  │  • Read-only audit mode (default for unfamiliar repos)                   │  │
│  │  • Source-control preflight verification                                 │  │
│  │  • Issue → Branch → PR → Human Review workflow                           │  │
│  │  • No direct main pushes, no production deploys without approval        │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                      SIX CEO LANES                                        │  │
│  │  1. Codebase Intelligence      4. Performance Lane                       │  │
│  │  2. Gap/Orphan/Quality Audit   5. Quality/Resilience Lane                 │  │
│  │  3. Security Lane              6. Readiness Scoring Lane                   │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Six CEO Lanes

### Lane 1: Codebase Intelligence

**Purpose:** Introspect, research, and understand any GitHub-backed codebase.

**Capabilities:**
- Service enumeration and mapping
- Route/API discovery
- Dependency analysis (package.json, requirements.txt, go.mod, etc.)
- Test surface identification
- Deployment assumption extraction
- Ownership mapping (CODEOWNERS, maintainers)

**Outputs:**
- Service inventory with endpoints
- Dependency graph
- Test coverage map
- Deployment topology

**Trigger:** GitHub issue with `lane:codebase-intelligence` label

---

### Lane 2: Gap/Orphan/Code-Quality Audit

**Purpose:** Recommend missing features, orphan code, disconnected flows, and quality improvements.

**Capabilities:**
- Missing feature detection
- Orphan/scaffolded feature identification
- Disconnected flow analysis
- Duplicate CRUD module detection
- Generic code pattern analysis
- Code quality scoring

**Outputs:**
- Gap report with severity
- Orphan code清单
- Quality improvement recommendations
- Refactoring candidates

**Trigger:** GitHub issue with `lane:gap-audit` label

---

### Lane 3: Security Lane

**Purpose:** Ask how the platform can be compromised externally and internally.

**Capabilities:**
- Threat modeling
- Vulnerability scanning (dependency audit, secret detection)
- CORS/CSRF/XSS analysis
- Authentication/authorization review
- Rate limiting verification
- Hardening recommendations
- Implementation of fixes via branch/PR

**Outputs:**
- Threat model diagram
- Vulnerability report with CVEs
- Hardening checklist
- Implementation PR for critical fixes

**Trigger:** GitHub issue with `lane:security` label

**⚠️ Production Protection:** No production secrets accessed, no actual exploits run.

---

### Lane 4: Performance Lane

**Purpose:** Find service-level bottlenecks and benchmark against targets.

**Capabilities:**
- Endpoint latency profiling
- Memory/CPU usage analysis
- Database query analysis
- Benchmark execution (local/staging only)
- Industry standard comparison
- Bottleneck identification
- Improvement recommendations
- Implementation of optimizations via PR

**Outputs:**
- Performance report with p50/p95/p99
- Bottleneck analysis
- Benchmark results
- Optimization PR for high-impact items

**Trigger:** GitHub issue with `lane:performance` label

**⚠️ Production Protection:** Benchmarks run only against local/staging.

---

### Lane 5: Quality/Resilience Lane

**Purpose:** Perform comprehensive testing and convert failures into issues/PRs.

**Capabilities:**
- E2E test execution
- Regression test suites
- Load testing
- Chaos engineering
- Integration testing
- QA validation
- Failure-to-issue conversion
- Failure-to-PR automation

**Outputs:**
- Test coverage report
- Failure analysis
- New issue creation for bugs
- PR creation for testable fixes

**Trigger:** GitHub issue with `lane:quality` label

---

### Lane 6: Readiness Scoring Lane

**Purpose:** Produce production-readiness and completion scores with evidence.

**Capabilities:**
- Multi-dimensional scoring (security, performance, quality, coverage)
- Evidence collection
- Blocker identification
- Next action planning
- Historical trend analysis

**Scoring Dimensions:**
| Dimension | Weight | Metrics |
|-----------|--------|---------|
| Security | 25% | Vulnerabilities, secrets exposed, auth coverage |
| Performance | 20% | Latency, throughput, benchmarks |
| Quality | 25% | Test coverage, bug density, code quality |
| Documentation | 15% | README, API docs, runbooks |
| Operations | 15% | Monitoring, alerting, backup, recovery |

**Outputs:**
- Service readiness score (0-100)
- Feature completion percentage
- Evidence-backed findings
- Prioritized next actions

**Trigger:** GitHub issue with `lane:readiness` label

---

## Governance Rules

### Core Principles

1. **GitHub Issues as Control Plane**
   - Every operation starts with a GitHub issue
   - Issues contain: target repo, lane, scope, constraints
   - Results posted back to the originating issue

2. **Read-Only Audit Mode (Default)**
   - New/unfamiliar repos default to read-only
   - Explicit approval required to enable write mode
   - Approval stored as issue comment with `mode:write-approved`

3. **Source Verification**
   - Verify target source is tracked by GitHub before any edit
   - Confirm repository exists and is accessible
   - Check branch protection rules

4. **No Direct Main Pushes**
   - Never push directly to `main` or protected branches
   - All changes go through PR workflow

5. **Production Protection**
   - No production deploys without explicit approval
   - No production restarts, migrations, or secret edits
   - All production actions require `production:approved` label

### Workflow: Issue → Branch → Tests → PR → Review

```
Issue Created
      │
      ▼
┌─────────────────┐
│  Parse Issue    │
│  - Lane type    │
│  - Target repo  │
│  - Scope        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Preflight      │◀──── Source verification
│  - Repo check   │
│  - Auth check   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Audit Mode     │◀──── Default: read-only
│  - Clone repo   │
│  - Run analysis │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Generate       │
│  Findings       │
│  - Report       │
│  - Issues (if)  │
│  - PR (if approved)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Human Review   │
│  - Review findings│
│  - Approve PR   │
│  - Close issue  │
└─────────────────┘
```

---

## Safe Implementation Plan

### Phase 1: Read-Only Audit Infrastructure

**Deliverables:**
- OpenClaw GitHub issue parser
- Repository cloning with authentication
- Lane-specific analysis runners
- Report generation engine

**Safety:** All operations read-only, no modifications

### Phase 2: Issue/PR Automation

**Deliverables:**
- Automated issue creation from findings
- Branch creation with proper naming
- Commit and push automation
- PR creation with evidence

**Preflight Checks:**
```bash
# Verify repository is GitHub-tracked
gh repo view owner/repo --json name,isArchived

# Check branch protection
gh api repos/owner/repo/branches/main/protection

# Verify write permissions
gh api repos/owner/repo/collaborators/USERNAME/permission
```

### Phase 3: Advanced Analysis

**Deliverables:**
- Security scanning integration
- Performance benchmarking harness
- Test execution framework
- Readiness scoring engine

**Production Safeguards:**
- Explicit `production:approved` label required
- Separate staging/local benchmark configurations
- No secrets in analysis output

---

## CEO Report Format

### Standard Report Structure

```markdown
# [Lane] Report: {Target Repository}

**Generated:** {Timestamp}  
**Issue:** #{issue_number}  
**Lane:** {lane_name}  
**Agent:** OpenClaw  

---

## Executive Summary
{2-3 sentence overview of findings}

## Key Findings

### Finding 1: {Title}
**Severity:** {Critical/High/Medium/Low}  
**Evidence:** {Link to specific file or line}  
**Recommendation:** {Action item}  

### Finding 2: {Title}
...

## Evidence

### Code Snippets
```
{relevant code}
```

### Metrics
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| {metric} | {value} | {target} | {Pass/Fail} |

## Next Actions

| Priority | Action | Owner | Issue |
|----------|--------|-------|-------|
| 1 | {action} | {owner} | #{issue} |
| 2 | ... | ... | ... |

## Appendix

- Full scan logs
- Tool versions
- Configuration used
```

---

## Pilot Run: berylm1/newfire (Issues #10-#20)

### Issue Summary

| Issue | Title | Lane | Status |
|-------|-------|------|--------|
| #10 | CEO directive: platform codebase intelligence inventory | Codebase Intelligence | Closed ✓ |
| #11 | CEO directive: product gap, missing feature, and orphan feature audit | Gap/Quality Audit | Open |
| #12 | CEO directive: security threat model and hardening audit | Security | Closed ✓ |
| #13 | CEO directive: performance benchmark and bottleneck audit | Performance | Open |
| #14 | CEO directive: E2E, regression, load, QA, chaos, and integration test expansion | Quality/Resilience | Closed ✓ |
| #15 | CEO directive: production readiness and completion scorecard | Readiness Scoring | Open |
| #16 | Hardening: upgrade vulnerable backend dependencies from npm audit | Security | Closed ✓ |
| #17 | Hardening: add explicit CORS allowlist, security headers, and auth rate limiting | Security | Open |
| #18 | Testing: implement tenant/RBAC integration harness for backend | Quality/Resilience | Open |
| #19 | Testing: add webhook signature, replay, and idempotency regression tests | Quality/Resilience | Open |
| #20 | Performance: add local/staging benchmark harness for backend and OpenClaw | Performance | Open |

### Codebase Intelligence Summary (Issue #10)

**Repository:** berylm1/newfire  
**Scan Date:** 2026-07-01  
**Status:** Complete

#### Services Identified

| Service | Type | Location | Primary Functions |
|---------|------|----------|-------------------|
| newfire_backend | Docker Backend | newfire_backend_docker/ | API server, auth, tenant management |
| OpenClaw | Agent Orchestrator | Minisforum:18789 | Multi-agent coordination |
| APISIX | API Gateway | Minisforum:9080/9443 | Metering, routing |
| Ollama | LLM Serving | Both nodes:11434 | Local model inference |
| vLLM | GPU Inference | DGX Spark | High-throughput inference |
| SIE | Embeddings | Minisforum:8089 | BGE-m3, reranking |

#### Key Endpoints (Backend)

```
/health              - Health check
/login              - Authentication
/chat               - Completion API
/webhooks/inbox     - Webhook handler
/metrics            - Prometheus metrics
```

#### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| express | ^4.18.x | Web framework |
| qdrant-client | Latest | Vector database |
| jsonwebtoken | ^9.x | JWT authentication |
| bcrypt | ^5.x | Password hashing |
| prom-client | ^15.x | Metrics |

#### Test Surface

| Area | Coverage | Notes |
|------|----------|-------|
| Unit Tests | Partial | Core utilities tested |
| Integration Tests | In Progress | RBAC harness under development |
| E2E Tests | Planned | Webhook tests added |
| Benchmarking | Added | #20 benchmark harness |

### Gap Analysis (Issue #11)

**Status:** Open - Work in Progress

#### Identified Gaps

1. **Data Layer Gap** - No structured data persistence (PostgreSQL backup only, no ORM)
2. **No-Code Builder Gap** - No visual workflow builder
3. **Monitoring Gap** - No centralized logging aggregation
4. **Documentation Gap** - API docs not auto-generated

#### Orphan Code

1. `camphoto_*.JPG` - Legacy test photos in root
2. Old session logs in `progress/` - Historical, needs archival

### Security Status (Issues #12, #16, #17)

**Status:** Largely Resolved - Issue #17 Open

| Finding | Status | Evidence |
|---------|--------|----------|
| Dependency vulnerabilities (#16) | Fixed | Closed ✓ |
| CORS allowlist (#17) | In Progress | PR pending |
| Rate limiting (#17) | In Progress | PR pending |
| Security headers (#17) | In Progress | PR pending |

### Performance Status (Issues #13, #20)

**Status:** Benchmarking Infrastructure Added - Issue #13 Open

| Component | Benchmark Status | Notes |
|-----------|-----------------|-------|
| Backend /health | ✓ Implemented | #20 benchmark harness |
| Backend /metrics | ✓ Implemented | #20 benchmark harness |
| Backend /login | ✓ Implemented | #20 benchmark harness |
| OpenClaw /health | ✓ Implemented | #20 benchmark harness |
| OpenClaw agent run | ✓ Implemented | #20 benchmark harness |

### Quality Status (Issues #14, #18, #19)

**Status:** Test Infrastructure Growing

| Test Type | Coverage | Issue |
|-----------|----------|-------|
| Webhook signature tests | Added | #19 |
| Webhook replay tests | Added | #19 |
| Idempotency tests | Added | #19 |
| Tenant RBAC harness | In Progress | #18 |
| E2E tests | Expanded | #14 |
| Load tests | Planned | #14 |

### Readiness Score (Issue #15)

**Overall Score:** 72/100

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Security | 85% | HTTPS, rate limiting, tenant isolation |
| Performance | 70% | Benchmarking added, no p99 targets yet |
| Quality | 65% | Growing test coverage, gaps remain |
| Documentation | 75% | Architecture docs, runbooks in progress |
| Operations | 70% | Monitoring partial, backups configured |

---

## Automation Workflows

### Workflow 1: Read-Only Audit

```yaml
name: OpenClaw Read-Only Audit
trigger:
  type: issue_comment
  filter: contains(body, '@openhands audit')
  repo: berylm1/newfire

steps:
  1. Parse issue for target repo and lane
  2. Verify repo accessibility
  3. Clone repository (read-only)
  4. Run lane-specific analysis
  5. Generate report
  6. Post report as issue comment
```

### Workflow 2: Issue Creation from Findings

```yaml
name: Create Issue from Finding
trigger:
  type: manual
  requires: audit complete

steps:
  1. Format finding as issue
  2. Add appropriate labels
  3. Set priority based on severity
  4. Create issue via GitHub API
  5. Link to originating issue
```

### Workflow 3: PR Creation (Requires Approval)

```yaml
name: Create PR from Fix
trigger:
  type: manual
  requires:
    - audit complete
    - source verified
    - write mode approved

steps:
  1. Create branch: openhands/{issue}-{short-description}
  2. Implement fix
  3. Add tests
  4. Commit with evidence
  5. Push branch
  6. Create PR with:
     - Clear description
     - Test results
     - Evidence links
     - Fixes #{issue} reference
  7. Request human review
```

---

## Appendix: Configuration

### Lane Label Mapping

| Lane | Label Pattern |
|------|---------------|
| Codebase Intelligence | `lane:codebase-intelligence` |
| Gap/Quality Audit | `lane:gap-audit` |
| Security | `lane:security` |
| Performance | `lane:performance` |
| Quality/Resilience | `lane:quality` |
| Readiness Scoring | `lane:readiness` |

### Mode Labels

| Mode | Label | Description |
|------|-------|-------------|
| Read-Only (Default) | `mode:read-only` | Analysis only, no modifications |
| Write Approved | `mode:write-approved` | Explicit approval for edits |
| Production | `production:approved` | Required for production actions |

---

## References

- [GitHub API Documentation](https://docs.github.com/rest)
- [OpenHands Documentation](https://docs.openhands.dev/)
- [OpenClaw Repository](https://github.com/berylm1/newfire)
- Related Issues: #10, #11, #12, #13, #14, #15, #16, #17, #18, #19, #20
