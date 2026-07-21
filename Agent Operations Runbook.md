# NewFire Agent Operations Runbook

Purpose: repeatable steps for using GitHub issues as the NewFire agent control plane and running OpenHands safely from the Minisforum worker.

## Architecture

- GitHub repo: `https://github.com/berylm1/newfire`
- Control plane: GitHub issues + labels
- Worker host: Minisforum via SSH `newwaveclaw@100.79.80.119`
- Coding agent: OpenHands in container `openhands-dgx`
- Coordinator/documentation: Hermes on Raspberry Pi
- Reports: `/home/newwaveclaw/newfire-agent/reports/`
- Logs: `/home/newwaveclaw/newfire-agent/logs/`
- Disposable workspaces: `/home/newwaveclaw/newfire-agent/workspace/openhands-runs/`
- Real repo: `/home/newwaveclaw/newfire-agent/workspace/repo`

## Safety rules

Every agent task must follow these rules:

- No direct pushes to `main`.
- No production deploys.
- No service restarts.
- No database migrations.
- No secret edits.
- Use branch/PR only after human review.
- Run first in a disposable workspace.
- If the task needs credentials, production access, or an unclear business decision, stop and use/comment `needs-human`.

## GitHub labels

Required labels:

- `agent-ready` — approved for autonomous agent work.
- `ceo-priority` — high-priority business/CEO task.
- `review-this` — safe review/docs/design task.
- `needs-human` — blocked until a human decision.

## One-time token setup

Token source should be `/home/beryl/.hermes/.env`:

```bash
GITHUB_TOKEN=[REDACTED]
```

Permissions:

```bash
chmod 600 /home/beryl/.hermes/.env
```

Do not keep GitHub tokens in Obsidian. If a token is temporarily captured in the vault, move it into `.env`, then replace the Obsidian copy with `[REDACTED]`.

## Creating agent-ready issues from nightly findings

Script:

```bash
/home/beryl/.hermes/scripts/newfire_create_agent_issues.py
```

Run:

```bash
/home/beryl/.hermes/scripts/newfire_create_agent_issues.py
```

Current generated issues:

- #2 Replace OpenClaw Stage B classifier stub with tested routing logic — https://github.com/berylm1/newfire/issues/2
- #3 Add tenant/RBAC integration tests for signup, company, agent access, and cross-tenant denial — https://github.com/berylm1/newfire/issues/3
- #4 Create RAG/memory implementation plan from current NewFire gaps — https://github.com/berylm1/newfire/issues/4
- #5 Audit and retire demo/dev access references from production runbooks — https://github.com/berylm1/newfire/issues/5
- #6 Add APISIX metering and rate-limit smoke tests — https://github.com/berylm1/newfire/issues/6

The script is idempotent by exact open issue title and skips duplicates.

## Running OpenHands on an issue

### 1. Pull issue text into a task file

Example for issue #2:

```bash
python3 - <<'PY'
import json, urllib.request
issue_no = 2
url = f'https://api.github.com/repos/berylm1/newfire/issues/{issue_no}'
with urllib.request.urlopen(url, timeout=30) as r:
    issue = json.load(r)
body = f"GitHub issue #{issue['number']}: {issue['title']}\nURL: {issue['html_url']}\n\n{issue.get('body') or ''}\n\nAdditional instruction: implement the smallest safe change that satisfies acceptance criteria. Do not loop waiting for user input; if blocked, write a clear blocker summary and finish."
open(f'/tmp/newfire-issue-{issue_no}-openhands-task.txt','w').write(body)
PY
scp /tmp/newfire-issue-2-openhands-task.txt newwaveclaw@100.79.80.119:/tmp/newfire-issue-2-openhands-task.txt
```

### 2. Confirm real repo is clean

```bash
ssh newwaveclaw@100.79.80.119 'cd ~/newfire-agent/workspace/repo && git branch --show-current && git status --short'
```

Expected:

```text
main
```

No status output means clean.

### 3. Run wrapper in safe mode

Read-only smoke:

```bash
ssh newwaveclaw@100.79.80.119 'OPENHANDS_MAX_ITERATIONS=18 ~/newfire-agent/scripts/run-openhands-task.sh --task-file /tmp/newfire-issue-2-openhands-task.txt --mode readonly --max-iterations 18'
```

Code task in disposable workspace:

```bash
ssh newwaveclaw@100.79.80.119 'OPENHANDS_MAX_ITERATIONS=30 ~/newfire-agent/scripts/run-openhands-task.sh --task-file /tmp/newfire-issue-2-openhands-task.txt --mode code-pr --max-iterations 30'
```

Important: `code-pr` mode currently means code edits are allowed only in the disposable workspace. It does not push or open a PR automatically.

## Verifying a run

The wrapper prints:

```text
RUN_ID=...
STATUS=...
WORKSPACE=...
LOG=...
REPORT=...
REAL_REPO_STATUS=clean
```

Check report:

```bash
ssh newwaveclaw@100.79.80.119 'tail -120 /home/newwaveclaw/newfire-agent/reports/<RUN_ID>.md'
```

Check real repo stayed clean:

```bash
ssh newwaveclaw@100.79.80.119 'cd ~/newfire-agent/workspace/repo && git status --short'
```

Compare disposable workspace to real repo:

```bash
ssh newwaveclaw@100.79.80.119 'cd ~/newfire-agent/workspace/openhands-runs/<RUN_ID> && diff -qr ~/newfire-agent/workspace/repo . | head -80'
```

If the agent gets stuck or hits max iterations, do not promote the result directly. Review/salvage the disposable diff first.

## Posting run status back to GitHub

Use the GitHub API from Hermes/Pi with `GITHUB_TOKEN` loaded from `/home/beryl/.hermes/.env`.

Status comment template:

```text
OpenHands issue #N run started from the Minisforum worker.

Result: <completed/partial/incomplete>.

Artifacts:
- Report: `<report path>`
- Log: `<log path>`
- Workspace: `<workspace path>`

Safety verification:
- Real repo remained clean.
- No direct push to main.
- No deploys, restarts, migrations, or secret edits.

Next step: <review/salvage/promote/create PR>.
```

## Issue #2 actual run record

Two runs were made:

- `openhands-code-pr-20260604-025217`
  - Report: `/home/newwaveclaw/newfire-agent/reports/openhands-code-pr-20260604-025217.md`
  - Result: got stuck in repeated test-file search loop; no changes.
- `openhands-code-pr-20260604-025716`
  - Report: `/home/newwaveclaw/newfire-agent/reports/openhands-code-pr-20260604-025716.md`
  - Result: partial disposable-workspace changes to:
    - `openclaw/app/classifier.py`
    - `openclaw/README.md`
    - `openclaw/tests/test_classifier.py`
  - Agent hit max iterations before finishing.

Safety result:

- Real repo remained clean.
- No push to `main`.
- No deploy/restart/migration/secret edit.

GitHub issue comment:

- https://github.com/berylm1/newfire/issues/2#issuecomment-4618593067

## Salvage workflow after partial agent output

1. Inspect the disposable diff.
2. Run syntax/tests where possible.
3. Decide whether to:
   - discard and rerun with a tighter prompt,
   - manually clean the diff into a branch,
   - or use a different agent/tool for the PR.
4. Only create a PR after the diff is clean and scoped.
5. Comment final status on the GitHub issue.
6. Update this runbook if a new pitfall or better command is discovered.

## Known pitfalls

- OpenHands can ask for user input even when instructed not to. The wrapper auto-continues, but this burns iterations.
- OpenHands can get stuck in repeated shell/search loops.
- A wrapper `STATUS=0` can still contain `AgentStuckInLoopError` or max-iteration errors; always inspect the report/log.
- `pytest` may be unavailable in the disposable environment. Use Python syntax/import smoke checks if needed.
- Do not treat disposable workspace changes as production-ready PRs without review.

## Nightly review agent

Nightly report-only agent:

```bash
/home/newwaveclaw/newfire-agent/scripts/nightly-agent.sh
```

Cron on Minisforum:

```text
15 3 * * * /home/newwaveclaw/newfire-agent/scripts/nightly-agent.sh >> /home/newwaveclaw/newfire-agent/logs/nightly-agent-cron.log 2>&1
```

Latest symlinks:

```bash
/home/newwaveclaw/newfire-agent/reports/latest-nightly-ceo-summary.md
/home/newwaveclaw/newfire-agent/reports/latest-nightly-precheck.md
```

Hermes 8 AM digest script:

```bash
/home/beryl/.hermes/scripts/newfire_agent_status.py
```

## Current next step

Review and clean/salvage issue #2 disposable diff before creating a branch/PR. After issue #2 is clean, move to issue #3 for tenant/RBAC integration tests.

---

## GitHub Webhook → Minisforum Listener (Issue #22: OpenClaw GitHub-wide Agent)

### Architecture

```
GitHub (berylm1/newfire)
    │
    ├─ Issues labeled `agent-ready` or `ceo-priority`
    │   └─ Webhook (issues, issue_comment events)
    │       │
    │       ▼
    │   Minisforum: `newfire_webhook_listener.py` (port 8080)
    │       │
    │       ├─ Validates HMAC signature (WEBHOOK_SECRET)
    │       ├─ Filters by trigger labels, ignores `needs-human`
    │       ├─ Accepts manual `/run-agent` comments
    │       │
    │       ▼
    │   Spawns background thread → `run-openhands-task.sh`
    │       │
    │       ├─ Creates task file from issue body
    │       ├─ Verifies real repo is clean
    │       ├─ Runs OpenHands in disposable workspace
    │       ├─ Logs to `/home/newwaveclaw/newfire-agent/logs/`
    │       ├─ Reports to `/home/newwaveclaw/newfire-agent/reports/`
    │       │
    │       ▼
    │   Posts result back to GitHub issue (via API)
    │
    └─ Hermes/Pi: 8 AM digest fetches latest reports via SSH
```

### Listener Script

**Location (Pi/Hermes):** `/home/beryl/.hermes/scripts/newfire_webhook_listener.py`  
**Deploy to Minisforum:** `/home/newwaveclaw/newfire-agent/scripts/newfire_webhook_listener.py`

### Systemd Service

**File:** `/home/beryl/.hermes/scripts/newfire-webhook-listener.service`  
**Install on Minisforum:**
```bash
sudo cp newfire-webhook-listener.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now newfire-webhook-listener
```

### Environment Variables (Minisforum `/home/newwaveclaw/.env`)

```bash
WEBHOOK_SECRET=<github-webhook-secret>  # From GitHub webhook settings
WEBHOOK_PORT=8080
GITHUB_TOKEN=<token-with-repo-scope>    # For posting results back to issues
```

### GitHub Webhook Configuration

**In repo settings → Webhooks → Add webhook:**
- **Payload URL:** `http://<minisforum-tailscale-ip>:8080/github-webhook` (e.g., `http://100.79.80.119:8080/github-webhook`)
- **Content type:** `application/json`
- **Secret:** Same as `WEBHOOK_SECRET` above
- **Events:** 
  - ✅ Issues
  - ✅ Issue comments
  - (Optional) Pull requests — for future PR review automation
- **Active:** ✅

### Trigger Logic

| Event | Condition | Action |
|-------|-----------|--------|
| `issues.opened` | Has `agent-ready` or `ceo-priority` label, no `needs-human` | Auto-trigger OpenHands |
| `issues.reopened` | Same labels | Auto-trigger OpenHands |
| `issues.labeled` | Label added is `agent-ready` or `ceo-priority` | Auto-trigger OpenHands |
| `issue_comment.created` | Comment starts with `/run-agent`, `/retry`, `/run agent` | Manual trigger OpenHands |

### Safety Guards in Listener

- **Signature verification** — HMAC-SHA256 with `WEBHOOK_SECRET`
- **Label gating** — Only `agent-ready`/`ceo-priority` triggers; `needs-human` blocks
- **Clean repo check** — Aborts if real repo has uncommitted changes
- **Disposable workspace** — All OpenHands edits isolated, never touch real repo directly
- **Iteration limit** — `OPENHANDS_MAX_ITERATIONS=30` prevents runaway
- **Timeout** — 30-minute hard timeout per run
- **Human merge gate** — Listener only runs OpenHands; PR creation is manual/review step

### Deployment Steps (when Minisforum is online)

1. **Copy scripts to Minisforum:**
   ```bash
   scp /home/beryl/.hermes/scripts/newfire_webhook_listener.py newwaveclaw@100.79.80.119:/home/newwaveclaw/newfire-agent/scripts/
   scp /home/beryl/.hermes/scripts/newfire-webhook-listener.service newwaveclaw@100.79.80.119:/tmp/
   ```

2. **On Minisforum, set up Python venv and install deps:**
   ```bash
   cd ~/newfire-agent
   python3 -m venv venv
   source venv/bin/activate
   pip install flask  # or use stdlib http.server (no extra deps)
   ```

3. **Configure environment:**
   ```bash
   cat > ~/.env <<'EOF'
   WEBHOOK_SECRET=<generate-with-openssl-rand-hex-32>
   WEBHOOK_PORT=8080
   GITHUB_TOKEN=<your-github-token>
   EOF
   chmod 600 ~/.env
   ```

4. **Install and start systemd service:**
   ```bash
   sudo cp /tmp/newfire-webhook-listener.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now newfire-webhook-listener
   sudo systemctl status newfire-webhook-listener
   ```

5. **Configure GitHub webhook** (repo settings → Webhooks → Add webhook) with Payload URL `http://100.79.80.119:8080/github-webhook`

6. **Test:** Add `agent-ready` label to an existing issue (e.g., #2) → should trigger OpenHands run

### Monitoring

- **Service logs:** `journalctl -u newfire-webhook-listener -f`
- **Run reports:** `/home/newwaveclaw/newfire-agent/reports/openhands-webhook-*.md`
- **Run logs:** `/home/newwaveclaw/newfire-agent/logs/openhands-webhook-*.log`
- **Hermes 8 AM digest** already fetches latest nightly + webhook runs via SSH

### Next Steps for #22

- [ ] Deploy listener when Minisforum comes online
- [ ] Generate `WEBHOOK_SECRET` and configure GitHub webhook
- [ ] Test with issue #2 (OpenClaw classifier) — add `agent-ready` label
- [ ] Verify OpenHands run completes, posts result to issue
- [ ] Add PR creation step (manual or automated with `needs-human` gate)
- [ ] Document first end-to-end run in Obsidian
