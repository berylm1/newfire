# 2026-06-04 - GitHub Control Plane Next Step

Status: waiting for GitHub write authentication
Related: [[2026-06-04 - OpenHands Wrapper Created]], [[2026-06-03 - Path From OpenHands Smoke Test to CEO Agent]]

## Current state

The OpenHands wrapper is created and verified on the Minisforum:

```bash
/home/newwaveclaw/newfire-agent/scripts/run-openhands-task.sh
```

The next step is to create the GitHub control plane for agent-approved tasks.

## Authentication finding

On the Minisforum:

- `gh` CLI is not installed.
- No `GITHUB_TOKEN` is present in the process environment.
- No `~/.hermes/.env` GitHub token is present.
- No GitHub credential entry exists in `~/.git-credentials`.

Therefore Hermes cannot create labels/issues directly until Beryl provides GitHub write authentication locally on the Minisforum.

## Helper script created

A helper script was installed on the Minisforum:

```bash
/home/newwaveclaw/newfire-agent/scripts/setup-github-control-plane.py
```

It will:

1. Prompt silently for a GitHub token if `GITHUB_TOKEN` is not set.
2. Create/verify these labels:
   - `agent-ready`
   - `ceo-priority`
   - `review-this`
   - `needs-human`
3. Create the first safe issue:
   - `Agent smoke test: summarize NewFire repo structure`
4. Apply labels:
   - `agent-ready`
   - `ceo-priority`
5. Print the issue number.

The script does not save the token.

## Command for Beryl to run on Minisforum

```bash
cd ~/newfire-agent/scripts
./setup-github-control-plane.py
```

When prompted, paste a GitHub token with repo access. The input is hidden.

## Alternate command if token is already exported

```bash
export GITHUB_TOKEN='***'
cd ~/newfire-agent/scripts
./setup-github-control-plane.py
unset GITHUB_TOKEN
```

## After setup succeeds

Run the OpenHands wrapper using the issue's safe task text:

```bash
OPENHANDS_MAX_ITERATIONS=18 ~/newfire-agent/scripts/run-openhands-task.sh \
  --mode readonly \
  --task "GitHub issue smoke test: summarize the NewFire repo structure in 3-5 bullets. Do not edit files. Confirm the real repo remains clean."
```

Then comment on the GitHub issue with:

- Run ID
- Report path
- Log path
- Confirmation that real repo remained clean
- Short summary

## Safety notes

No GitHub labels/issues were created yet by Hermes because write authentication is not configured. The helper script is ready for Beryl to run locally with a token.
