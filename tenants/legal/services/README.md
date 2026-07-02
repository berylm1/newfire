# Legal tenant — shared services

Small internal services, split out of code that used to be imported directly
as Python modules across agents. Each agent process now calls these over HTTP
instead of importing `shared/activity_log.py` or
`intake_conflict_check/conflicts_db.py` — a real service boundary instead of
shared-code coupling, and the piece that makes it possible for a
gateway-triggered process (e.g. a WhatsApp handler) to write to the same feed
a CLI-run agent reads from, without needing to share a filesystem or Python
path.

## Services

**Activity Log Service** (`activity_log_service/`, default port 8001)
Owns the day's activity feed. `POST /events` to log something, `GET
/events/today` to read today's feed. This is what the daily briefing agent
reads from.

**Conflicts Service** (`conflicts_service/`, default port 8002)
Owns the conflicts-of-interest lookup. `POST /check` with a list of party
names, returns any matches.

**RAG Service** (`rag_service/`, default port 8003)
Owns document search for the tenant's own case documents and precedent.
`POST /documents` to embed and store a document, `POST /search` to get the
closest matches for a query. Backed by Qdrant, embeddings from the tenant's
self-hosted Ollama instance. See `rag_service/README.md` for details.

**Approval Service** (`approval_service/`, default port 8004)
Owns the human-in-the-loop approval queue for agents that pause on a
`human_approval_interrupt` node (intake conflict-check, citation checker).
`POST /approvals` to submit a draft for review, `GET /approvals/pending` to
list what's waiting, `POST /approvals/{id}/decide` to approve or reject one.
A separate resume script (`shared/resume_approvals.py`) polls `GET
/approvals/resumable` and replays decisions into the paused graph. See
`approval_service/README.md` for details.

All four are swappable the same way the rest of this tenant is: point the
storage inside `main.py` at a real database and nothing calling the service
needs to change.

## Running locally

```
pip install -r requirements.txt
uvicorn activity_log_service.main:app --port 8001 &
uvicorn conflicts_service.main:app --port 8002 &
uvicorn rag_service.main:app --port 8003 &
uvicorn approval_service.main:app --port 8004 &
```

Agents pick these up automatically via `ACTIVITY_LOG_SERVICE_URL` /
`CONFLICTS_SERVICE_URL` / `RAG_SERVICE_URL` / `APPROVAL_SERVICE_URL` (default
to `http://localhost:8001` / `http://localhost:8002` / `http://localhost:8003`
/ `http://localhost:8004`). No code changes needed in the agents beyond
importing `client.py` from each service instead of the old shared modules.

In production, all four run as systemd services on the gateway box
(`legal-activity-log` on 8101, `legal-conflicts` on 8102, `legal-rag` on
8103, `legal-approval` on 8104), each bound to `127.0.0.1` only.
