# Memory Service

Cross-session note history so an agent isn't starting cold every time it
runs. Before this service, every `intake_conflict_check` run had zero
awareness that it may have seen the same party in some prior, separate run —
each conversation started fresh, no matter how many times a firm had dealt
with the same client or opposing party before. This service is a durable,
append-only note history keyed by `(tenant_id, client_key)` that an agent
reads before it acts and writes to after a human has actually decided
something.

## Name matching is out of scope

`client_key` is whatever string the caller sends — typically a party name
pulled out of an intake email by an LLM extraction step. This service
compares keys for **exact string equality only**. "Marcus Whitfield" and
"M. Whitfield" are different keys here, and always will be; there's no
normalization, fuzzy matching, or dedup. Solving that reliably (aliases,
typos, maiden names, company name changes) is a real, separate problem, and
this service intentionally doesn't attempt it — callers are responsible for
using a consistent key for the same underlying party if they want history to
connect across runs.

This is also not semantic search — that's `rag_service`'s job. This is a
chronological note history, nothing more.

## Endpoints

`POST /memory/{tenant_id}/{client_key}/notes` — body `{"note": str,
"matter_type": str | None, "source": str}`. Appends a note and returns the
created record (`id`, timestamps). Append-only — there's no update or delete
endpoint, because this is a history, not a mutable profile.

`GET /memory/{tenant_id}/{client_key}` — returns `{"client_key", "notes":
[...]}`, all notes for that client in chronological order. Returns an empty
list, not a 404, when the client has no history — a first-time intake is the
common case, not an error, and callers shouldn't need to handle a 404 for it.

`GET /health` — liveness check.

## Storage

JSON file (`memory_notes.json`, same simplicity level as the other
services), keyed by `tenant_id::client_key` so the same `client_key` string
under two different tenants can never leak into each other. Point
`STORE_PATH` at a real database if a firm's note volume ever outgrows it, and
nothing calling this service needs to change.

## Running locally

```
pip install -r requirements.txt
uvicorn memory_service.main:app --port 8006
```

Agents pick this up via `MEMORY_SERVICE_URL` (defaults to
`http://localhost:8006`). Import `client.py` for `add_note` and
`get_client_memory`.

In production this runs as `legal-memory.service` on port 8106, same pattern
as `legal-activity-log` (8101), `legal-conflicts` (8102), `legal-rag` (8103),
`legal-approval` (8104), and `legal-webhook` (8105).
