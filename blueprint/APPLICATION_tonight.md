# Tonight's Application: Joba as the First Pilot

Written 2026-04-20. Companion to `BLUEPRINT.md`. The goal is ONE agent live for Joba before morning, not all five.

## The three roles (the product)

| Role | Primary bottleneck (hypothesis) | Sacred / human-only |
|------|---------------------------------|---------------------|
| M.S. student (UMES, blue catfish thesis) | Literature review, advisor comms, course deadlines | Research direction, ethical calls, advisor trust |
| Residence Life staff | Resident issues, incident reports, staff comms | Pastoral care, crisis response, discipline |
| BCF president | Weekly announcements, agenda prep, member follow-up | Prayer, counseling, spiritual leadership |

## The ruthless scope for tonight

**One agent, one trigger, one action, human approval gate.**

Based on the blueprint's 5-agent model, Agent 2 (AI PR) is the highest-leverage first deploy because communication is the tax across all three of Joba's roles. It drafts, Joba approves, Joba sends.

## The one-night pipeline

```
Inbound email (school + BSF)
    -> classify (student / Res Life / BSF / other)
    -> extract intent (question, request, FYI, scheduling)
    -> pull context from RAG (past replies, SOPs, thesis notes)
    -> draft reply in Joba's voice
    -> land in "Drafts: Review" folder
    -> Joba reads, approves, sends
```

n8n runs the flow. Paperclip agent drafts. Qdrant holds Joba's past-reply corpus. Human-in-the-loop is enforced by the Drafts folder.

## Data layer tonight

Minimum viable corpus for the voice agent:
- Last 90 days of sent mail (school + personal Gmail)
- BSF WhatsApp / announcement archive if exportable
- Res Life SOPs and templates if any exist

These get chunked, embedded with `nomic-embed-text`, loaded into a new Qdrant collection `joba_voice`.

## Intelligence layer tonight

Three system prompts, one per role, all with the same voice rules block.

Voice rules block will be extracted from the sent-mail corpus using the blueprint's voice-replication prompt (see `BLUEPRINT.md` Part 2 Step 5).

Hard guardrails:
- Never send, only draft
- Never draft to thesis advisor without explicit flag
- Never draft pastoral / prayer requests (route to Joba with "HUMAN NEEDED" tag)
- Never draft Res Life disciplinary content

## Infra tonight

- Trigger: Gmail IMAP polling from n8n every 5 min (school + personal)
- Orchestration: n8n workflow "Joba Inbound Triage"
- Drafting: HTTP node -> Paperclip agent `joba-pr` -> returns draft JSON
- RAG: Paperclip agent calls Qdrant `joba_voice` via the MCP tool from tonight's push
- Output: Gmail draft creation API (draft only, never send)

## Open questions for Joba before we build

Answer these fast, I will fill defaults for anything left blank.

1. Which Gmail accounts should the pipe watch tonight? (school umes.edu, personal, BSF shared) bmalomo@umes.edu
2. Do you have IMAP enabled on the school account, or only OAuth? I am not sure
3. Do you have a sent-mail export handy, or do we pull live via IMAP? You can pull via imap
4. Is there a shared Res Life inbox, or is it all in your personal? i have my own account and there is a reslife folder that has all our documents
5. Confirm the three "never draft" categories above, or edit: - Never send, only draft, - Never draft pastoral / prayer requests (route to Joba with "HUMAN NEEDED" tag)
- Never draft Res Life disciplinary content
6. Midnight go/no-go signal: what has to be working for you to call tonight a win? (my suggested bar: at least one inbound email from today drafted and sitting in your Drafts folder, in your voice, with correct role classification) yes that will be good.

## If tonight works, tomorrow's ritual

17 minutes in the morning, every day:
1. Open Drafts folder, approve or edit the overnight batch (about 10 min)
2. Open dashboard, look at yesterday's audit line (tasks done, automatable vs human-essential) (about 5 min)
3. Flag one task today for Agent 3 (Delegator) to SOP (about 2 min)

## Week 2 onward (after tonight's proof)

Agent 1 (Strategist): advisor meeting prep, thesis literature synthesis, Res Life decision matrices
Agent 3 (Delegator): screen-capture SOP flow for Res Life routines
Agent 4 (Operator): auto-route forms to the right folder, nudge members who missed BSF meeting
Agent 5 (Content Flywheel): one thought per week expanded into LinkedIn + newsletter for the thesis area

The five agents map to the three roles like this:

|             | Student | Res Life | BSF |
|-------------|---------|----------|-----|
| Strategist  | advisor prep, lit review | incident triage | event planning |
| PR (tonight)| email drafts | email drafts | announcements |
| Delegator   | research SOP | shift SOP | exec team SOP |
| Operator    | deadline nudges | form routing | member follow-up |
| Content     | thesis thought-leadership | n/a | devotional repurpose |
