"""Delivery backends for the Notify service.

Swappable interface, same convention as `conflicts_service`'s synthetic data
and the old `docket_feed.py`'s synthetic docket: `send` is the one function a
real integration replaces, and nothing calling this module needs to change
when that happens. No firm has a real SMTP account or WhatsApp Business API
credential wired up yet, so the only backend today is this local stub, which
durably records what *would* have been sent instead of calling anything
external. That's intentional for this round, not an oversight — it makes the
service fully testable today and gives a real integration point for later.
"""

import json
import os
import uuid
from datetime import datetime, timezone

SENT_LOG_PATH = os.path.join(os.path.dirname(__file__), "sent_log.json")


def _load_log() -> list[dict]:
    if not os.path.exists(SENT_LOG_PATH):
        return []
    with open(SENT_LOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_log(entries: list[dict]) -> None:
    with open(SENT_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def send(tenant_id: str, channel: str, to: str, subject: str | None, body: str) -> dict:
    """Stub send — appends the attempt to SENT_LOG_PATH and returns it.

    Never calls an external API. Swap this function's body for a real SMTP
    client or WhatsApp-send call later; `main.py` doesn't need to change.
    """
    entry = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "channel": channel,
        "to": to,
        "subject": subject,
        "body": body,
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    entries = _load_log()
    entries.append(entry)
    _save_log(entries)
    return entry


def get_log() -> list[dict]:
    return _load_log()
