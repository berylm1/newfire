# 2026-06-03 - Tonight OpenHands Agent Push Plan

Status: planned for tonight
Project: [[NewFire Task Index|NewFire Tasks]]
Related: [[OpenHands CEO Update Routing Plan]]

## Objective

By tonight, get the NewFire OpenHands agent from “installed pieces” to a controlled first working loop:

GitHub approved task → Minisforum OpenHands worker → DGX Spark Qwen3-Coder vLLM → branch/PR or report → Hermes/Beryl CEO-style update.

## Tonight success definition

Minimum success:

1. Minisforum can run OpenHands headless against the NewFire repo using DGX Spark Qwen3-Coder.
2. GitHub repo has routing labels: `agent-ready`, `ceo-priority`, `needs-human`, `review-this`.
3. There is one safe test issue in GitHub.
4. OpenHands performs a read-only or tiny documentation-only task and produces logs.
5. Beryl receives a concise agent update summary.

Stretch success:

1. Minisforum is registered as a GitHub self-hosted runner.
2. Draft workflow is committed to `.github/workflows/openhands-agent-ready.yml`.
3. Labeling an issue `agent-ready` triggers the runner automatically.
4. OpenHands opens a PR.

## Phase 0 — Safety boundaries

- Do not let the agent push to `main`.
- Do not let the agent deploy, migrate databases, restart services, or touch production secrets.
- First task should be read-only or docs-only.
- First implementation PR should be small enough to review in under 10 minutes.
- GitHub PR is the approval gate.

## Phase 1 — Connect to Minisforum

From Beryl’s machine that can reach the NewFire tailnet:

```bash
ssh newwaveclaw@100.79.80.119
```

Then verify baseline:

```bash
hostname
whoami
pwd
cd ~/newfire-agent/workspace/repo
git status --short
git branch --show-current
git pull --ff-only origin main
```

Expected: user is `newwaveclaw`, repo is clean or only known local files, branch is `main`.

## Phase 2 — Verify OpenHands + DGX Spark vLLM

On the Minisforum:

```bash
cd ~/newfire-agent/workspace/repo
command -v openhands
openhands --version || true
```

Set the Qwen3-Coder endpoint values:

```bash
export LLM_MODEL="<qwen3-coder-model-name-from-vllm>"
export LLM_BASE_URL="http://<dgx-spark-vllm-host>:<port>/v1"
export LLM_API_KEY="dummy"
```

Run a read-only smoke test:

```bash
mkdir -p ~/newfire-agent/logs
openhands --headless --json --override-with-envs \
  -t "In this repo, inspect the top-level files and produce a short read-only summary. Do not edit files." \
  | tee ~/newfire-agent/logs/openhands-smoke-test.jsonl
```

Pass condition:

- OpenHands starts successfully.
- It calls the DGX Spark endpoint.
- It returns a useful repo summary.
- It does not edit files.

Verify no edits:

```bash
git status --short
```

## Phase 3 — Create GitHub routing labels

From a machine with GitHub write access and `gh` authenticated:

```bash
cd ~/newfire-agent/workspace/repo

gh label create agent-ready --color 0E8A16 --description "Approved for OpenHands implementation agent" || true
gh label create ceo-priority --color B60205 --description "Include in CEO agent updates" || true
gh label create needs-human --color D93F0B --description "Needs Beryl/CEO clarification before agent work" || true
gh label create review-this --color 5319E7 --description "Run AI/code review only" || true
```

Verify:

```bash
gh label list | grep -E 'agent-ready|ceo-priority|needs-human|review-this'
```

## Phase 4 — Create one safe test issue

Create a small docs-only test issue:

```bash
gh issue create \
  --title "Agent smoke test: summarize NewFire repo structure" \
  --body "This is a controlled OpenHands smoke test. The agent should inspect the repository and create a short Markdown summary under docs/agent-smoke-test.md. Do not modify production code, deploy, migrate, or touch secrets. Open a PR only." \
  --label agent-ready \
  --label ceo-priority
```

This gives the CEO-agent a real queue item without risking code.

## Phase 5A — If no GitHub self-hosted runner exists yet: manual OpenHands run

Create a branch manually:

```bash
cd ~/newfire-agent/workspace/repo
git checkout main
git pull --ff-only origin main
git checkout -b agent/smoke-test-repo-summary
```

Run OpenHands with a bounded task:

```bash
openhands --headless --json --override-with-envs \
  -t "Create docs/agent-smoke-test.md with a concise summary of the NewFire repo structure and obvious next engineering checks. Do not modify production code. Do not edit secrets. After writing the doc, stop." \
  | tee ~/newfire-agent/logs/openhands-doc-smoke-test.jsonl
```

Review changes:

```bash
git status --short
git diff -- docs/agent-smoke-test.md
```

If safe, commit and open PR:

```bash
git add docs/agent-smoke-test.md
git commit -m "docs: add OpenHands agent smoke-test summary"
git push -u origin HEAD

gh pr create \
  --title "docs: add OpenHands agent smoke-test summary" \
  --body "## Summary
- First controlled OpenHands smoke test on the NewFire repo
- Uses Minisforum OpenHands worker with DGX Spark Qwen3-Coder vLLM endpoint
- Docs-only change; no production code touched

## Safety
- No deployment
- No database migration
- No secret changes
- Human review required before merge"
```

## Phase 5B — If self-hosted GitHub runner exists: wire workflow

Check runner:

```bash
systemctl --user list-units '*runner*' '*actions*' 2>/dev/null || true
systemctl list-units '*runner*' '*actions*' 2>/dev/null || true
find ~ -maxdepth 4 -type f -name run.sh -path '*actions-runner*' -print
```

If runner exists, copy the draft workflow from Obsidian into the repo:

```bash
mkdir -p .github/workflows
# Copy content from:
# /home/beryl/Obsidian vault/Projects/NewFire/Templates/openhands-agent-ready-workflow.yml
# into:
# .github/workflows/openhands-agent-ready.yml
```

Before commit, edit:

- `runs-on` labels to match the actual Minisforum runner labels.
- GitHub secrets names if needed:
  - `OPENHANDS_LLM_MODEL`
  - `OPENHANDS_LLM_BASE_URL`
  - `OPENHANDS_LLM_API_KEY`

Commit workflow only after runner and secret names are confirmed.

## Phase 6 — CEO/Beryl update

Send Beryl this status after the smoke test:

```text
NewFire Agent Update — Tonight

- Progress: OpenHands worker was tested on the Minisforum against the DGX Spark Qwen3-Coder endpoint.
- Output: [repo summary generated / PR opened / blocked at X].
- Safety: no production code merged; no deployment or secret changes.
- Quality gate: [smoke test passed / failed with reason].
- Next decision: approve GitHub runner workflow or continue manual PR-only agent runs.
```

## If blocked

### If OpenHands cannot reach vLLM

Check from Minisforum:

```bash
curl "$LLM_BASE_URL/models" -H "Authorization: Bearer $LLM_API_KEY"
```

Then verify the model name exactly matches the vLLM-served model.

### If `gh` is missing or not authenticated

Use GitHub web UI for labels/issues tonight, or install/login later.

### If runner is missing

Do not block the night. Use manual OpenHands headless run first, then configure the runner tomorrow.

## Recommended tonight route

1. Do Phase 1.
2. Do Phase 2.
3. Do Phase 3.
4. Do Phase 4.
5. If runner exists, attempt Phase 5B.
6. If runner does not exist, do Phase 5A and open a docs-only PR manually.

This gets a real CEO-agent proof point tonight without taking unnecessary production risk.
