# 2026-06-04 - GitHub Control Plane Created

Status: completed
Related: [[2026-06-04 - OpenHands Wrapper Created]], [[2026-06-04 - GitHub Control Plane Next Step]], [[OpenHands CEO Update Routing Plan]]

## Outcome

Beryl ran the Minisforum GitHub helper script successfully:

```bash
cd ~/newfire-agent/scripts
./setup-github-control-plane.py
```

The script authenticated to GitHub as:

```text
berylm1
```

It created the NewFire agent-control labels and first safe issue.

## Labels created

- `agent-ready` — Approved for controlled OpenHands agent execution.
- `ceo-priority` — Include in CEO/stakeholder updates.
- `review-this` — Review-only task; do not implement changes automatically.
- `needs-human` — Blocked until human clarification or approval.

## First issue created

```text
Issue: #1
Title: Agent smoke test: summarize NewFire repo structure
URL: https://github.com/berylm1/newfire/issues/1
Labels: agent-ready, ceo-priority
State: open
```

## Issue-backed OpenHands run

Hermes then ran the OpenHands wrapper against the issue #1 smoke-test intent.

First attempt:

- Run ID: `openhands-readonly-20260604-015215`
- Real repo status: clean
- Result: OpenHands got stuck in a repeated `ls -F` loop and reached `AgentState.ERROR`.
- Safety impact: none; real repo stayed clean.

Second attempt with anti-loop wording:

```bash
OPENHANDS_MAX_ITERATIONS=18 ~/newfire-agent/scripts/run-openhands-task.sh \
  --mode readonly \
  --task "Issue 1 smoke test. Read README.md once and list the top-level directories once. Then immediately call finish. Final answer must contain exactly: 1) 3 bullets summarizing the repo, 2) Risk level: low, 3) Real repo clean: yes. Do not edit files. Do not repeat commands."
```

Successful run artifacts:

```text
RUN_ID=openhands-readonly-20260604-015517
LOG=/home/newwaveclaw/newfire-agent/logs/openhands-readonly-20260604-015517.log
REPORT=/home/newwaveclaw/newfire-agent/reports/openhands-readonly-20260604-015517.md
WORKSPACE=/home/newwaveclaw/newfire-agent/workspace/openhands-runs/openhands-readonly-20260604-015517
REAL_REPO_STATUS=clean
```

Verification:

- Exit status: `0`
- Agent state: `AgentState.FINISHED`
- Real repo remained clean.
- Task completed in disposable workspace.

## OpenHands final output

OpenHands summarized the repo as:

- NewFire is a two-machine AI homelab system using a Minisforum X1 Pro 370 control plane and NVIDIA DGX Spark GPU compute for local LLMs and agent orchestration.
- The system includes services like OpenClaw, OpenHands, OpenCode, APISIX, Ollama, vLLM, and NemoClaw running across the two nodes with tenant-aware API metering.
- Documentation is organized in numbered steps covering architecture, recovery, setup, integration patterns, and launch checklist.

Risk level: low

Real repo clean: yes

## Next step

Because Hermes/Minisforum did not retain the GitHub token, issue commenting was not performed automatically. The next practical step is either:

1. Manually comment on issue #1 with the successful run output, or
2. Add a short helper for Beryl to paste a token and post the run report as an issue comment without saving credentials.

After that, the next phase is docs-only PR behavior: have the agent make a low-risk documentation change in a disposable workspace, review the diff, then create a branch/PR only after human approval.
