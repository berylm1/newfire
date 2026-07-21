# 2026-06-03 - Path From OpenHands Smoke Test to CEO Agent

Status: next-phase plan
Related: [[2026-06-03 - OpenHands Minisforum Setup Progress]], [[OpenHands CEO Update Routing Plan]]

## Goal

Turn the verified Minisforum OpenHands setup into the CEO-requested NewFire coding/review agent:

```text
CEO/Beryl approved task → GitHub issue/label → OpenHands on Minisforum → branch/PR/report → Beryl/CEO update → human merge decision
```

## Current confirmed baseline

- Pi can reach the NewFire tailnet.
- Pi can SSH to the Minisforum node `america` at `100.79.80.119` as `newwaveclaw`.
- OpenHands container `openhands-dgx` is running on the Minisforum.
- OpenHands UI is reachable at `http://100.79.80.119:3000/` over Tailscale.
- OpenHands CLI can start runtime containers and inspect a mounted repo copy.
- Real repo remained clean after testing.
- Required CLI/run fixes discovered:
  - `SANDBOX_USER_ID=1000`
  - `RUN_AS_OPENHANDS=true`
  - `WORKSPACE_BASE=<workspace>`
  - `WORKSPACE_MOUNT_PATH=<workspace>`
  - `SANDBOX_VOLUMES=<workspace>:/workspace:rw`

## Phase 1 — Stabilize manual agent run

Objective: one repeatable command that runs OpenHands safely.

Create a Minisforum wrapper script, likely:

```bash
~/newfire-agent/scripts/run-openhands-task.sh
```

The wrapper should:

1. Create a fresh disposable worktree/copy for each run.
2. Set the required OpenHands env overrides.
3. Cap iterations and log output.
4. Never run on `main` directly.
5. Start docs-only/read-only until trusted.
6. Save a run summary under `~/newfire-agent/reports/`.

Exit criteria:

- A one-line command can run OpenHands against a safe task.
- Logs are captured.
- Repo remains clean unless intentionally creating a branch.

## Phase 2 — Create GitHub control plane

Objective: GitHub becomes the task queue and audit trail.

Create labels:

- `agent-ready` — approved for OpenHands attempt.
- `ceo-priority` — include in CEO digest.
- `review-this` — review-only, no implementation.
- `needs-human` — blocked/needs clarification.

Create first issue:

```text
Title: Agent smoke test: summarize NewFire repo structure
Labels: agent-ready, ceo-priority
Scope: docs/read-only summary or docs-only update. No production changes.
```

Exit criteria:

- GitHub has labels and one safe test issue.
- Beryl/CEO can point to the issue as the authorized task.

## Phase 3 — Manual branch/PR lane

Objective: OpenHands can produce a branch/PR, not just a report.

Process:

1. Pull `main` on Minisforum.
2. Create branch like `agent/docs-smoke-test-<issue-number>`.
3. Run OpenHands with a small docs-only task.
4. Inspect diff.
5. Commit only if safe.
6. Push branch.
7. Open PR.
8. Human reviews before merge.

Exit criteria:

- One safe PR opened by/through the agent.
- PR includes summary, test/log path, and risk level.
- No auto-merge.

## Phase 4 — GitHub Actions/self-hosted runner trigger

Objective: remove manual SSH from the loop.

Preferred route:

- GitHub issue labeled `agent-ready` triggers workflow.
- Workflow runs only on Minisforum self-hosted runner.
- Workflow calls the wrapper script.
- Workflow uploads/report logs.
- Workflow creates or updates PR/comment.

Exit criteria:

- Labeling an issue starts an agent run.
- Run is auditable in GitHub Actions.
- Failure posts a clear issue comment/report.

## Phase 5 — CEO update lane

Objective: CEO gets business-readable progress without reading logs.

Hermes/Pi watches GitHub daily or after runs and sends Beryl:

```text
CEO Update — NewFire Agent

- Progress: Agent attempted/completed [business-readable task].
- Output: PR/report link.
- Quality gate: tests passed/failed/not run.
- Blocker: concise blocker if any.
- Next decision: review PR / clarify scope / approve next task.
```

Exit criteria:

- Beryl receives a concise digest.
- CEO direct delivery can be added later via Telegram group/channel.

## Phase 6 — Trust expansion

Only after successful manual runs:

1. Read-only review/report.
2. Docs-only PRs.
3. Low-risk frontend/docs fixes.
4. Small backend changes with tests.
5. Nightly review queue.
6. Never auto-merge production changes.

## Safety gates that stay permanent

- No direct pushes to `main`.
- No production deploys.
- No migrations.
- No service restarts.
- No secret edits.
- Human review before merge.
- GitHub issue/PR is the source of truth.
- OpenHands headless/CLI tasks must run through wrapper constraints.

## Immediate next command work

Next technical action is to create the Minisforum wrapper script and run one cleaner docs-only task with enough iterations for `finish`.
