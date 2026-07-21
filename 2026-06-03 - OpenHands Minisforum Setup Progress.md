# 2026-06-03 - OpenHands Minisforum Setup Progress

Status: connected and partially verified
Related: [[2026-06-03 - Tonight OpenHands Agent Push Plan]], [[OpenHands CEO Update Routing Plan]]

## What worked

- Pi successfully joined the NewFire Tailscale tailnet.
- Pi can SSH into the Minisforum target:
  - Tailscale node: `america`
  - Tailscale IP: `100.79.80.119`
  - SSH user: `newwaveclaw`
- OpenHands container is already running on Minisforum:
  - Container: `openhands-dgx`
  - Image: `ghcr.io/all-hands-ai/openhands:0.44`
  - UI/API reachable over Tailscale at `http://100.79.80.119:3000/`
- OpenHands env includes model routing variables:
  - `LLM_MODEL`
  - `LLM_BASE_URL`
  - `LLM_API_KEY`
- Real NewFire repo remained unchanged after smoke tests:
  - `~/newfire-agent/workspace/repo`
  - `git status --short` returned clean.

## Smoke tests performed

A disposable repo copy was created on Minisforum:

```bash
~/newfire-agent/workspace/openhands-smoke-copy
```

OpenHands CLI was run inside the `openhands-dgx` container against that copy.

Important working overrides discovered:

```bash
SANDBOX_USER_ID=1000
RUN_AS_OPENHANDS=true
WORKSPACE_BASE=<host smoke copy path>
WORKSPACE_MOUNT_PATH=<host smoke copy path>
SANDBOX_VOLUMES=<host smoke copy path>:/workspace:rw
```

Without `SANDBOX_USER_ID=1000`, the runtime failed with:

```text
RuntimeError: Failed to create user `openhands` with UID 0. Output: [useradd: UID 0 is not unique]
```

Without overriding the workspace mount, the runtime saw an empty `/workspace`.

## Smoke result

The final smoke run successfully:

- Started the OpenHands runtime container.
- Reached the model/backend enough for the agent to think and issue tool actions.
- Listed the mounted NewFire workspace.
- Read `README.md`, `00_OVERVIEW.md`, and `infra/README.md`.
- Produced a useful internal summary of the repo structure.

However, the run ended with:

```text
RuntimeError: Agent reached maximum iteration. Current iteration: 12, max iteration: 12
```

So OpenHands execution path is functional, but the agent did not call `finish` cleanly before the iteration cap. This is acceptable for first smoke verification but needs tuning before production tasks.

## Useful log paths on Minisforum

- `/home/newwaveclaw/newfire-agent/logs/openhands-smoke-readonly-20260603-233103.log`
- `/home/newwaveclaw/newfire-agent/logs/openhands-smoke-readonly-uid1000-20260603-233143.log`
- `/home/newwaveclaw/newfire-agent/logs/openhands-smoke-codeact-copy-20260603-233423.log`
- `/home/newwaveclaw/newfire-agent/logs/openhands-smoke-codeact-mounted-20260603-233701.log`
- `/home/newwaveclaw/newfire-agent/logs/openhands-smoke-codeact-sandboxvol-20260603-233918.log`

## OpenHands agent-generated repo summary

The agent identified NewFire as a two-machine AI homelab setup:

- Minisforum X1 Pro 370 as the control plane.
- NVIDIA DGX Spark as the compute engine.
- Services include OpenClaw, OpenHands, OpenCode, Ollama, vLLM, NemoClaw, APISIX, SIE, and OpenRouter.
- Docs are organized as `00_OVERVIEW.md` through `08_CHECKLIST.md`.
- `infra/` contains deployment artifacts for Codeep, dev hub, and Cloudflared.
- Current state is Minisforum operational with DGX Spark recovery/setup documented.

## Next steps

1. Create a stable wrapper script on Minisforum for OpenHands CLI runs with the required env overrides.
2. Tune the prompt/iteration limit so the agent ends with `finish`.
3. Create GitHub labels: `agent-ready`, `ceo-priority`, `needs-human`, `review-this`.
4. Create one safe docs-only GitHub issue.
5. Decide whether to run the first real attempt manually or via GitHub Actions self-hosted runner.

## Safety status

- No production deploys.
- No push to `main`.
- No migrations.
- No service restarts.
- No secrets printed or stored.
- Real repo remained clean.
