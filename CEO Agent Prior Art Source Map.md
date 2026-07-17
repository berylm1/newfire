# CEO Agent Prior Art Source Map

Created: 2026-06-03
Purpose: early source-gathering for the NewFire CEO-requested coding/review agent. This is a research map, not a final architecture decision.

## Local setup we should optimize around

- Production worker: NewFire Minisforum host, not the Raspberry Pi.
- Intended loop: GitHub repository -> issue/PR/task queue -> agent works in sandbox -> tests -> opens PR / leaves review -> human approval.
- Pi/Hermes role: orchestration, documentation, scheduling, coordination, and CEO-facing summaries unless explicitly promoted.

## Prior art / source list

### 1. OpenHands

- URL: https://github.com/OpenHands/OpenHands
- Docs: https://docs.openhands.dev/modules/usage/how-to/github-action
- What it proves: a self-hostable/open-source software agent can work from GitHub issues and PR comments. The GitHub Action can trigger from a `fix-me` label or an `@openhands-agent` comment, then attempt to resolve the issue or PR.
- Fit for NewFire: strong candidate for the implementation worker route because it already has GitHub issue/PR workflows and local/API deployment options.

### 2. SWE-agent / mini-SWE-agent

- SWE-agent repo: https://github.com/SWE-agent/SWE-agent
- mini-SWE-agent repo: https://github.com/SWE-agent/mini-swe-agent
- Docs: https://swe-agent.com/latest/usage/hello_world/
- What it proves: agents can take a GitHub issue, run inside a Docker sandbox, edit code, run tests, and try to fix real repository issues. SWE-agent’s own docs specifically frame a tutorial around fixing a GitHub issue and using Docker sandbox execution.
- Fit for NewFire: excellent low-complexity baseline for a nightly “take issue -> attempt fix -> report/PR” worker.

### 3. GitHub Copilot cloud agent

- Docs: https://docs.github.com/en/copilot/concepts/coding-agent/coding-agent
- Start sessions: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/assign-copilot-to-an-issue
- What it proves: GitHub itself now supports background coding agents that can research a repo, create implementation plans, fix bugs, implement small features, improve tests/docs, address tech debt, and create PRs.
- Fit for NewFire: best hosted reference model for the UX and governance pattern, even if we choose a self-hosted route.

### 4. PR-Agent / Qodo PR-Agent

- Repo: https://github.com/The-PR-Agent/pr-agent
- GitHub installation docs: https://docs.pr-agent.ai/installation/github/
- Usage docs: https://docs.pr-agent.ai/usage-guide/automations_and_usage/
- What it proves: open-source PR review automation can run as a GitHub Action, comment on PRs, review, describe, improve, ask questions, and respond to PR comments.
- Fit for NewFire: strong review-side component. Pair with an implementation agent instead of expecting one tool to do everything.

### 5. Aider

- Repo/docs: https://github.com/Aider-AI/aider and https://aider.chat/
- What it proves: terminal-based coding agents can map a codebase, edit files, and work well as an agent-controlled CLI tool.
- Fit for NewFire: useful as the underlying coding CLI inside a wrapper, especially if Hermes/Cron creates focused tasks and captures logs.

### 6. OpenAI Codex CLI

- Repo: https://github.com/openai/codex
- What it proves: lightweight terminal coding agents are a mainstream route for local/self-hosted coding workflows.
- Fit for NewFire: candidate CLI worker on the Minisforum if API/model access and repo permissions are configured safely.

### 7. Claude Code Action

- Repo: https://github.com/anthropics/claude-code-action
- What it proves: coding agents can be wired directly into GitHub Actions for issue/PR-based workflows.
- Fit for NewFire: useful reference for GitHub-native triggering and permission boundaries, whether or not Claude is the chosen model/provider.

### 8. Gemini CLI / run-gemini-cli GitHub Action

- Gemini CLI repo: https://github.com/google-gemini/gemini-cli
- GitHub Action repo: https://github.com/google-github-actions/run-gemini-cli
- What it proves: model-provider CLIs are also being packaged as GitHub Actions, so the industry pattern is converging around “agent CLI + GitHub workflow + constrained token/permissions.”
- Fit for NewFire: another reference implementation for issue/PR automation and GitHub Action wiring.

### 9. OpenCode

- Repo: https://github.com/anomalyco/opencode
- What it proves: open-source terminal coding agents are mature enough to be run as local worker tools.
- Fit for NewFire: possible local CLI option, especially if we want a provider-flexible tool rather than only one vendor.

### 10. Pythagora / GPT Pilot

- Repo: https://github.com/Pythagora-io/gpt-pilot
- What it proves: multi-step app-building agents exist and can run in Docker/local workflows.
- Fit for NewFire: better reference for greenfield app-building than for careful production repo maintenance; likely not the first route.

## Emerging pattern

The strongest prior-art pattern is not “one magical CEO agent.” It is a governed pipeline:

1. Human/CEO creates or labels a GitHub issue, or Hermes creates a nightly task from a backlog.
2. Agent runs on a dedicated worker with repo checkout, secrets, and Docker sandboxing.
3. Agent produces a patch branch/PR, test log, and plain-English summary.
4. Separate review agent reviews the PR and flags risks.
5. Human approves merge.
6. Hermes posts a concise CEO update and records the decision/status in Obsidian.

## Initial recommendation to evaluate next

Start with a two-lane prototype on the Minisforum:

- Implementation lane: mini-SWE-agent or OpenHands.
- Review lane: PR-Agent.
- Orchestration lane: Hermes cron/job on Pi or Minisforum triggers nightly, watches GitHub issues/labels, and sends 3-5 bullet CEO updates.

This keeps the system close to what others have already proven while matching NewFire’s need for safety, reviewability, and production separation from Pi learning experiments.
