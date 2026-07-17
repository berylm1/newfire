# Farmer Data Collection v3: Production Readiness Audit

Title: Farmer Data Collection v3 - Production Readiness Audit
Date: 2026-06-23
Tags: openhands, audit, nodejs, express, mongodb, security, testing
Status: in-progress
Repo: https://github.com/berylm1/farmer-data-collection-v3 (private)
Machine: newwaveclaw@america (OpenHands container)
Model: qwen3-coder-30b-64k via Ollama on ghana:11434

Comprehensive production-readiness audit launched via OpenHands agent on 2026-06-23. The OpenHands agent has all four tools enabled (terminal, file_editor, task_tracker, browser_tool_set) and is running autonomously.

## Conversation Details

- Conversation ID: `a675faa1-4536-4d93-93be-c59e5a2e067b`
- Model: `qwen3-coder-30b-64k` via Ollama on ghana:11434
- Workspace: `/workspace/farmer-review` inside openhands-app container
- Repo cloned to: `/workspace/farmer-review/repo`
- AUDIT.md location: `/workspace/farmer-review/AUDIT.md`
- Launch time: 2026-06-23 approx 04:24 UTC

## Repo Stack (discovered from clone)

- Runtime: Node.js + Express 4.18
- Database: MongoDB via Mongoose 6.0
- Auth: JWT via jsonwebtoken 8.5 and bcryptjs
- Security middleware: helmet, cors
- Testing: Jest and Supertest
- Files at clone: 6 total (server.js, models/Farmer.js, controllers/farmerController.js, package.json, README.md, .env)

## Audit Scope

(a) Introspect, research, and understand the codebase

(b) Recommend and fix gaps, missing features, orphan code, and code quality issues

(c) Security audit covering external and internal attack surface; implement all fixes

(d) Performance benchmarking per service vs industry standards; implement all fixes

(e) Extensive E2E, regression, load, QA, chaos, and integration testing; fix all failures

(f) Production readiness and completion scorecard for every service and feature

Browser tool is enabled for live E2E testing of the running application.

## Container Setup (pre-audit)

Go 1.24.4 and Rust 1.96.0 were installed in the OpenHands container before launching the audit.

Go was installed via apt using `docker exec -u root openhands-app apt-get install -y golang-go`.

Rust was installed as the openhands user via rustup using the minimal profile, then the binaries were symlinked into /usr/local/bin so the agent can call `rustc` and `cargo` without sourcing the cargo env file.

Confirmed versions: go1.24.4 linux/amd64, rustc 1.96.0.

## GitHub PAT Secret Injection

The GitHub PAT is stored encrypted in `/var/lib/docker/volumes/openhands-data/_data/secrets.json`. The encryption uses Fernet with a key derived from the file at `/var/lib/docker/volumes/openhands-data/_data/agent-canvas/secret-key.txt`.

To inject the PAT into a conversation, run the decryption + POST on america. The correct `secret_sources` field is a dict mapping env var name to a StaticSecret object with kind and value fields. Using a list instead of a dict silently fails and produces an empty registry with no error.

Example payload shape:

```python
payload = {
    'secrets': {
        'GITHUB_PERSONAL_ACCESS_TOKEN': {
            'kind': 'StaticSecret',
            'value': pat
        }
    }
}
# POST to http://localhost:8000/api/conversations/{CID}/secrets
```

## Initial Findings at Turn 38

Code quality gaps found in the 6 original files:

- server.js has 3 TODO comments including missing DB connection logic
- models/Farmer.js has no field validation
- controllers/farmerController.js has completely empty function bodies
- No authentication middleware on any protected routes
- No error handling and no try-catch blocks anywhere
- No tests exist in the test suite despite Jest being listed as a dev dependency

This is a starter/scaffold codebase. The agent needs to implement most of the functionality rather than patch existing bugs.

## Status Log

2026-06-23 04:24: Conversation created. 0 turns.

2026-06-23 04:27: AUDIT.md scaffolded. 13 turns, 1,336 tokens. PAT not yet injected so clone returned empty scaffold.

2026-06-23 04:29: Real repo cloned after PAT injected via secrets API. 19 turns, 1,624 tokens. 6 real files visible.

2026-06-23 ~04:45: Audit analysis in progress. 38 turns, 10,952 tokens, 959s LLM time.

## Monitor Commands

Check conversation status (run on america):

```bash
curl -s 'http://localhost:8000/api/conversations/a675faa1-4536-4d93-93be-c59e5a2e067b' \
  -H 'X-Session-API-Key: 0a5180831d41062f5e7abf8dd3f2bbb2965d64f48276e2c809eeaf85f5de37ec' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["execution_status"])'
```

Read the audit document:

```bash
docker exec openhands-app cat /workspace/farmer-review/AUDIT.md
```

List all repo files the agent has created or modified:

```bash
docker exec openhands-app find /workspace/farmer-review/repo -type f | grep -v .git | sort
```

## Known OpenHands API Gotchas (discovered during this session)

1. `secret_sources` in the conversation creation payload must be a dict, not a list. A list silently fails and no secrets are injected.

2. The `ask_agent` endpoint is a one-off sidebar question and does not inject a user turn into the running conversation thread.

3. There is no built-in user-message injection into a running conversation. The clean path is to stop and restart with the corrected payload.

4. Secrets can be added to a running conversation after creation via POST to `/api/conversations/{id}/secrets` using the StaticSecret format shown above.
