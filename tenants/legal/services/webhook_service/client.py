"""Client for the Webhook service — thin HTTP wrapper for the consuming side.

This is for whatever polls the queue (`shared/process_webhook_events.py`),
not for sending webhooks — the producing side is an external system (a
firm's email provider, form tool, CRM) POSTing directly to
`/webhooks/{tenant_id}/{source}` with a signature it computes itself. The one
piece worth sharing is `sign_payload`, so callers and tests can construct a
validly-signed request the same way a real sender would.
"""

import hashlib
import hmac
import os

import requests

BASE_URL = os.environ.get("WEBHOOK_SERVICE_URL", "http://localhost:8005")


def sign_payload(secret: str, raw_body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def get_pending_events(tenant_id: str | None = None, source: str | None = None) -> list[dict]:
    params = {}
    if tenant_id is not None:
        params["tenant_id"] = tenant_id
    if source is not None:
        params["source"] = source
    response = requests.get(f"{BASE_URL}/events/pending", params=params, timeout=5)
    response.raise_for_status()
    return response.json()


def get_event(event_id: str) -> dict:
    response = requests.get(f"{BASE_URL}/events/{event_id}", timeout=5)
    response.raise_for_status()
    return response.json()


def mark_event_processed(event_id: str) -> dict:
    response = requests.post(f"{BASE_URL}/events/{event_id}/mark_processed", timeout=5)
    response.raise_for_status()
    return response.json()
