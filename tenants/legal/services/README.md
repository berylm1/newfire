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

**Webhook Service** (`webhook_service/`, default port 8005)
Owns the generic inbound trigger for this tenant — the front door for
external events (a new client email, a website contact-form submission, a
CRM webhook) reaching an agent without a human invoking it directly.
`POST /webhooks/{tenant_id}/{source}` verifies an HMAC signature and queues
the event, `GET /events/pending` lists what's waiting. A separate poller
(`shared/process_webhook_events.py`) polls for `source="email"` events and
feeds them into the intake/conflict-check agent. See
`webhook_service/README.md` for details.

**Memory Service** (`memory_service/`, default port 8006)
Owns cross-session note history so an agent isn't starting cold every time it
sees a party it may have seen before. `POST /memory/{tenant_id}/notes`
(`client_key` in the body) to append a note, `GET /memory/{tenant_id}?
client_key=...` to read a client's note history (an empty list, not a 404,
if there's none yet) — `client_key` stays out of the URL path since party
and company names routinely contain `/` (`"d/b/a"` constructs). `client_key`
is whatever string the caller sends (typically a party name from an intake
email) — matched exactly, no fuzzy name matching or dedup. `intake_conflict_check`'s
`recall_node` reads this before drafting a memo; `resume_approvals.py` writes
to it after a human decides. See `memory_service/README.md` for details.

**Case Service** (`case_service/`, default port 8007)
Owns the client/case record — the structured foundation the tenant didn't
have before. `POST /cases` to create one, `GET /cases/{tenant_id}` to list
a tenant's cases, `GET /cases/{tenant_id}/{case_id}` to fetch one, `PATCH
/cases/{tenant_id}/{case_id}` for a partial update (dict fields like
`key_dates` and `fee_status` merge instead of replacing wholesale). `daily_briefing`
reads this for its docket instead of the old hardcoded sample file. See
`case_service/README.md` for details.

**Notify Service** (`notify_service/`, default port 8008)
Owns generic outbound delivery — the mirror image of `webhook_service`.
`POST /notify` to send a message via a named channel (`email` or
`whatsapp`), `GET /notify/log` to see what's gone out. Not wired to a real
SMTP/WhatsApp provider yet — the backend is a local stub that records what
would have been sent. `daily_briefing` calls this to deliver the drafted
briefing. See `notify_service/README.md` for details.

**Client Hub Service** (`client_hub_service/`, default port 8009)
Owns the centralized client-facing view — composes `case_service` and
`notify_service` rather than owning its own storage. `GET
/hub/{tenant_id}` lists a tenant's cases with an added
`outstanding_balance` field (who's paid, who hasn't). `POST
/hub/{tenant_id}/{case_id}/email` sends an email to that client via
`notify_service` and logs the send to `activity_log_service`. See
`client_hub_service/README.md` for details.

**Visa Bulletin Service** (`visa_bulletin_service/`, default port 8010)
Owns the real monthly Visa Bulletin data — fetches and parses the actual
PDF from travel.state.gov (the HTML page is behind a Cloudflare bot-check
a plain HTTP client can't pass; the PDF asset path isn't). `GET
/bulletin/current` returns the parsed Final Action Dates tables
(family-sponsored and employment-based), cached and only re-fetched when
the cache isn't for a plausible current month. `POST /check` compares a
category/country/priority-date against it. The only service in this
tenant that needs outbound internet access — see
`visa_bulletin_service/README.md` for details, including how the PDF
parser handles multi-line category labels and page-break boilerplate.

All ten are swappable the same way the rest of this tenant is: point the
storage inside `main.py` (or `backends.py`, for `notify_service`) at a real
database or provider and nothing calling the service needs to change.

## Running locally

```
pip install -r requirements.txt
uvicorn activity_log_service.main:app --port 8001 &
uvicorn conflicts_service.main:app --port 8002 &
uvicorn rag_service.main:app --port 8003 &
uvicorn approval_service.main:app --port 8004 &
uvicorn webhook_service.main:app --port 8005 &
uvicorn memory_service.main:app --port 8006 &
uvicorn case_service.main:app --port 8007 &
uvicorn notify_service.main:app --port 8008 &
uvicorn client_hub_service.main:app --port 8009 &
uvicorn visa_bulletin_service.main:app --port 8010 &
```

Agents pick these up automatically via `ACTIVITY_LOG_SERVICE_URL` /
`CONFLICTS_SERVICE_URL` / `RAG_SERVICE_URL` / `APPROVAL_SERVICE_URL` /
`WEBHOOK_SERVICE_URL` / `MEMORY_SERVICE_URL` / `CASE_SERVICE_URL` /
`NOTIFY_SERVICE_URL` / `CLIENT_HUB_SERVICE_URL` / `VISA_BULLETIN_SERVICE_URL`
(default to `http://localhost:8001` / `http://localhost:8002` /
`http://localhost:8003` / `http://localhost:8004` / `http://localhost:8005`
/ `http://localhost:8006` / `http://localhost:8007` / `http://localhost:8008`
/ `http://localhost:8009` / `http://localhost:8010`). No code changes
needed in the agents beyond importing `client.py` from each service
instead of the old shared modules.

In production, the first six run as systemd services on the gateway box
(`legal-activity-log` on 8101, `legal-conflicts` on 8102, `legal-rag` on
8103, `legal-approval` on 8104, `legal-webhook` on 8105, `legal-memory` on
8106), each bound to `127.0.0.1` only. `case_service`, `notify_service`,
`client_hub_service`, and `visa_bulletin_service` follow the same
8107/8108/8109/8110 numbering but aren't deployed yet — this round is
local-only. `visa_bulletin_service` would need real outbound internet
access when it is deployed, unlike the loopback-only services around it.
