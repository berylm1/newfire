#!/usr/bin/env python3
"""
NewFire second brain bootstrap for Apple Notes (iCloud / Personal account).

Creates a folder tree under "NewFire" and seeds the canon notes (architecture
and north-star) pulled from memory. Project, daily-log, and decisions folders
get a short how-to-use placeholder only.

Re-runnable: existing folders and notes by the same title are skipped.
"""

import subprocess
import sys

ACCOUNT = "Personal"
PARENT = "NewFire"

# Folder list (top-level subfolders under NewFire)
FOLDERS = [
    "00 Inbox",
    "01 North Star",
    "02 Architecture",
    "03 Active Projects",
    "04 Daily Log",
    "05 Decisions",
]

# (folder, title, body_html) tuples
NOTES = [
    # ---------- 00 Inbox ----------
    ("00 Inbox", "How to use Inbox",
     """<div><b>Capture first, organize later.</b></div>
<br>
<div>Drop anything here that needs to be remembered: an idea, a question, a screenshot, a snippet of a conversation, a thought from the shower. Do not stop to file it. The point of this folder is zero friction.</div>
<br>
<div><b>Capture methods</b></div>
<ul>
<li>iPhone: lock screen widget, share sheet from any app, or Siri "Hey Siri, add a note to Inbox"</li>
<li>Mac: <b>fn fn</b> for dictation, or Notes app sidebar</li>
<li>Apple Watch: dictate via Siri</li>
</ul>
<br>
<div><b>Weekly ritual (Sunday)</b></div>
<div>Move each item to its real home (North Star, Architecture, Active Projects, Decisions) or delete. Inbox should reach zero every Sunday.</div>"""),

    # ---------- 01 North Star ----------
    ("01 North Star", "AI Operating System Blueprint",
     """<div>The canonical framework NewFire is built to. Quote, do not re-derive.</div>
<br>
<div><b>The 8 Layers</b></div>
<ol>
<li>Fundamentals (token, model, prompt, context, temperature)</li>
<li>Data and Knowledge (embedding, vector DB, RAG, fine-tuning)</li>
<li>Intelligence Layer (system prompt, memory, multimodal, guardrails)</li>
<li>Models and Providers (Claude, GPT, Gemini, Llama, Mistral)</li>
<li>Infrastructure and Connectivity (API, webhooks, MCP, function calling, SDK)</li>
<li>Agents and Automation (orchestration, multi-agent, HITL) <i>highest leverage</i></li>
<li>No-Code Builder Tools (n8n, Zapier, Flowise, Voiceflow)</li>
<li>Business Layer (use case, ROI, AI strategy, AI stack)</li>
</ol>
<div>Layers 5, 6, 7 are where entrepreneur leverage lives. Layer 4 is where most people waste time arguing which model is best.</div>
<br>
<div><b>The 5 Agents (conductor and orchestra)</b></div>
<ol>
<li>Strategist or Chief of Staff: research, competitive scan, decisions (Perplexity, Manus, Claude)</li>
<li>PR: meeting summaries, drafts, decks (Fireflies, Gemini, Gamma)</li>
<li>Delegator: SOP documentation (Scribe or screen capture plus LLM)</li>
<li>Operator: trigger-to-action automation (Zapier, n8n)</li>
<li>Content Flywheel: one weekly thought expanded to 10 to 20 pieces in your voice</li>
</ol>
<br>
<div><b>Frame quotes</b></div>
<div>"Misdiagnosis in AI does not just waste time, it destroys your confidence."</div>
<div>"Stop playing every single instrument yourself. You are the conductor."</div>
<div>"You are paid for leading, but in reality you are doing high-paid intern work."</div>
<div>"If you cannot articulate the time saved, the revenue added, or the cost reduced, rethink the use case before you build."</div>
<br>
<div><b>When to use</b></div>
<ul>
<li>Before starting any new infra work, check which layer the problem lives on.</li>
<li>Before tempted to compare models, ask whether Layer 4 is really the bottleneck.</li>
<li>When designing automation for yourself, map it to one of the 5 agents.</li>
</ul>
<br>
<div><i>Source: BLUEPRINT.md at Desktop/AI_Homelab_Setup/blueprint/</i></div>"""),

    ("01 North Star", "Operating Framework (Visionary Architect)",
     """<div><b>Core identity:</b> Visionary Architect and CEO who operates at the intersection of high-level strategy and technical mastery.</div>
<div><b>Strengths:</b> Belief, Learner, Performer. Sanguine temperament.</div>
<div><b>Risk:</b> Ni-Ti loop exhaustion from reactive over-performance.</div>
<br>
<div><b>Four life domains</b></div>
<ol>
<li>BlueRoses Inc. (company)</li>
<li>UMES Research (thesis: Blue Catfish Adaptive AI Educator)</li>
<li>Residence Life (UMES duty)</li>
<li>Personal Growth (technical mastery, learning, spiritual, physical)</li>
</ol>
<br>
<div><b>Non-negotiable scheduling rules</b></div>
<ul>
<li><b>15-Minute Reset.</b> Mandatory buffer between meetings or context switches. No back-to-back.</li>
<li><b>Deep Work Blocks.</b> 3-hour uninterrupted blocks for BlueRoses and BlueCatfish during peak cognitive hours: <b>07:00 to 10:00 AM</b> and <b>21:00 to 24:00 ET</b>. Target 5 or more per week.</li>
<li><b>Sanguine Yes Filter.</b> If a request is reactive rather than strategic, ask: "Does this align with the Primary Vision, or is this a Sanguine distraction?"</li>
<li><b>Learner's Path.</b> Protected time for technical mastery (AI homelab, certifications). Admin does not swallow it.</li>
</ul>
<br>
<div><b>Tension to manage:</b> Bible reading typically runs 21:50 to 23:00, which overlaps the night peak window. Schedule must surface this conflict, not hide it.</div>
<br>
<div><b>Weekly ritual (Sunday):</b> produce a Battle Map for the coming week with Deep Work blocks, buffers, and domain allocations.</div>
<div><b>Daily morning:</b> name the Single Most Productive Move for that day.</div>"""),

    ("01 North Star", "NewFire Mission and May 1 Goal",
     """<div><b>What NewFire is:</b> a commercial AI platform for small businesses, run from a two-machine homelab (Minisforum X1 Pro 370 control plane + NVIDIA DGX Spark compute), exposed at <b>newfire.app</b>.</div>
<br>
<div><b>Launch target:</b> May 1, 2026.</div>
<br>
<div><b>Live as of 2026-04-20</b></div>
<ul>
<li>Domain: newfire.app (Cloudflare edge). newfire.ai is NOT in use.</li>
<li>4 real client companies in DB: Atlanta Auto Shine AI, Beulah Automations, LedgerLeads AI, Eternal Lens AI.</li>
<li>8 conversations total. Real usage is light but live.</li>
</ul>
<br>
<div><b>The pitch in one sentence</b></div>
<div>NewFire gives a small business a private team of AI agents (lead gen, content, scheduling, intake) running on dedicated hardware they do not have to operate.</div>
<br>
<div><b>Pilot tier</b></div>
<ul>
<li>Standard: most clients. Local + OpenRouter smart routing.</li>
<li>Privacy tier: Funmi (immigration lawyer). Local-only, encrypted, audit trail, no auto-send. See Architecture &gt; Funmi Privacy Posture.</li>
</ul>
<br>
<div><b>Why this matters:</b> proves a one-person founder can run a real AI product on owned hardware with cloud only as overflow.</div>"""),

    # ---------- 02 Architecture ----------
    ("02 Architecture", "Homelab Map (Minisforum + DGX Spark)",
     """<div><b>Two machines, one platform.</b></div>
<br>
<div><b>Minisforum X1 Pro 370</b> (Control Plane, Tailscale 100.79.80.119)</div>
<ul>
<li>OpenClaw gateway :18789 (orchestration, model routing, fallback)</li>
<li>OpenCode :3002 (coding agent, points at DGX GPU)</li>
<li>APISIX 3.15 :9080 (API auth, rate limiting, metering)</li>
<li>Ollama CPU :11434 (small models)</li>
<li>Prometheus :9090, Grafana :3003</li>
<li>newfire-backend (Express) on 127.0.0.1:3200 (NOT containerized, single point of failure)</li>
<li>newfire-app (React) container :4000 (nginx)</li>
<li>UFW + fail2ban active. Users: newwaveclaw, openclaw (UID 999)</li>
</ul>
<br>
<div><b>NVIDIA DGX Spark</b> (Compute Engine, Tailscale 100.88.112.5)</div>
<ul>
<li>OpenHands :3000 (GPU autonomous agent)</li>
<li>NemoClaw v0.0.6 sandbox</li>
<li>Ollama GPU :11434 (deepseek-r1, glm4, gemma)</li>
<li>Whisper :9000 (speech-to-text)</li>
<li>Qdrant (vector DB, funmi_legal collection)</li>
<li>User: newwave-dgx. SSH user across both: newwaveclaw.</li>
</ul>
<br>
<div><b>Cloud overflow</b></div>
<div>OpenRouter (Claude Sonnet 4.5, DeepSeek R1, MiniMax M2.7, Nemotron Nano free).</div>
<br>
<div><b>Network</b></div>
<ul>
<li>Tailscale between both machines.</li>
<li>Cloudflared tunnel for public ingress on newfire.app and *.newfire.app first-level wildcard.</li>
<li>zrok2 + OpenZiti self-hosted on Minisforum.</li>
</ul>"""),

    ("02 Architecture", "Backend Service (smart routing)",
     """<div><b>Single backend coordinates everything.</b> No localStorage hacks, no bypassing OpenClaw, no hardcoded users.</div>
<br>
<div><b>Pipeline</b></div>
<ol>
<li>User signs up (real Postgres account)</li>
<li>Onboarding interview (AI asks about their business)</li>
<li>Backend parses agent recommendations</li>
<li>Backend provisions: Paperclip company + OpenClaw workers + APISIX consumer + NemoClaw sandbox</li>
<li>Dashboard renders real agents</li>
<li>Chat routes through OpenClaw (orchestration, fallback, budget tracking)</li>
<li>Paperclip tracks usage, costs, audit</li>
</ol>
<br>
<div><b>Smart routing (OpenClaw decides)</b></div>
<ul>
<li>Simple tasks (content, Q&amp;A) to Ollama local: gemma4:26b or glm4:9b (free)</li>
<li>Complex agentic to OpenHands or OpenCode in NemoClaw sandbox: minimax-m2.7 via OpenRouter ($0.30 / $1.20 per M)</li>
<li>Coding tasks to OpenCode worker: minimax-m2.7</li>
<li>Frontier reasoning (legal, high-stakes) to OpenRouter GLM-5.1 ($0.95 / $3.15 per M)</li>
<li>Embeddings to nomic-embed-text (local, free)</li>
<li>Voice to Whisper medium (local Docker on DGX :9000, free)</li>
</ul>
<br>
<div><b>Services coordinated</b></div>
<div>Paperclip :3100, OpenClaw :18789, OpenCode :3002, OpenHands :3000, NemoClaw gRPC :8080, APISIX :9080, Ollama :11434, Whisper :9000.</div>"""),

    ("02 Architecture", "NSS Sandbox Service (dev.newfire.app)",
     """<div><b>What:</b> NewFire Sandbox Service, the self-hosted Daytona-equivalent at <b>dev.newfire.app</b>. Gives developers ephemeral GPU-capable sandboxes on the DGX Spark.</div>
<div><b>Why not fork Daytona:</b> AGPL-3.0 would compel publishing all NewFire source. Clean re-implementation in Node keeps NewFire proprietary and trims 11 services to about 4.</div>
<br>
<div><b>Locked decisions (2026-04-28)</b></div>
<ol>
<li><b>Two repos, not monorepo.</b> newfire-nss-control (Minisforum :3300) + newfire-nss-runner (DGX :3301).</li>
<li><b>Separate dev-portal auth.</b> Standalone dev_users table, own JWT signing key, invite-only for v1.</li>
<li><b>DNS:</b> wildcard *.newfire.app via Cloudflare tunnel. Pattern: sbx-{id}-{port}.newfire.app. Free Universal SSL on first-level only; second-level wildcard needs ACM ($10 per month) and user declined 2026-04-28.</li>
<li><b>Default image:</b> nss/sandbox:ubuntu-22.04-cuda12 (python 3.11, node 20, cuda 12, openssh-server, git).</li>
<li><b>OpenHands integration:</b> custom runtime adapter, about 200 lines Python in a third repo openhands-nss-runtime.</li>
</ol>
<br>
<div><b>Build order (7 PRs)</b></div>
<ol>
<li>DNS + wildcard cert. <b>DONE 2026-04-28</b></li>
<li>DB schema + control-plane skeleton. <b>DONE 2026-04-28</b> (6 nss_* tables, 14 of 14 smoke tests pass)</li>
<li>Runner agent on DGX. NEXT.</li>
<li>NSS dev-portal UI + dev.newfire.app cutover.</li>
<li>Preview-URL routing.</li>
<li>Exec + files API.</li>
<li>OpenHands NewFire runtime.</li>
</ol>"""),

    ("02 Architecture", "Live Platform State (verified 2026-04-20)",
     """<div><b>This corrects older docs.</b> Observed from production DB and deployed code, not from memory or plans.</div>
<br>
<div><b>Domain</b></div>
<ul>
<li>newfire.app is live (Cloudflare 104.21.68.193)</li>
<li>newfire.ai is NOT in use. Any config mentioning it is wrong.</li>
</ul>
<br>
<div><b>Frontend</b></div>
<div>Source: ~/newfire-app/ (React 19 + Vite + Tailwind + react-router-dom). Built output served by Cloudflare + newfire-app container :4000.</div>
<br>
<div><b>Backend</b></div>
<div>Source: ~/newfire-backend/ (Express + Postgres). Runs as a host process on Minisforum 127.0.0.1:3200. JWT auth with roles: user, client, Developer, admin.</div>
<br>
<div><b>Companies live (4)</b></div>
<ol>
<li>Atlanta Auto Shine AI (mobile detailing): Lead Responder, Schedule Master, Follow-Up Pro</li>
<li>Beulah Automations (jewelry): Instagram Trend Scout, WhatsApp Concierge, Visual Storyteller</li>
<li>LedgerLeads AI (bookkeeping): Instagram Prospector, Outreach Specialist, Conversion Assistant</li>
<li>Eternal Lens AI (wedding photography): Lead Responder, Booking Coordinator, Gallery Concierge</li>
</ol>
<br>
<div><b>Active users</b></div>
<div>John (Atlanta Auto Shine), Tolu (Beulah), Pat (LedgerLeads), testrun (Eternal Lens). 8 conversations total, light but live usage.</div>
<br>
<div><b>Stale assumptions corrected</b></div>
<ul>
<li>Sherifah's old signup row deleted 2026-04-21; she re-registers fresh at deployment.</li>
<li>Funmi is NOT in DB. Expected as future client with strict privacy posture.</li>
<li>Model routing is keyword-based in orchestrator.js classifyAgentModel(), not the 4-tier fallback older docs implied.</li>
</ul>"""),

    ("02 Architecture", "8-Layer Gap Map",
     """<div>What is built, what is partial, what is missing. Maps the 8-layer framework onto this homelab (2026-04-20).</div>
<br>
<div><b>Status by layer</b></div>
<ol>
<li><b>Fundamentals.</b> Covered, conceptual only.</li>
<li><b>Data.</b> BIGGEST GAP. Embedding done (nomic-embed-text). Vector DB now done (Qdrant on DGX, funmi_legal seeded 2026-04-20). Knowledge DB still missing.</li>
<li><b>Intelligence Layer.</b> Partial. System prompts done. Persistent memory missing. Multimodal: Whisper done, no image or video. Guardrails (Warden) not deployed.</li>
<li><b>Models and Providers.</b> Strongest layer. Ollama local + OpenRouter cloud + OpenClaw smart routing all done.</li>
<li><b>Infrastructure and Connectivity.</b> Partial. APISIX done, function calling done. Webhooks missing. MCP missing. Client SDK missing.</li>
<li><b>Agents and Automation.</b> Partial. Orchestration done. Multi-agent workflow planned. HITL missing (Funmi compliance risk).</li>
<li><b>No-Code Builder Tools.</b> SECOND BIGGEST GAP. Nothing deployed. Clients cannot self-serve workflows.</li>
<li><b>Business Layer.</b> Partial. Use case + AI stack + strategy done. ROI dashboard missing. Prompt versioning missing. AI avatars missing.</li>
</ol>
<br>
<div><b>Priority order to fix</b></div>
<ol>
<li>Vector DB + RAG (unblocks Funmi). DONE 2026-04-20.</li>
<li>No-code workflow builder (unblocks client self-serve).</li>
<li>Webhooks layer.</li>
<li>HITL approval queue.</li>
<li>Persistent memory.</li>
<li>ROI dashboard (Grafana).</li>
<li>MCP server.</li>
<li>AI avatars.</li>
</ol>"""),

    ("02 Architecture", "Funmi Privacy Posture",
     """<div><b>Why this is stricter than other tenants:</b> Funmi is an immigration lawyer. Her corpus contains attorney-client privileged material, PII, immigration status, asylum details. A leak can harm real people.</div>
<br>
<div><b>Requirements when Funmi onboarding becomes real</b></div>
<ol>
<li><b>Qdrant collection funmi_legal:</b> encrypted at rest, no backups off DGX without encrypted tunnel.</li>
<li><b>Tenant scoping:</b> only Funmi's agents can call rag_search against funmi_legal. Enforced in MCP server, not prompt discipline.</li>
<li><b>Model routing:</b> any prompt that includes retrieved funmi_legal content stays local (Ollama on DGX). No OpenRouter, even with no-train policies.</li>
<li><b>Logging:</b> never log retrieved document content. Retrieval IDs and scores only. Redact error traces before they leave DGX.</li>
<li><b>Drafts:</b> AI legal drafts carry a disclaimer footer and are flagged HUMAN_NEEDED for any final-action step. No auto-send.</li>
<li><b>Backups:</b> encrypted restic repo with key NOT stored on either host (Keychain or offline).</li>
<li><b>Deletion:</b> one-command tenant purge (Qdrant, chat history, API keys, logs, backups). Legal obligation, not optional.</li>
<li><b>Retention:</b> default chat history 30 days unless she opts longer.</li>
<li><b>Audit trail:</b> every funmi_legal access writes an audit row (who, when, what), admin-only visibility.</li>
<li><b>When in doubt, route to Funmi the human, not a model.</b></li>
</ol>"""),

    # ---------- 03 Active Projects ----------
    ("03 Active Projects", "How to use Active Projects",
     """<div><b>One note per in-flight project.</b> Architecture notes describe the system; these notes describe the work.</div>
<br>
<div><b>Template for a new project note</b></div>
<ul>
<li><b>Status:</b> NOT STARTED / IN PROGRESS / BLOCKED / DONE</li>
<li><b>Why now:</b> one sentence.</li>
<li><b>Definition of done:</b> what proves it works.</li>
<li><b>Next concrete step:</b> the single thing to do next.</li>
<li><b>Open blockers:</b> what is in the way.</li>
<li><b>Log:</b> short dated entries at the bottom (newest on top).</li>
</ul>
<br>
<div><b>Candidate notes to add</b> (when each becomes active)</div>
<ul>
<li>May 1 Launch Punch List</li>
<li>OpenClaw v1 Build</li>
<li>NSS PR 3 (Runner agent on DGX)</li>
<li>No-Code Builder Pick</li>
<li>Sherifah Onboarding Recovery</li>
</ul>
<br>
<div><i>Architecture in 02 stays stable. This folder churns.</i></div>"""),

    # ---------- 04 Daily Log ----------
    ("04 Daily Log", "How to use Daily Log",
     """<div><b>One note per day.</b> Title format: YYYY-MM-DD. Newest entries live at the top of the note.</div>
<br>
<div><b>Structure each day</b></div>
<ul>
<li><b>Single Most Productive Move:</b> the one thing that matters most today.</li>
<li><b>Deep Work block(s) planned:</b> which domain, which window (07:00 to 10:00 or 21:00 to 24:00 ET).</li>
<li><b>Wins:</b> what shipped.</li>
<li><b>Snags:</b> what blocked.</li>
<li><b>Sanguine flags:</b> reactive requests that should not have eaten time.</li>
</ul>
<br>
<div><b>Sunday rollup:</b> read the past 7 daily notes, write a Battle Map for the coming week, file it here as a YYYY-Www-battlemap note.</div>"""),

    # ---------- 05 Decisions ----------
    ("05 Decisions", "How to use Decisions",
     """<div><b>One note per decision worth remembering.</b> Architecture and active projects describe the present; this folder explains why the present looks the way it does.</div>
<br>
<div><b>Template</b></div>
<ul>
<li><b>Date:</b> YYYY-MM-DD</li>
<li><b>Decision:</b> one sentence.</li>
<li><b>Context:</b> what was true when this was decided.</li>
<li><b>Options considered:</b> the alternatives and why they lost.</li>
<li><b>Why this won:</b> the reason that mattered most.</li>
<li><b>Reversal cost:</b> easy / medium / hard to undo.</li>
<li><b>Revisit if:</b> the condition that would invalidate it.</li>
</ul>
<br>
<div><b>Decisions worth back-filling soon</b></div>
<ul>
<li>Why newfire.app, not newfire.ai (domain pivot)</li>
<li>Why two repos for NSS, not a monorepo</li>
<li>Why a clean Daytona re-implementation, not a fork</li>
<li>Why separate dev-portal auth from newfire.app JWT</li>
<li>Why first-level wildcard, not paying for ACM</li>
</ul>"""),
]


def osa(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True)


def ensure_parent_folder():
    script = f'''
    tell application "Notes"
        tell account "{ACCOUNT}"
            if not (exists folder "{PARENT}") then
                make new folder with properties {{name:"{PARENT}"}}
            end if
        end tell
    end tell
    '''
    return osa(script)


def ensure_subfolder(name: str):
    script = f'''
    tell application "Notes"
        tell account "{ACCOUNT}"
            tell folder "{PARENT}"
                if not (exists folder "{name}") then
                    make new folder with properties {{name:"{name}"}}
                end if
            end tell
        end tell
    end tell
    '''
    return osa(script)


def escape_for_applescript(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def ensure_note(folder: str, title: str, body_html: str):
    # Body uses HTML; first line becomes title in Notes if name is not set.
    # We set name explicitly and prepend <h1> title in body for clarity.
    full_body = f"<h1>{title}</h1>\n{body_html}"
    body_esc = escape_for_applescript(full_body)
    title_esc = escape_for_applescript(title)
    script = f'''
    tell application "Notes"
        tell account "{ACCOUNT}"
            tell folder "{PARENT}"
                tell folder "{folder}"
                    if not (exists note named "{title_esc}") then
                        make new note with properties {{name:"{title_esc}", body:"{body_esc}"}}
                    end if
                end tell
            end tell
        end tell
    end tell
    '''
    return osa(script)


def main():
    print(f"Bootstrapping NewFire second brain in Apple Notes account: {ACCOUNT}")
    print()

    r = ensure_parent_folder()
    if r.returncode != 0:
        print(f"FAIL parent folder: {r.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"[ok] parent folder: {PARENT}")

    for f in FOLDERS:
        r = ensure_subfolder(f)
        if r.returncode != 0:
            print(f"FAIL subfolder {f}: {r.stderr}", file=sys.stderr)
            continue
        print(f"[ok] subfolder: {f}")

    print()
    for folder, title, body in NOTES:
        r = ensure_note(folder, title, body)
        if r.returncode != 0:
            print(f"FAIL note {folder} / {title}: {r.stderr}", file=sys.stderr)
            continue
        print(f"[ok] note: {folder} / {title}")

    print()
    print("Done. Open Notes and check the NewFire folder.")


if __name__ == "__main__":
    main()
