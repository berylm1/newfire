"""Memory service — owns cross-session note history for the legal tenant's
agents.

Every agent run used to start cold: `intake_conflict_check` had no way to
know it had seen the same prospective client or opposing party in some prior,
separate run, even though a partner reading the same two intakes back to back
would remember instantly. This service is that missing memory — a durable,
append-only note history keyed by `(tenant_id, client_key)` that any agent
can read before it acts and write to after a human has actually decided
something.

This is intentionally not name matching or deduplication: `client_key` is
whatever string the caller sends (typically a party name pulled straight out
of an intake email), compared for exact equality only. "Marcus Whitfield" and
"M. Whitfield" are different keys here. Solving that is a real, separate
problem — this service stores notes under whatever key it's given and trusts
callers to normalize consistently. It's also not semantic search — that's
`rag_service`'s job; this is a chronological note history, nothing more.

Swappable like the rest of this tenant: point STORE_PATH at a real database
and nothing calling this service needs to change.
"""

import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel

STORE_PATH = os.path.join(os.path.dirname(__file__), "memory_notes.json")

app = FastAPI(title="Memory Service")


class NoteIn(BaseModel):
    client_key: str
    note: str
    matter_type: str | None = None
    source: str


def _load() -> dict[str, dict]:
    if not os.path.exists(STORE_PATH):
        return {}
    with open(STORE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save(notes: dict[str, dict]) -> None:
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)


def _key(tenant_id: str, client_key: str) -> str:
    # tenant_id folded into the storage key (not just a field on the record)
    # so the same client_key string under two different tenants can never
    # collide and leak notes across firms.
    return f"{tenant_id}::{client_key}"


@app.post("/memory/{tenant_id}/notes")
def add_note(tenant_id: str, note: NoteIn) -> dict:
    notes = _load()
    key = _key(tenant_id, note.client_key)
    record = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "client_key": note.client_key,
        "note": note.note,
        "matter_type": note.matter_type,
        "source": note.source,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    notes.setdefault(key, []).append(record)
    _save(notes)
    return record


@app.get("/memory/{tenant_id}")
def get_client_memory(tenant_id: str, client_key: str) -> dict:
    # client_key is a query param, not a path segment — party/company names
    # routinely contain "/" (e.g. "d/b/a" constructs), which breaks path
    # routing outright. A query param has no such ambiguity.
    notes = _load()
    key = _key(tenant_id, client_key)
    # No history is the common case (most first-time intakes), not an error —
    # always 200 with an empty list, never 404.
    return {"client_key": client_key, "notes": notes.get(key, [])}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
