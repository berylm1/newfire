# Kimi K2.6 and OpenCode: Implementation + Framework Impact

Written 2026-04-21.

## Current state and blocker

- Kimi K2.6 is available on both Ollama Cloud (`kimi-k2.6:cloud`) and OpenRouter (`moonshotai/kimi-k2.6`).
- Neither usable right now. Ollama Cloud requires a paid subscription. Our OpenRouter account has zero credits ("never purchased credits" error).
- Model context window: 256,000 tokens. Confirmed via OpenRouter catalog.
- OpenCode on Minisforum currently runs `deepseek-r1:32b-8k` (local, free, 8k context). That is fine for small features; it cannot hold the full NewFire codebase.

## What I did do without credits

1. Added Kimi variants and proper deepseek context windows to `CONTEXT_WINDOWS` in orchestrator.js. The metrics panel now correctly shows context utilization for these models once they're used.
2. Documented the activation path below so you can flip on with one env change once credits are loaded.

## To activate Kimi K2.6 in the backend smart router

Once OpenRouter credits are loaded ($5 minimum):

1. Add to MODEL_ROUTING in orchestrator.js:
   ```
   longcontext: { model: 'moonshotai/kimi-k2.6', provider: 'openrouter' },
   ```
2. Extend classifyAgentModel to pick `longcontext` when the agent's recent metrics show context_used_pct >= 60% on three or more calls in 24h. Or when role description contains "research", "full document", "codebase", "long conversation".
3. Rebuild backend container.

## To use Kimi K2.6 inside OpenCode for coding

OpenCode accepts any OpenAI-compatible backend. Two options:

Option A: Point OpenCode at OpenRouter directly
```
docker exec opencode-app sh -c '
  echo "OPENAI_BASE_URL=https://openrouter.ai/api/v1" >> /etc/opencode/env
  echo "OPENAI_API_KEY=<OPENROUTER_KEY>" >> /etc/opencode/env
  echo "LLM_MODEL=moonshotai/kimi-k2.6" >> /etc/opencode/env
'
docker restart opencode-app
```
Costs about 5 cents per 1k input tokens. A single autonomous feature build can burn $1-5 in one session.

Option B: Point OpenCode at LiteLLM on the Mac (for personal dev) or at LiteLLM on Minisforum (for NewFire work)
Wrap the same model behind LiteLLM to keep auth central and let us swap providers without touching OpenCode. This is what I recommend once the personal Mac stack grows, since the same LiteLLM already serves your triage workflow.

## Framework impact (the important part)

### Layer 1 (Fundamentals): context window becomes a first-class routing signal

The metrics panel we just built proves it. Right now, our agents default to `gemma4:26b` which has an 8k window. For anything conversational, fine. For anything that includes RAG retrieval plus multi-turn history plus system prompt, 8k runs out fast. Kimi's 256k window (32x larger) means entire codebases, entire client knowledge bases, entire thesis PDFs fit in a single call.

Smart-routing rule this unlocks: any chat where `context_used_pct > 60%` on `gemma4:26b` auto-routes next time to a bigger-window model. Kimi K2.6 becomes the "long-tail" model for the stack.

### Layer 4 (Models & Providers): the routing table gets a new column

Before tonight, our routing was:
- simple (fast) -> glm4:9b local
- general -> gemma4:26b local
- agentic -> minimax-m2.7 cloud
- reasoning -> glm-5.1 cloud

After Kimi lands, add:
- longcontext -> kimi-k2.6 cloud
- coding -> kimi-k2.6 cloud OR deepseek-r1:32b local

Selection criteria expands from just "how smart" to "how smart x how much context x cost". The metrics panel gives us the data to tune this weekly.

### Layer 6 (Agents & Automation): autonomous coding agent joins the team

This is the step change. OpenCode + Kimi = the "Agent 3 / Delegator" from the AI CEO blueprint, but for software work. Before: Joba hand-writes code, AI helps in-editor. After: Joba describes a feature in one paragraph, OpenCode plans, writes files, runs tests, fixes bugs, ships a PR. Human-in-the-loop shifts from "write every line" to "review the commit".

The video framed this as Level 6 of the 7 Levels ladder (OpenClaw + n8n + Claude Code as your main building tools). We are already at Level 6. Kimi + OpenCode improves the horsepower of our Level 6 tool.

**What it changes for NewFire product velocity:**
- Client onboarding tweaks Joba wants (e.g., "add an 'upgrade plan' button to Dashboard for paying clients") go from a 30-minute hand-code to a 2-minute prompt
- Per-client customizations (Funmi wants a docket viewer, Sherifah wants a calendar embed) stop being a linear cost
- Bug triage can run overnight: point OpenCode at the repo, describe the bug symptom, find and fix before morning

**What it does NOT change:**
- Layer 6 still demands HITL for anything touching production. Kimi autonomous does not mean "auto-merge to main". The commits need review. The deploys need us to push them.
- Our existing client data privacy posture (project_funmi_privacy.md) still applies: Kimi's cloud endpoint means we cannot let it see Funmi's legal corpus or any client's private content without violating the local-only rule for sensitive tenants.

### Layer 7 (No-Code Builder Tools): Paperclip and n8n are not replaced, they are complemented

OpenCode writes code; n8n wires workflows; Paperclip orchestrates agents. Each has a lane. Kimi raises the ceiling of OpenCode's lane. If we already had to choose between "build it in n8n" vs "build it as a proper service", Kimi + OpenCode makes the "proper service" path cheap enough that we default to it more often for client-facing features. For internal automation, n8n still wins on speed.

### Layer 8 (Business Layer): two new economics questions

1. **How do we price client customizations now?** If a client-specific feature costs us $3 in Kimi tokens and 10 minutes of review time, our previous "$500 custom work" fee is wrong. Options: drop the fee to make custom work common, or hold the fee and charge on outcome rather than effort.
2. **What is our model budget per client?** We already set rate limits (20 rps, 1000 req/day). We did NOT set a DOLLAR cap. If Sherifah's receptionist agent routes 500 queries/day to Kimi K2.6 at cloud pricing, that's real money. Add a `monthly_budget_usd` column to companies, hard-stop routing to expensive models when a client blows past their budget.

## Concrete next step I can do tonight

- Add `longcontext` to MODEL_ROUTING (code ready but gated, commented out)
- Extend `classifyAgentModel` to consider context signals
- Add a `monthly_budget_usd` column to companies and have the metrics writer check it before allowing cloud model calls

None of this activates Kimi without credits, but it all prepares the stack to use Kimi well the minute credits exist.

Say "prep for kimi" if you want that commit now. Say "hold" if you'd rather wait until you fund OpenRouter.
