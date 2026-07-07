"""Webhook service — the generic inbound trigger the legal tenant didn't have.

Every agent in this tenant used to run only when a human invoked it directly.
There was no way for an external event — a new client email, a website
contact-form submission, a CRM webhook — to reach an agent at all. This
service is that missing front door: any vendor a firm actually uses (Gmail
push notifications, Typeform, a CRM's webhook feature, whatever) can be
pointed at `POST /webhooks/{tenant_id}/{source}` once it's configured to sign
its requests, and a separate poller (`shared/process_webhook_events.py`)
picks up queued events and feeds them into the right agent. This service
doesn't know or care which vendor sent the event, or what agent eventually
consumes it — it only verifies, stores, and queues.

Because this endpoint is meant to be reachable from the public internet, the
signature check is the whole safety story: every request must carry an
X-Webhook-Signature header (HMAC-SHA256 over the raw body, keyed by a secret
issued per tenant at onboarding). No signature, wrong signature, no record.

Swappable like the rest of this tenant: point STORE_PATH at a real database
and nothing calling this service needs to change.
"""

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request

STORE_PATH = os.path.join(os.path.dirname(__file__), "webhook_events.json")
SECRETS_PATH = os.environ.get(
    "WEBHOOK_SECRETS_PATH", os.path.join(os.path.dirname(__file__), "webhook_secrets.json")
)

app = FastAPI(title="Webhook Service")


def get_secret(tenant_id: str) -> str | None:
    if not os.path.exists(SECRETS_PATH):
        return None
    with open(SECRETS_PATH, encoding="utf-8") as f:
        secrets = json.load(f)
    return secrets.get(tenant_id)


def _verify_signature(secret: str, raw_body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    # Timing-attack-safe comparison — this endpoint is public-facing, so a
    # naive `==` here would leak how many leading bytes matched.
    return hmac.compare_digest(expected, signature)


def _load() -> dict[str, dict]:
    if not os.path.exists(STORE_PATH):
        return {}
    with open(STORE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save(events: dict[str, dict]) -> None:
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)


@app.post("/webhooks/{tenant_id}/{source}", status_code=202)
async def receive_webhook(tenant_id: str, source: str, request: Request) -> dict:
    raw_body = await request.body()

    secret = get_secret(tenant_id)
    if secret is None:
        raise HTTPException(status_code=401, detail="unknown tenant")

    signature = request.headers.get("X-Webhook-Signature")
    if not _verify_signature(secret, raw_body, signature):
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        payload = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="body is not valid JSON")

    events = _load()
    record = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "source": source,
        "payload": payload,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "processed": False,
    }
    events[record["id"]] = record
    _save(events)

    # Best-effort — a firm's whole webhook layer shouldn't go down because
    # activity_log_service is unreachable.
    try:
        from activity_log_service.client import log_event

        log_event("webhook_received", "low", f"New {source} event received for {tenant_id}")
    except Exception:
        pass

    return record


@app.get("/events/pending")
def get_pending_events(tenant_id: str | None = None, source: str | None = None) -> list[dict]:
    events = _load()
    results = [e for e in events.values() if not e["processed"]]
    if tenant_id is not None:
        results = [e for e in results if e["tenant_id"] == tenant_id]
    if source is not None:
        results = [e for e in results if e["source"] == source]
    return results


@app.get("/events/{event_id}")
def get_event(event_id: str) -> dict:
    events = _load()
    record = events.get(event_id)
    if record is None:
        raise HTTPException(status_code=404, detail="event not found")
    return record


@app.post("/events/{event_id}/mark_processed")
def mark_event_processed(event_id: str) -> dict:
    events = _load()
    record = events.get(event_id)
    if record is None:
        raise HTTPException(status_code=404, detail="event not found")
    if record["processed"]:
        raise HTTPException(status_code=409, detail="event already processed")

    record["processed"] = True
    events[event_id] = record
    _save(events)
    return record


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
