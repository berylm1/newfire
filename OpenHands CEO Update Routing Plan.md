# OpenHands CEO Update Routing Plan

Created: 2026-06-03
Status: planning note

## Known setup

- NewFire implementation worker: Minisforum.
- Coding agent already installed: OpenHands.
- Model backend: Qwen3-Coder served by vLLM on DGX Spark.
- Hermes/Pi role: coordination, documentation, scheduling, and Telegram updates; not the production code worker.

## Goal

Route OpenHands so it behaves like the CEO-requested agent:

1. It receives bounded engineering tasks from GitHub issues, labels, PR comments, or a nightly backlog scan.
2. It runs on the Minisforum against the NewFire repo, using the DGX Spark Qwen3-Coder vLLM endpoint.
3. It creates durable GitHub artifacts: branch, PR, comments, CI/test logs.
4. It sends concise status updates to Beryl and the CEO.
5. It never merges without human approval.

## Source findings

### OpenHands GitHub Action / Resolver pattern

Docs: https://docs.openhands.dev/openhands/usage/run-openhands/github-action.md

OpenHands supports a GitHub issue/PR workflow where:

- Add a `fix-me` label to an issue or PR to request a full attempt.
- Comment with `@openhands-agent` to request a focused response to that specific comment.
- It opens or updates a PR and can be iterated on through PR comments.
- Useful variables include:
  - `LLM_MODEL`
  - `OPENHANDS_MAX_ITER`
  - `OPENHANDS_MACRO`
  - `OPENHANDS_BASE_CONTAINER_IMAGE`
  - `TARGET_BRANCH`
  - `TARGET_RUNNER`

For NewFire, `TARGET_RUNNER` should point to a self-hosted GitHub Actions runner on the Minisforum if we use GitHub Actions as the trigger layer.

### OpenHands headless mode

Docs: https://docs.openhands.dev/openhands/usage/cli/headless.md

OpenHands can run without the UI:

```bash
openhands --headless -t "Your task here"
openhands --headless --json -t "Your task here" > output.jsonl
```

The `--json` mode streams structured JSONL events, which is ideal for converting agent activity into summaries for Beryl/CEO.

Important safety note: headless mode always runs in always-approve mode, so it should only run inside a constrained repo checkout/container with limited secrets and protected-branch rules.

### OpenHands event automations

Docs: https://docs.openhands.dev/openhands/usage/automations/event-automations.md

OpenHands has event automation concepts for GitHub events/custom webhooks, such as:

- PR labeled with a specific label.
- Issue comment mentioning OpenHands.
- Auto-review when a PR gets a label.
- Triage or response workflows from GitHub events.

This supports the desired CEO-agent shape: event-driven work plus scheduled digest.

### OpenHands SDK GitHub workflows

PR review docs: https://docs.openhands.dev/sdk/guides/github-workflows/pr-review.md
TODO management docs: https://docs.openhands.dev/sdk/guides/github-workflows/todo-management.md

Useful patterns:

- PR review can trigger from a `review-this` label or by requesting `openhands-agent` as reviewer.
- TODO management workflow shows `LLM_MODEL`, `LLM_BASE_URL`, and `LLM_API_KEY` env vars, creates a branch, commits, pushes, opens a PR, and writes a GitHub workflow summary.

This is close to the NewFire loop we want, except our tasks should come from CEO/Beryl-approved issues instead of arbitrary TODO comments.

## Recommended routing architecture

### Lane 1 — GitHub task intake

Use GitHub as the source of truth for work:

- Label: `agent-ready` — OpenHands may attempt implementation.
- Label: `ceo-priority` — include in CEO digest.
- Label: `needs-human` — do not run automatically; ask Beryl/CEO.
- Label: `review-this` — run OpenHands/PR-Agent review only.

### Lane 2 — OpenHands execution on Minisforum

Two possible routes:

#### Option A: GitHub Actions self-hosted runner

- Install a GitHub self-hosted runner on the Minisforum.
- Add it to the NewFire repo/org.
- Configure OpenHands workflow with `TARGET_RUNNER` set to that runner label.
- Store model config as repo/org secrets:
  - `LLM_MODEL`: Qwen3-Coder model name expected by vLLM/OpenHands/LiteLLM.
  - `LLM_BASE_URL`: DGX Spark vLLM OpenAI-compatible endpoint.
  - `LLM_API_KEY`: placeholder or actual API key depending on vLLM auth.
- Trigger from issue labels/comments.

Pros: GitHub-native audit trail, easy CEO visibility, good artifact history.
Cons: runner/secrets need careful hardening.

#### Option B: Hermes cron/webhook wrapper around OpenHands headless

- Hermes monitors GitHub issues/PRs on a schedule or via webhook.
- Hermes SSHes/executes on Minisforum or triggers a local script there.
- The script runs `openhands --headless --json` with a task prompt.
- Script captures JSONL/logs, branch, PR URL, test result.
- Hermes summarizes and sends Telegram/CEO update.

Pros: more control over summaries and routing.
Cons: more custom glue code than GitHub Actions.

## Best first implementation route

Use **Option A for the production work loop** and **Hermes for digest/routing**:

1. GitHub issue gets `agent-ready`.
2. GitHub Action runs on Minisforum self-hosted runner.
3. OpenHands uses DGX Spark Qwen3-Coder endpoint via `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY`.
4. OpenHands creates PR.
5. PR review lane runs on `review-this` or every OpenHands-created PR.
6. Hermes cron sends CEO/Beryl digest from GitHub state every morning/evening.

This avoids making Telegram the control plane for code changes. Telegram should be for summaries and approvals; GitHub should remain the production record.

## CEO/Beryl update format

Send a concise update like:

```text
NewFire Agent Update — 2026-06-03

- Worked on: #123 — short issue title
- Result: PR #456 opened / no-code-change / blocked
- Tests: passed / failed / not run, with one-line reason
- Risk: low / medium / high
- Decision needed: review PR, clarify scope, or approve next task
```

For CEO-facing versions, keep it higher level:

```text
CEO Update — NewFire Agent

- Progress: Agent completed/attempted [business-readable task].
- Output: PR opened and ready for review.
- Quality gate: tests passed/failed.
- Blocker: one concise blocker if any.
- Next decision: approve review, clarify requirement, or prioritize next item.
```

## Immediate next tasks

1. Confirm the Minisforum OpenHands command/env variables that successfully talk to DGX Spark vLLM.
2. Confirm whether NewFire GitHub repo already has a self-hosted runner from the Minisforum.
3. Add label taxonomy to the repo: `agent-ready`, `ceo-priority`, `needs-human`, `review-this`.
4. Add a workflow that routes `agent-ready` issues/PRs to OpenHands on the Minisforum runner.
5. Add a Hermes scheduled digest that reads GitHub issues/PRs and sends Telegram summaries.
6. Add the CEO as a delivery target or create a shared Telegram group/channel for agent updates.

## Current delivery limitation

Hermes currently sees only one Telegram target: Beryl Malomo DM. To update the CEO directly, Beryl needs to add Hermes to a shared Telegram group/channel or provide another connected delivery path. Until then, Hermes can draft CEO updates and send them to Beryl only.

## 2026-06-03 startup actions completed

- Created a local Hermes status script: `/home/beryl/.hermes/scripts/newfire_agent_status.py`.
- Scheduled a daily NewFire OpenHands/CEO-agent status digest at **8:00 AM Eastern** back to Beryl's Telegram chat.
- Verified public GitHub state for `berylm1/newfire`:
  - repo is public;
  - open issues: 0;
  - open PRs: 0;
  - current labels are only GitHub defaults;
  - missing routing labels: `agent-ready`, `ceo-priority`, `needs-human`, `review-this`.
- Re-tested Pi → Minisforum SSH from Hermes/Pi and it still times out to `newwaveclaw@100.79.80.119`; direct remote setup must be done from Beryl's machine or after Tailscale/SSH access is bridged.
- Created a draft GitHub Actions workflow template at `Projects/NewFire/Templates/openhands-agent-ready-workflow.yml` for routing `agent-ready` issues/PRs to OpenHands on a Minisforum self-hosted runner.

## First paste blocks for Beryl on the Minisforum

### Verify OpenHands CLI + Qwen3-Coder endpoint

```bash
cd ~/newfire-agent/workspace/repo
command -v openhands
openhands --version || true

export LLM_MODEL="<qwen3-coder-model-name-from-vllm>"
export LLM_BASE_URL="http://<dgx-spark-vllm-host>:<port>/v1"
export LLM_API_KEY="dummy"

openhands --headless --json --override-with-envs \
  -t "In this repo, inspect the top-level files and produce a short read-only summary. Do not edit files." \
  | tee ~/newfire-agent/logs/openhands-smoke-test.jsonl
```

### Check whether the Minisforum is already a GitHub self-hosted runner

```bash
systemctl --user list-units '*runner*' '*actions*' 2>/dev/null || true
systemctl list-units '*runner*' '*actions*' 2>/dev/null || true
find ~ -maxdepth 4 -type f -name run.sh -path '*actions-runner*' -print
```

### Create routing labels once GitHub write access is available

```bash
# Requires gh auth or a GITHUB_TOKEN with repo scope.
gh label create agent-ready --color 0E8A16 --description "Approved for OpenHands implementation agent" || true
gh label create ceo-priority --color B60205 --description "Include in CEO agent updates" || true
gh label create needs-human --color D93F0B --description "Needs Beryl/CEO clarification before agent work" || true
gh label create review-this --color 5319E7 --description "Run AI/code review only" || true
```
