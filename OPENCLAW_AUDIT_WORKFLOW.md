# OpenClaw Audit Workflow

**Version:** 1.0  
**Parent:** [OPENCLAW_GITHUB_CONTROL_PLANE.md](./OPENCLAW_GITHUB_CONTROL_PLANE.md)  
**Issue:** #22  

---

## Overview

This document describes the minimal workflow for selecting repositories and issues, then running read-only audit passes using the OpenClaw GitHub-wide agent control plane.

---

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AUDIT WORKFLOW                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌───────────────┐                                                               │
│  │  GitHub Issue │  ← Create issue with target repo and lane                    │
│  │  with Lane    │                                                               │
│  └───────┬───────┘                                                               │
│          │                                                                       │
│          ▼                                                                       │
│  ┌───────────────┐                                                               │
│  │  Agent Parses │  ← Extract: repo, lane, scope, constraints                  │
│  │  Issue        │                                                               │
│  └───────┬───────┘                                                               │
│          │                                                                       │
│          ▼                                                                       │
│  ┌───────────────┐                                                               │
│  │  Repo Check   │  ← Verify GitHub tracking, accessibility, auth               │
│  │  Preflight    │                                                               │
│  └───────┬───────┘                                                               │
│          │                                                                       │
│          ▼                                                                       │
│  ┌───────────────┐     ┌───────────────┐                                        │
│  │  Clone Repo   │────▶│  Read-Only     │  ← Default mode                       │
│  │  (if needed)  │     │  Analysis      │                                        │
│  └───────────────┘     └───────┬───────┘                                        │
│                                │                                                 │
│                                ▼                                                 │
│                    ┌───────────────────────┐                                     │
│                    │  Lane-Specific Audit  │                                     │
│                    ├───────────────────────┤                                     │
│                    │ 1. Codebase Intel     │                                     │
│                    │ 2. Gap/Quality Audit  │                                     │
│                    │ 3. Security Scan      │                                     │
│                    │ 4. Performance Bench  │                                     │
│                    │ 5. Quality/Resilience │                                     │
│                    │ 6. Readiness Score    │                                     │
│                    └───────────┬───────────┘                                     │
│                                │                                                 │
│                                ▼                                                 │
│                    ┌───────────────────────┐                                     │
│                    │  Generate Report      │                                     │
│                    │  - Findings           │                                     │
│                    │  - Evidence           │                                     │
│                    │  - Recommendations    │                                     │
│                    └───────────┬───────────┘                                     │
│                                │                                                 │
│                                ▼                                                 │
│                    ┌───────────────────────┐                                     │
│                    │  Post to GitHub       │  ← Comment on issue                 │
│                    │  - Report             │  ← Create linked issues (if needed) │
│                    │  - Labels              │  ← Create PR (if approved)          │
│                    └───────────────────────┘                                     │
│                                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Instructions

### Step 1: Create Audit Issue

Create a GitHub issue with the following format:

```markdown
## OpenClaw Audit Request

**Target Repository:** owner/repo-name
**Lane:** {lane-name}
**Scope:** {specific files, modules, or "full repository"}
**Constraints:** {any limitations or special instructions}

### Example

**Target Repository:** berylm1/newfire
**Lane:** codebase-intelligence
**Scope:** newfire_backend_docker/
**Constraints:** Read-only mode only

@openhands please run a codebase intelligence audit on the backend.
```

**Labels to add:**
- `lane:codebase-intelligence` (or appropriate lane label)
- `audit-request`

### Step 2: Agent Preflight Check

Before running any audit, the agent performs:

```bash
# 1. Verify repository exists and is accessible
gh repo view owner/repo --json name,url,isArchived,visibility

# 2. Check if we have read access
gh api repos/owner/repo --silent || echo "READ ACCESS OK"

# 3. For write operations, verify permissions
gh api repos/owner/repo/collaborators --jq '.[] | select(.login == "openhands") | .permissions'

# 4. Check branch protection
gh api repos/owner/repo/branches/main/protection --jq '.required_status_checks, .enforce_admins'
```

### Step 3: Clone Repository (Read-Only)

```bash
# Clone with HTTPS using token
git clone https://x-access-token:${GITHUB_TOKEN}@github.com/owner/repo.git /tmp/audit-repo

# Verify clone
cd /tmp/audit-repo && git status

# Set to read-only mode
chmod -R a-w /tmp/audit-repo
```

### Step 4: Lane-Specific Analysis

#### Lane 1: Codebase Intelligence

```bash
# Enumerate services
find . -name "package.json" -o -name "requirements.txt" -o -name "go.mod" -o -name "Cargo.toml"

# Map endpoints
grep -r "app\.\|router\.\|@app\|FastAPI" --include="*.py" --include="*.js" | head -50

# Extract dependencies
cat package.json | jq '.dependencies, .devDependencies'

# Find test files
find . -name "*test*" -o -name "*spec*" | grep -E "\.(py|js|ts)$"
```

#### Lane 2: Gap/Quality Audit

```bash
# Find orphan/scaffolded code
find . -type d -name "template*" -o -name "example*" -o -name "demo*"
find . -name "*_stub*" -o -name "*_mock*" -o -name "*_todo*"

# Detect duplicate code patterns
# (Requires specialized tooling)

# Check for missing error handling
grep -rn "except:" --include="*.py" | grep -v "except Exception" | grep -v "except Error"

# Find TODOs and FIXMEs
grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.py" --include="*.js"
```

#### Lane 3: Security Scan

```bash
# Dependency audit
npm audit --audit-level=moderate 2>/dev/null || echo "No npm audit"
pip-audit 2>/dev/null || echo "No pip-audit"
govulncheck ./... 2>/dev/null || echo "No govulncheck"

# Secret detection
grep -rEn "(api[_-]?key|secret|token|password|credential)" --include="*.py" --include="*.js" | grep -v "example\|test\|dummy\|mock"

# Check for SQL injection vectors
grep -rn "execute\|query\|raw\|f\"" --include="*.py" | grep -v "cursor.execute\|db.execute"

# CORS configuration check
grep -rn "cors\|Access-Control-Allow" --include="*.py" --include="*.js"
```

#### Lane 4: Performance Analysis

```bash
# Find N+1 query patterns
grep -rn "for.*in.*query\|for.*in.*filter\|for.*in.*all()" --include="*.py"

# Check for missing indexes (comments)
grep -rn "index\|foreign key" --include="*.py" --include="*.sql"

# Memory patterns
grep -rn "load\|fetch\|get_all" --include="*.py" | head -20

# Async patterns
grep -rn "async def\|await\|asyncio" --include="*.py"
```

#### Lane 5: Quality/Resilience

```bash
# Test coverage check
find . -name "coverage.xml" -o -name ".coverage" | head -5
find . -path "*/site-packages/coverage/*" | head -5

# Integration test presence
find . -name "*integration*" -o -name "*e2e*" -o -name "*end-to-end*"

# Chaos testing setup (if any)
find . -name "*chaos*" -o -name "*fault*"
```

#### Lane 6: Readiness Scoring

```bash
# Documentation check
find . -name "README*" -o -name "ARCHITECTURE*" -o -name "DESIGN*"
wc -l README* || echo "No README"

# Monitoring setup
grep -rn "metrics\|monitoring\|prometheus\|datadog" --include="*.py" --include="*.js"

# Backup configuration
find . -name "*backup*" -o -name "*dump*" -o -name "*restore*"

# Health checks
grep -rn "/health\|healthcheck\|/ready" --include="*.py" --include="*.js"
```

### Step 5: Generate Report

Format findings according to the CEO Report Format:

```markdown
# [Lane] Audit Report: {Repository}

**Repository:** {owner/repo}
**Lane:** {lane-name}
**Date:** {ISO timestamp}
**Mode:** Read-Only

## Summary
{2-3 sentence executive summary}

## Findings

### Finding 1: {Title}
- **Severity:** {Critical|High|Medium|Low}
- **File:** {path/to/file:line}
- **Evidence:** ```{code snippet}```
- **Recommendation:** {specific action}

### Finding 2: ...


## Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| {metric} | {value} | {notes} |

## Next Actions
| Priority | Action | Issue |
|----------|--------|-------|
| 1 | {action} | (create issue) |
| 2 | ... | ... |

---
*Generated by OpenClaw GitHub Control Plane*
```

### Step 6: Post Results to GitHub

```bash
# Comment on the original issue with the report
gh issue comment {issue-number} --body "$(cat report.md)"

# If findings warrant new issues, create them:
gh issue create \
  --title "Finding: {title}" \
  --body "**Severity:** {severity}\n\n{evidence}\n\n**Recommendation:** {action}\n\n*Reported by OpenClaw audit of #{issue-number}*" \
  --label "auto-generated,from-audit" \
  --assignee berylm1

# Update original issue with completion status
gh issue edit {issue-number} \
  --add-label "audit-complete" \
  --remove-label "audit-request"
```

---

## Automation Integration

### GitHub Actions Workflow

Create `.github/workflows/openhands-audit.yml`:

```yaml
name: OpenClaw Audit Trigger

on:
  issue_comment:
    types: [created]

jobs:
  audit-trigger:
    if: contains(github.event.comment.body, '@openhands audit')
    runs-on: ubuntu-latest
    steps:
      - name: Parse audit request
        run: |
          echo "AUDIT_REQUESTED=true" >> $GITHUB_ENV
          # Parse issue body for repo and lane
```

### OpenHands Automation

Use OpenHands Cloud automation for scheduled audits:

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weekly Security Audit",
    "prompt": "Run a security audit on berylm1/newfire focusing on dependency vulnerabilities and secret exposure. Report findings as GitHub issues.",
    "trigger": {
      "type": "cron",
      "schedule": "0 2 * * 0",
      "timezone": "UTC"
    }
  }'
```

---

## Safety Checklist

Before running any audit:

- [ ] Verify target repository is GitHub-tracked
- [ ] Confirm read-only mode is appropriate
- [ ] Check for any explicit write mode approvals in issue
- [ ] Review scope for sensitive areas (secrets, credentials)
- [ ] Ensure no production systems will be affected
- [ ] Document any findings that require immediate action

---

## Appendix: Common Audit Commands

```bash
# Full repository stats
git ls-files | wc -l                    # Total files
find . -name "*.py" | wc -l             # Python files
find . -name "*.js" -o -name "*.ts" | wc -l  # JS/TS files

# Complexity metrics
find . -name "*.py" -exec wc -l {} + | tail -1  # Total Python LOC
find . -name "*.py" -exec wc -l {} + | sort -n | tail -10  # Largest files

# Test coverage (if available)
cat coverage/coverage.xml 2>/dev/null | grep -o 'line-rate="[0-9.]*"'

# Security
npm audit --json 2>/dev/null | jq '.metadata.vulnerabilityCount' || echo "0"
grep -r "password\|secret\|key" --include="*.py" --include="*.js" | grep -v "test\|mock\|example" | wc -l
```

---

## Related Documents

- [OPENCLAW_GITHUB_CONTROL_PLANE.md](./OPENCLAW_GITHUB_CONTROL_PLANE.md) - Full architecture
- [CEO Report Format](./OPENCLAW_GITHUB_CONTROL_PLANE.md#ceo-report-format) - Report template
- Issues: #10-#20 (pilot run targets)
