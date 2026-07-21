# 2026-06-04 - OpenHands Wrapper Created

Status: completed
Related: [[2026-06-03 - Path From OpenHands Smoke Test to CEO Agent]], [[2026-06-03 - OpenHands Minisforum Setup Progress]]

## Outcome

Created and verified the first stable OpenHands wrapper script on the NewFire Minisforum.

Wrapper path:

```bash
/home/newwaveclaw/newfire-agent/scripts/run-openhands-task.sh
```

The wrapper provides one controlled command for running OpenHands against a disposable NewFire repo copy.

## Usage

Read-only/default mode:

```bash
~/newfire-agent/scripts/run-openhands-task.sh \
  --mode readonly \
  --task "Inspect README.md and summarize the repo. Do not edit files."
```

Docs-PR preparation mode:

```bash
~/newfire-agent/scripts/run-openhands-task.sh \
  --mode docs-pr \
  --task "Make a documentation-only improvement. Do not edit code, secrets, deploy configs, or service definitions."
```

Optional iteration override:

```bash
OPENHANDS_MAX_ITERATIONS=18 ~/newfire-agent/scripts/run-openhands-task.sh \
  --mode readonly \
  --task "Wrapper smoke test only: inspect README.md and the top-level directory listing, then finish with exactly 3 bullets. Do not edit files."
```

## Safety behavior

The wrapper:

- Refuses to run if the real repo is not on `main`.
- Refuses to run if the real repo has uncommitted changes.
- Creates a fresh disposable workspace under:

```bash
/home/newwaveclaw/newfire-agent/workspace/openhands-runs/
```

- Runs OpenHands against the disposable workspace, not the real repo.
- Sets the required OpenHands runtime env overrides:

```bash
SANDBOX_USER_ID=1000
RUN_AS_OPENHANDS=true
WORKSPACE_BASE=<disposable-workspace>
WORKSPACE_MOUNT_PATH=<disposable-workspace>
SANDBOX_VOLUMES=<disposable-workspace>:/workspace:rw
```

- Redacts common API key/token patterns from logs.
- Writes logs to:

```bash
/home/newwaveclaw/newfire-agent/logs/
```

- Writes reports to:

```bash
/home/newwaveclaw/newfire-agent/reports/
```

- Verifies whether the real repo stayed clean after the run.
- Verifies whether the disposable workspace changed.

## Verified smoke run

Command:

```bash
OPENHANDS_MAX_ITERATIONS=18 ~/newfire-agent/scripts/run-openhands-task.sh \
  --mode readonly \
  --task "Wrapper smoke test only: inspect README.md and the top-level directory listing, then finish with exactly 3 bullets summarizing what this repo contains. Do not edit files."
```

Result:

- Exit status: `0`
- OpenHands reached `AgentState.FINISHED`.
- Real repo remained clean.
- Disposable workspace had no changes.
- OpenHands read `README.md` and listed the workspace.
- OpenHands produced the requested 3-bullet repo summary.

Run artifacts:

```bash
RUN_ID=openhands-readonly-20260604-002940
LOG=/home/newwaveclaw/newfire-agent/logs/openhands-readonly-20260604-002940.log
REPORT=/home/newwaveclaw/newfire-agent/reports/openhands-readonly-20260604-002940.md
WORKSPACE=/home/newwaveclaw/newfire-agent/workspace/openhands-runs/openhands-readonly-20260604-002940
```

## OpenHands output summary

OpenHands summarized the repo as containing:

- Documentation/configuration for the NewFire AI homelab with Minisforum control plane and DGX Spark compute engine.
- Infrastructure and backend components for Docker, operational scripts, and AI agent/model-worker coordination.
- Supporting materials such as architecture diagrams, progress logs, blueprint documentation, and database backups.

## Next step

Move from local wrapper validation to GitHub control-plane validation:

1. Create GitHub labels: `agent-ready`, `ceo-priority`, `review-this`, `needs-human`.
2. Create first safe issue.
3. Run wrapper using issue text as the task source.
4. Then add branch/PR behavior for docs-only tasks.
