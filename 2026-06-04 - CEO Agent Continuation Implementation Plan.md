# 2026-06-04 - CEO Agent Continuation Implementation Plan

> **For Hermes:** Use subagent-driven-development / careful human-reviewed implementation. Do not let any agent push to `main`, deploy, restart services, run migrations, or edit secrets.

**Goal:** Continue the CEO-requested NewFire nightly code-review / implementation agent from safe report-only mode into a controlled issue → agent run → reviewed branch/PR workflow.

**Architecture:** GitHub issues are the control plane. The Minisforum (`newwaveclaw@100.79.80.119`) is the production worker. Hermes on the Raspberry Pi coordinates, documents, schedules, and sends CEO-facing summaries. OpenHands may work only in disposable workspaces until a human reviews and promotes the diff.

**Tech Stack:** GitHub issues/labels, SSH, Minisforum Ubuntu worker, OpenHands container/wrapper, Python status/report scripts, Obsidian runbook, eventual PR workflow.

Related:

- [[2026-06-02 - Nightly GitHub Code Review Agent from Patrick]]
- [[2026-06-02 - Minisforum Nightly Code Agent Deployment Plan]]
- [[../Agent Operations Runbook|NewFire Agent Operations Runbook]]
- [[../CEO Agent Prior Art Source Map|CEO Agent Prior Art Source Map]]

---

## Current state confirmed

- Production worker host: `newwaveclaw@100.79.80.119`
- Real repo path on Minisforum: `/home/newwaveclaw/newfire-agent/workspace/repo`
- Real repo branch: `main`
- Real repo status: clean at latest quick check
- Nightly report-only agent exists and is scheduled from Minisforum
- Latest report symlinks exist:
  - `/home/newwaveclaw/newfire-agent/reports/latest-nightly-ceo-summary.md`
  - `/home/newwaveclaw/newfire-agent/reports/latest-nightly-precheck.md`
- Hermes status script exists on Pi:
  - `/home/beryl/.hermes/scripts/newfire_agent_status.py`
- Latest Hermes status showed:
  - Open GitHub issues: 6
  - Open PRs: 0
  - Agent-ready issues: 6
  - CEO-priority issues: 3
  - PRs needing review: none

## Current agent-ready queue

1. `#2` — Replace OpenClaw Stage B classifier stub with tested routing logic
   - Priority: highest / CEO-priority
   - Status: partial OpenHands disposable run exists; needs review/salvage before PR.
2. `#3` — Add tenant/RBAC integration tests for signup, company, agent access, and cross-tenant denial
   - Priority: high / CEO-priority
   - Status: next after #2 is cleaned.
3. `#4` — Create RAG/memory implementation plan from current NewFire gaps
   - Priority: medium-high / review-this
   - Status: docs/design first.
4. `#5` — Audit and retire demo/dev access references from production runbooks
   - Priority: medium / docs-security hygiene
   - Status: safe docs-only candidate.
5. `#6` — Add APISIX metering and rate-limit smoke tests
   - Priority: medium / tests-docs.

## Hard safety boundaries

Every continuation step must respect:

- No direct push to `main`.
- No production deploy.
- No service restart.
- No database migration.
- No secret edits.
- No `.env` commits.
- First implementation runs in disposable workspace only.
- Promote to branch/PR only after human/Hermes review of the diff.
- If blocked by credentials, production access, or unclear business logic, mark `needs-human`.

---

## Phase 1 — Resume from issue #2 safely

### Task 1: Inspect the partial OpenHands run for issue #2

**Objective:** Understand whether the existing disposable diff is useful or should be discarded.

**Files / paths:**

- Remote report: `/home/newwaveclaw/newfire-agent/reports/openhands-code-pr-20260604-025716.md`
- Remote disposable workspace: `/home/newwaveclaw/newfire-agent/workspace/openhands-runs/openhands-code-pr-20260604-025716`
- Real repo: `/home/newwaveclaw/newfire-agent/workspace/repo`

**Commands:**

```bash
ssh newwaveclaw@100.79.80.119 'tail -160 /home/newwaveclaw/newfire-agent/reports/openhands-code-pr-20260604-025716.md'
ssh newwaveclaw@100.79.80.119 'cd /home/newwaveclaw/newfire-agent/workspace/repo && git status --short'
ssh newwaveclaw@100.79.80.119 'cd /home/newwaveclaw/newfire-agent/workspace/openhands-runs/openhands-code-pr-20260604-025716 && git diff -- openclaw/app/classifier.py openclaw/README.md openclaw/tests/test_classifier.py | sed -n "1,260p"'
```

**Expected:**

- Real repo remains clean.
- Disposable diff only touches classifier, README, and tests.
- If diff is noisy, incomplete, or unsafe, do not promote it.

### Task 2: Decide salvage vs rerun

**Objective:** Choose one safe path for issue #2.

Decision options:

1. **Salvage manually** if the diff is small, correct, and testable.
2. **Rerun OpenHands with a tighter task prompt** if the diff is absent/noisy.
3. **Switch to Hermes/manual implementation** if OpenHands loops again.

Default recommendation:

- Inspect and salvage only the smallest useful parts.
- Do not trust the previous OpenHands run automatically because it hit max iterations / partial state.

### Task 3: Create a clean issue #2 branch only after review

**Objective:** Create a controlled branch in the real repo only when the intended diff is clear.

**Branch name:**

```bash
fix/issue-2-openclaw-classifier-routing
```

**Commands:**

```bash
ssh newwaveclaw@100.79.80.119 'cd /home/newwaveclaw/newfire-agent/workspace/repo && git checkout main && git pull --ff-only && git checkout -b fix/issue-2-openclaw-classifier-routing'
```

**Do not run this until Task 1 and Task 2 are complete.**

### Task 4: Implement the smallest issue #2 fix

**Objective:** Replace classifier stub behavior with tested routing logic without broad architecture changes.

Likely files:

- `openclaw/app/classifier.py`
- `openclaw/tests/test_classifier.py`
- `openclaw/README.md`

Expected change shape:

- define explicit routing categories / lanes;
- classify requests deterministically from existing fields/content;
- include fallback behavior;
- add tests proving common routes and fallback;
- update README to describe current non-stub behavior.

**Do not:**

- change production secrets;
- change deployment config;
- add new external service dependency;
- rewrite OpenClaw broadly.

### Task 5: Verify issue #2 branch locally on Minisforum

**Objective:** Prove the branch is safe enough to push for PR review.

Commands depend on project test setup, but start with:

```bash
ssh newwaveclaw@100.79.80.119 'cd /home/newwaveclaw/newfire-agent/workspace/repo && python3 -m py_compile openclaw/app/classifier.py'
ssh newwaveclaw@100.79.80.119 'cd /home/newwaveclaw/newfire-agent/workspace/repo && python3 -m pytest openclaw/tests/test_classifier.py -q'
```

If `pytest` is unavailable:

```bash
ssh newwaveclaw@100.79.80.119 'cd /home/newwaveclaw/newfire-agent/workspace/repo && python3 - <<"PY"
import importlib.util
spec = importlib.util.spec_from_file_location("classifier", "openclaw/app/classifier.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print("classifier import smoke ok")
PY'
```

Expected:

- syntax/import smoke passes;
- targeted tests pass if test runner is available;
- `git diff --stat` shows only intended files.

### Task 6: Push branch and open PR for Sagar/human review

**Objective:** Move reviewed, tested work into GitHub PR workflow.

Commands:

```bash
ssh newwaveclaw@100.79.80.119 'cd /home/newwaveclaw/newfire-agent/workspace/repo && git status --short && git diff --stat'
ssh newwaveclaw@100.79.80.119 'cd /home/newwaveclaw/newfire-agent/workspace/repo && git add openclaw/app/classifier.py openclaw/tests/test_classifier.py openclaw/README.md && git commit -m "fix(openclaw): replace classifier stub with tested routing logic"'
ssh newwaveclaw@100.79.80.119 'cd /home/newwaveclaw/newfire-agent/workspace/repo && git push -u origin HEAD'
```

PR title:

```text
fix(openclaw): replace classifier stub with tested routing logic
```

PR body must include:

- issue link: `Fixes #2` or `Refs #2` depending on whether fully complete;
- summary;
- files changed;
- tests run;
- safety statement: no deploy/restart/migration/secret edit;
- note that Sagar/human review is required before merge.

---

## Phase 2 — Issue #3 after #2 is stable

### Task 7: Inspect auth/tenant/RBAC code paths

**Objective:** Locate the smallest integration-test target for signup, company creation, agent access, and cross-tenant denial.

Search targets:

```bash
ssh newwaveclaw@100.79.80.119 'cd /home/newwaveclaw/newfire-agent/workspace/repo && find . -path "*/.git" -prune -o -type f \( -name "*.py" -o -name "*.ts" -o -name "*.js" \) | grep -Ei "auth|tenant|company|rbac|jwt|agent" | head -120'
```

Expected output:

- identify test folder;
- identify auth/JWT/company/agent access implementation;
- identify whether integration tests need mocked DB or Docker services.

### Task 8: Create issue #3 branch and tests only

Branch:

```bash
fix/issue-3-tenant-rbac-tests
```

Goal:

- add tests before implementation changes;
- prefer mocks/local fixtures first;
- no production DB migration;
- no live service mutation.

---

## Phase 3 — Documentation/design tasks

These can run in parallel after issue #2 path is clear.

### Issue #4 — RAG/memory implementation plan

Good first docs-only PR.

Output:

- architecture note under repo docs;
- ordered implementation steps;
- source-of-truth data flow;
- storage choice discussion;
- risks and test plan.

### Issue #5 — Retire demo/dev access references

Good docs/security hygiene PR.

Rules:

- Do not delete historical progress logs blindly.
- Separate historical docs from current production runbooks.
- Redact or reframe active runbook references if they imply demo credentials/access.

### Issue #6 — APISIX metering smoke tests

Tests/docs first.

Rules:

- no live gateway mutation;
- use local/mocked config validation if possible;
- document what a real integration test would need.

---

## Phase 4 — CEO-facing delivery

### Daily 8 AM digest from Hermes

Existing script:

```bash
/home/beryl/.hermes/scripts/newfire_agent_status.py
```

CEO digest should be 3–5 bullets:

- what ran;
- top finding;
- agent queue status;
- PRs needing review;
- next safe action.

### Patrick 4 AM delivery

Still needs final delivery channel/email confirmation.

Until confirmed:

- deliver to Beryl/Hermes chat;
- save reports in Obsidian and Minisforum report folder;
- do not claim Patrick email is configured.

---

## Implementation start checklist

Before coding again:

- [ ] Confirm we are continuing issue #2 first.
- [ ] Inspect the partial OpenHands diff.
- [ ] Verify real repo remains clean.
- [ ] Decide salvage vs rerun vs manual fix.
- [ ] Only then create a clean branch.
- [ ] Run targeted checks.
- [ ] Push branch and create PR for human review.
- [ ] Update GitHub issue and Obsidian runbook.

## Immediate next action

Start with **Phase 1 / Task 1**: inspect the partial issue #2 run and determine whether it is salvageable.
