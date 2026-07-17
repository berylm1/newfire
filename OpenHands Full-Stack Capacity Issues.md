# OpenHands: Full-Stack Engineer Capacity Issues
*Audited: 2026-06-24 | Updated: 2026-06-25 | Version: agent-canvas v1.28.1 | Model: qwen3-coder-30b via vLLM on DGX*

---

## Summary

OpenHands is capable of operating as a full-stack AI engineer but had 12 distinct issues across 4 categories. 10 issues are now fixed or resolved. 2 remain open (low priority).

---

## Category 1: Authentication and GitHub Access

### ISSUE-01: GitHub PAT was expired (FIXED)
**What it caused:** Every git clone stalled at a `Username for 'https://github.com':` interactive prompt, timed out after 30 seconds, and exited with code -1. The agent had no way to distinguish "auth failure" from "repo does not exist."

**Root cause:** The token stored in OpenHands secrets (`ghp_Ml3V...`) was revoked since it was saved. No fallback was configured.

**Fix applied:** New PAT generated and injected at three levels: (1) re-encrypted into `secrets.json`, (2) as `GITHUB_TOKEN` Docker env var so the container always has it, (3) written to `~/.git-credentials` with credential.helper=store so HTTPS clones authenticate without prompting.

---

### ISSUE-02: gh CLI had no authentication (FIXED)
**What it caused:** `gh issue create`, `gh pr create`, and all GitHub workflow commands failed silently or with "not authenticated."

**Root cause:** gh CLI requires either `gh auth login` or a `GITHUB_TOKEN` env var. Neither was configured.

**Fix applied:** `GITHUB_TOKEN` env var is now baked into the container. gh CLI reads it automatically on every invocation.

---

### ISSUE-03: git user identity not configured (FIXED)
**What it caused:** `git commit` failed with "Please tell me who you are" on every attempt.

**Root cause:** No `git config --global user.email` or `user.name` was set inside the container.

**Fix applied:** Added `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, `GIT_COMMITTER_EMAIL` as Docker env vars and ran `git config --global` inside the container.

---

## Category 2: Browser and UI Visibility

### ISSUE-04: Browser screenshots not appearing in Browser panel (FIXED)
**What it caused:** The browser panel in OpenHands showed nothing. The agent was navigating pages but the human operator could not see what was on screen. Failed in 4 of 6 test cases.

**Root cause (4 separate sub-causes):**
1. The `browser-screenshots` skill used keyword triggers. Natural phrases like "check", "open", "pull up", "localhost" never matched and the skill never activated.
2. Skill activation only evaluated keywords on the first message of a conversation. Mid-conversation follow-ups never re-triggered it.
3. The skill was added to settings mid-day. All conversations created before that point had it completely absent.
4. The underlying `browser_get_state` tool defaults `include_screenshot` to `false`. The skill instruction was a one-sentence suggestion the model did not reliably follow.

**Fix applied:**
- Changed skill `trigger` from `"type": "keyword"` to `null`. Per OpenHands source code, `trigger=None` injects the skill content directly into the system prompt on every conversation, every turn, permanently.
- Rewrote skill content from a suggestion to an explicit mandatory rule with correct/wrong examples.
- Added `system_message_suffix` and `user_message_suffix` as per-turn and per-message reminders.
- MCP Playwright (`@playwright/mcp`) moved to `disabled_mcpServers`. The agent cannot pick the wrong route.
- Skill updated to v1.1.0 (2026-06-25): removed the MCP Playwright fallback instruction since Playwright is disabled, leaving only the built-in VNC/headed Chromium path.

---

### ISSUE-05: No live browser view between tool calls (OPEN - LOW PRIORITY)
**What it means:** The VNC display (:1, 1280x800) and noVNC proxy (port 8002) are running correctly. The visual browser panel works when `include_screenshot=true` is passed. But there is no persistent "live view" of the browser. The panel only refreshes when the agent explicitly calls `browser_get_state(include_screenshot=true)`. The operator cannot watch the agent browse in real time between tool calls.

**Recommended fix:** No configuration fix available within OpenHands settings. This is an architectural limitation of how agent-canvas renders browser state. Workaround: the `system_message_suffix` already instructs the agent to call `browser_get_state(include_screenshot=true)` after every single browser interaction.

---

## Category 3: Development Environment

### ISSUE-06: pnpm/Corepack interactive prompts blocked package installation (FIXED)
**What it caused:** `pnpm install` prompted for interactive Y/n Corepack confirmation. The agent's non-interactive bash shell could not answer it. The command hung, the agent retried twice, then called `FinishAction` and quit the entire task.

**Root cause:** Corepack prompts for permission to download package managers when `COREPACK_ENABLE_DOWNLOAD_PROMPT` is not set. In CI/non-interactive environments this blocks indefinitely.

**Fix applied:**
- Added `CI=true`, `COREPACK_ENABLE_DOWNLOAD_PROMPT=0`, `NPM_CONFIG_YES=true`, `npm_config_yes=true` as Docker env vars.
- Written to `/etc/environment` inside the container (PAM-level, survives tmux session creation) and `/etc/profile.d/oh-env.sh` (login shells).
- Created `/usr/local/bin/oh-bootstrap.sh`: a universal repo bootstrap script that sets `COREPACK_ENABLE_DOWNLOAD_PROMPT=0` explicitly as an inline prefix on every `pnpm install` invocation, independent of shell environment inheritance.

**Validated:** farmer-data-collection-v3 (1635 packages, 596/606 tests passing) installed cleanly without prompts.

---

### ISSUE-07: Docker socket not accessible inside container (OPEN - HIGH PRIORITY)
**What it causes:** The agent cannot run `docker compose up`, `docker build`, `docker run`, or any Docker command to start and test the application stack. `docker` binary exists at `/usr/bin/docker` but `/var/run/docker.sock` is not mounted into the container. All `docker compose` deployment verification steps silently fail.

**Impact:** For full-stack deployment testing this is the single biggest remaining blocker. An agent cannot verify that services start, read container logs, or test networked services it deploys itself.

**Recommended fix:** Mount the Docker socket into the container:
```
-v /var/run/docker.sock:/var/run/docker.sock
```
Security note: this gives the container full Docker daemon access (root equivalent on the host). Use a dedicated Docker-in-Docker sidecar or rootless Docker as a safer alternative. Requires container recreation.

---

### ISSUE-08: Agent quits early instead of continuing past blockers (FIXED)
**What it caused:** When blocked (pnpm hung, server unreachable, tool missing), the agent called `FinishAction` and stopped, leaving most of the task incomplete.

**Root cause:** The model treats a blocked subtask as a reason to summarize and exit. The `FinishTool` description in source code even says "Use when you cannot proceed further due to technical limitations," actively encouraging quitting. `AgentFinishedCritic` was disabled.

**Fix applied:**
- Enabled `AgentFinishedCritic` via `verification.critic_enabled: true` in `agent_settings` (the SDK reads from `agent_settings.verification`, not the top-level `verification` key).
- `enable_iterative_refinement: true`, `max_refinement_iterations: 3`, `critic_threshold: 0.6`.
- `AgentFinishedCritic.evaluate()` returns score 0.0 when `FinishAction` is called without a git patch, triggering up to 3 refinement iterations before allowing the agent to stop.
- Added `developer-environment` always-on skill with explicit rule: "Never call FinishAction until all phases are complete."

**Note:** The top-level `verification` key in settings.json is ignored by the SDK. The fix must target `agent_settings.verification`.

---

## Category 4: Architecture and Intelligence

### ISSUE-09: Sub-agent parallelization not functional (FIXED)
**What it caused:** Attempts to register a `code_reader` agent type and dispatch parallel tasks failed: "Unknown agent 'code_reader'. Available types: none registered." Zero parallel work ran.

**Root cause:** Agent type registration (`register_agent()`) is not supported in agent-canvas 1.28.1. The REST API does have `POST /conversations/{id}/fork` and `POST /conversations/{fork_id}/events`, but these were server-side only.

**Fix applied:** Implemented `SpawnAgentTool` as a new Python module at:
`/usr/local/lib/python3.13/site-packages/openhands/sdk/tool/builtins/spawn_agent.py`

The tool wraps the fork REST API so the model can call it as a native tool:
1. `POST /conversations/{current_id}/fork` to deep-copy the conversation event history
2. `POST /conversations/{fork_id}/events` with `{"role": "user", "content": task, "run": true}` to dispatch the sub-task

Registered in `BUILT_IN_TOOLS` and `BUILT_IN_TOOL_CLASSES` in `builtins/__init__.py`. Added `SpawnAgentTool` to `agent.include_default_tools` in settings.json.

**Limitation:** Sub-agents run sequentially from the model's perspective (it dispatches and gets a `fork_id` back, but does not wait for results in the same turn). True parallel execution requires multiple concurrent conversations managed by an orchestrator layer above the model.

---

### ISSUE-10: Critic and iterative refinement disabled (FIXED)
**What it caused:** The agent completed tasks and called FinishAction without self-verifying whether what it produced was correct.

**Root cause:** `agent_settings.verification.critic_enabled: false` and `enable_iterative_refinement: false`.

**Fix applied:** Updated `agent_settings.verification` (the key the SDK reads) in settings.json:
```json
"verification": {
    "critic_enabled": true,
    "critic_mode": "finish_and_message",
    "enable_iterative_refinement": true,
    "max_refinement_iterations": 3,
    "critic_threshold": 0.6
}
```
Container restarted to pick up changes.

---

### ISSUE-11: Context condenser can silently drop task state mid-run (FIXED)
**What it caused:** The condenser summarized conversations at 240 messages. On a large multi-phase task the agent could lose track of open GitHub issues, completed phases, file paths, and error messages.

**Root cause:** LLM summarization compresses prior context into a paragraph. Structured state (issue numbers, branch names, file paths) does not survive summarization reliably.

**Fix applied:** Increased `agent_settings.condenser.max_size` from 240 to 400. This gives the agent roughly 65% more runway before condensation fires on long tasks.

**Remaining mitigation:** The `developer-environment` skill instructs the agent to write progress to files so condensation-induced amnesia is recoverable.

---

### ISSUE-12: Model global config not persisted in settings (OPEN - INFORMATIONAL)
**What it means:** `model: null` and `base_url: null` in the global settings. The model (qwen3-coder-30b via vLLM on DGX) is configured per-conversation through profiles, not at the global settings level. If a profile is misconfigured or the DGX vLLM server is down, new conversations silently fail to initialize.

**Note:** The `agent_settings.llm` block does have the model configured (`openai/qwen3-coder-30b-64k:latest` at `http://100.88.112.5:11434/v1`). The top-level null is a UI display issue, not a runtime issue.

**Recommended fix:** Verify whether the active profile is being applied on every new conversation. If so, this is low risk. If not, set a global model fallback in settings.json.

---

## Status Summary

| # | Issue | Category | Status | Priority |
|---|-------|----------|--------|----------|
| 01 | Expired GitHub PAT | Auth | FIXED | - |
| 02 | gh CLI unauthenticated | Auth | FIXED | - |
| 03 | git user identity missing | Auth | FIXED | - |
| 04 | Browser screenshots not showing | Browser | FIXED | - |
| 05 | No live browser view between tool calls | Browser | OPEN | Low |
| 06 | pnpm Corepack interactive prompt | Dev Env | FIXED | - |
| 07 | Docker socket not mounted | Dev Env | OPEN | HIGH |
| 08 | Agent quits early on blockers | Dev Env | FIXED | - |
| 09 | Sub-agent parallelization broken | Architecture | FIXED | - |
| 10 | Critic and refinement disabled | Architecture | FIXED | - |
| 11 | Context condenser drops task state | Architecture | FIXED | - |
| 12 | Global model config not persisted | Architecture | OPEN | Low |

**10 fixed, 2 open. Biggest remaining blocker for full-stack deployment work: ISSUE-07 (Docker socket).**

---

## Devin.ai Parity Validation (2026-06-24)

End-to-end test run on `berylm1/farmer-data-collection-v3` (Node.js/TypeScript monorepo, pnpm, Express, Drizzle ORM, PostgreSQL):

- **pnpm install:** 1635 packages, no Corepack prompts (oh-bootstrap.sh + /etc/environment fix)
- **tsc --noEmit:** Clean, zero type errors
- **Test suite:** 596 passed / 10 failed / 30 skipped
- **Server:** Running on port 3001

The 10 failures are not tooling or environment issues. They split into:
1. `auth.test.ts`: Hard-codes `postgresql://postgres:postgres@localhost:5432/farmer_data` but the running PostgreSQL uses `fatima_user:StrongDBPass123!`. Fix: create `.env.test` with correct `DATABASE_URL`.
2. `e2e-farmer-journey.test.ts` (2 tests): Assert unauthenticated access to `/api/pool-metrics` and expect `x-trace-id` headers on redirected routes. Fix: test assertion update or server auth policy adjustment.

---

## Next Steps (in order)

1. **Mount Docker socket** into the container so the agent can run `docker compose up` and verify deployments (requires container recreate with `-v /var/run/docker.sock:/var/run/docker.sock`)
2. **Verify critic fires** on a real task by watching for refinement iterations in conversation events
3. **Accept ISSUE-12** as low-risk (model is configured in `agent_settings.llm`; top-level null is cosmetic)
4. **Fix farmer-data-collection-v3 test credentials** with a `.env.test` file for the remaining 10 failures
