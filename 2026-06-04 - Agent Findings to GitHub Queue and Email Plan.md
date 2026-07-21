# Agent Findings to GitHub Queue and Email Plan

Date: 2026-06-04

## Goal
Turn the nightly NewFire agent's top findings into a GitHub-controlled agent queue, then think through how backend email delivery to `pmunis@gmail.com` should work.

## Current state
- Latest nightly report source: `/home/newwaveclaw/newfire-agent/reports/latest-nightly-ceo-summary.md`
- Repo: `https://github.com/berylm1/newfire`
- Existing public issue verified:
  - #1 `Agent smoke test: summarize NewFire repo structure`
  - Labels: `agent-ready`, `ceo-priority`
- GitHub write auth status:
  - Pi/Hermes now has `GITHUB_TOKEN` saved in `/home/beryl/.hermes/.env` with file mode `600`.
  - The plaintext token note in Obsidian was replaced with `[REDACTED]` so the vault does not preserve secrets.
  - Minisforum still has no GitHub token source detected; `gh` CLI is not installed there.
- Result: issue creation completed from Pi/Hermes via GitHub API.

## Prepared GitHub issue creator
Script created:

```bash
/home/beryl/.hermes/scripts/newfire_create_agent_issues.py
```

Run after adding a GitHub token:

```bash
GITHUB_TOKEN='[REDACTED]' /home/beryl/.hermes/scripts/newfire_create_agent_issues.py
```

Or add to `/home/beryl/.hermes/.env`:

```bash
GITHUB_TOKEN=[REDACTED]
```

Then run:

```bash
/home/beryl/.hermes/scripts/newfire_create_agent_issues.py
```

The script is idempotent by exact open issue title and will skip duplicates.

## Agent-ready issues prepared

### #2. Replace OpenClaw Stage B classifier stub with tested routing logic
- URL: https://github.com/berylm1/newfire/issues/2
- Labels: `agent-ready`, `ceo-priority`
- Scope: `openclaw` classifier/routing logic, tests, docs.
- Why first: highest-impact CEO finding; directly addresses scaffold/stub logic.
- Safety: branch/PR only; no main push; no deploy; no secrets.

### #3. Add tenant/RBAC integration tests for signup, company, agent access, and cross-tenant denial
- URL: https://github.com/berylm1/newfire/issues/3
- Labels: `agent-ready`, `ceo-priority`
- Scope: local/test-only integration tests and fixtures.
- Why second: tenant isolation is core business logic and must be proven end-to-end.
- Safety: no production DB, no live migrations, no deploy.

### #4. Create RAG/memory implementation plan from current NewFire gaps
- URL: https://github.com/berylm1/newfire/issues/4
- Labels: `agent-ready`, `review-this`
- Scope: docs/design first, then break into follow-up implementation issues.
- Why: customer value is high, but implementation should be planned before code churn.

### #5. Audit and retire demo/dev access references from production runbooks
- URL: https://github.com/berylm1/newfire/issues/5
- Labels: `agent-ready`, `review-this`
- Scope: docs/security hygiene.
- Why: reduces launch-readiness and security-review noise.

### #6. Add APISIX metering and rate-limit smoke tests
- URL: https://github.com/berylm1/newfire/issues/6
- Labels: `agent-ready`, `review-this`
- Scope: local/mocked tests or documented safe smoke checks.
- Why: per-client usage control affects cost, SLA, and scale.

## Recommended first OpenHands target
Once issues are created, run OpenHands on issue 1 of the new backlog:

```text
Replace OpenClaw Stage B classifier stub with tested routing logic
```

This is the strongest first code task because it is high-value, contained, testable, and tied directly to the CEO finding.

## Email backend plan for pmunis@gmail.com

### Current machine state
- `himalaya` is not installed/configured.
- No `~/.config/himalaya/config.toml` was found.
- No `msmtp`, `sendmail`, `mail`, `mailx`, or `mutt` sender path was available.
- Conclusion: Hermes cannot send email from this Pi yet without configuring a sender backend.

### Backend options

#### Option A — Gmail app-password SMTP via Himalaya or msmtp
Best quick path if Beryl has a Gmail/Google Workspace sender account.

Needs:
- Sender address.
- Google App Password, not the normal Google password.
- SMTP config stored locally with secret redacted from notes.

Pros:
- Simple.
- Works from cron/scripts.
- Easy to send reports to `pmunis@gmail.com`.

Cons:
- Requires app-password setup and safe credential storage.

#### Option B — Microsoft/Outlook SMTP or Microsoft Graph
Good if NewFire uses Microsoft 365.

Pros:
- Business-friendly sender identity.
- Graph API is more robust long-term.

Cons:
- SMTP AUTH may be disabled by tenant policy.
- Graph OAuth setup is more involved.

#### Option C — Transactional email API: Resend, SendGrid, Postmark, AWS SES
Best production backend for automatic agent/CEO reports.

Pros:
- Purpose-built for backend sending.
- Good logs, deliverability, templates.
- Easy for Hermes cron/newfire agent to call via API.

Cons:
- Requires account/domain verification and API key.

### Recommended backend path
For NewFire backend/reporting, use a transactional email API eventually. For tonight/early testing, use Gmail app-password SMTP or keep sending via Telegram until a sender account is ready.

### Draft message to pmunis@gmail.com
Subject: NewFire AI agent control plane is live

```text
Hi Patrick,

Quick NewFire update: we now have a controlled AI agent workflow running against the GitHub repo.

- GitHub is being used as the task control plane with labels like agent-ready, ceo-priority, review-this, and needs-human.
- The first OpenHands smoke test completed safely in read-only mode: no deploys, restarts, migrations, secrets, pushes, or main-branch changes.
- A nightly review agent is now running on the Minisforum worker and generating CEO-style findings.
- The top findings are being converted into agent-ready GitHub issues so each task can be handled one at a time by the coding agent behind human PR review.

Next target: replace the OpenClaw Stage B classifier stub with tested routing logic, then add tenant/RBAC integration tests.

Best,
Beryl
```

## Next action needed
Provide or configure one of these before issue/email automation can execute fully:

1. GitHub token with Issues write access for `berylm1/newfire`.
2. Sender backend for email delivery, preferably:
   - Gmail app-password SMTP for quick setup, or
   - Resend/Postmark/SendGrid for production-style backend email.
