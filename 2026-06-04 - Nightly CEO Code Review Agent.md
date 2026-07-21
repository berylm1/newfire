# 2026-06-04 - Nightly CEO Code Review Agent

## CEO directive captured
Mr Patrick asked for an agent that checks code out of GitHub every night, analyzes it for:

- Technical debt and bugs.
- Performance issues.
- Whether business roles/permissions are fully implemented.
- Orphan, partial, generic scaffolded, disconnected, CRUD-only, or incomplete platform features.
- What must be fully implemented end-to-end.
- A morning update.

## Implementation completed

The Minisforum production worker now has a safe nightly report-only code-review runner:

```bash
/home/newwaveclaw/newfire-agent/scripts/nightly-agent.sh
```

It runs against:

```bash
/home/newwaveclaw/newfire-agent/workspace/repo
https://github.com/berylm1/newfire
```

Current report symlinks:

```bash
/home/newwaveclaw/newfire-agent/reports/latest-nightly-ceo-summary.md
/home/newwaveclaw/newfire-agent/reports/latest-nightly-precheck.md
```

Manual verified run:

```text
STATUS=0
SUMMARY=/home/newwaveclaw/newfire-agent/reports/nightly-ceo-summary-20260604-021950.md
PRECHECK_REPORT=/home/newwaveclaw/newfire-agent/reports/nightly-precheck-20260604-021950.md
LOG=/home/newwaveclaw/newfire-agent/logs/nightly-agent-20260604-021950.log
```

## Schedule

Installed in the `newwaveclaw` crontab on the Minisforum:

```cron
15 3 * * * /home/newwaveclaw/newfire-agent/scripts/nightly-agent.sh >> /home/newwaveclaw/newfire-agent/logs/nightly-agent-cron.log 2>&1
```

The existing 2:00 AM database backup remains untouched:

```cron
0 2 * * * /home/newwaveclaw/scripts/backup-db.sh >> /home/newwaveclaw/backups/cron.log 2>&1
```

Hermes/Pi morning digest integration was also updated so the 8:00 AM Telegram status script reads the latest Minisforum summary over SSH before adding GitHub issue/PR queue status.

Local Hermes script:

```bash
/home/beryl/.hermes/scripts/newfire_agent_status.py
```

## Safety posture

The nightly review runner is intentionally report-only:

- No file edits.
- No direct pushes to `main`.
- No merges.
- No deploys.
- No service restarts.
- No migrations.
- No secrets touched.
- Human review remains required before implementation PRs merge.

## First verified findings

The first successful run found the CEO's target areas:

1. OpenClaw routing still has Stage B classifier stub/scaffold markers.
2. Tenant/RBAC/business role behavior needs end-to-end tests.
3. MCP/SDK/RAG/memory/webhook/ROI-dashboard surfaces remain incomplete or disconnected in the repo docs/backlog.
4. Demo/dev access references still appear in platform docs and should be separated from production runbooks.
5. APISIX metering/resource controls are documented but not yet proven by automated smoke tests.

## Agent-ready backlog suggested by the run

1. Replace OpenClaw Stage B classifier stub with tested routing logic.
2. Add tenant/RBAC integration tests for signup, company, agent access, and cross-tenant denial.
3. Create RAG/memory implementation plan from current NewFire gaps.
4. Audit and retire demo/dev access references from production runbooks.
5. Add APISIX metering and rate-limit smoke tests.

## Notes

An earlier OpenHands-based full nightly review attempt produced a very large log and got stuck in an interactive/awaiting-user loop. I replaced the nightly default with a deterministic, bounded report-only scan so the CEO gets a reliable morning update. OpenHands should still be used for one approved issue at a time after a human labels work `agent-ready`.
