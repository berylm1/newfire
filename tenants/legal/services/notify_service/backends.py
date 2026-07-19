"""Delivery backends for the Notify service.

Swappable interface, same convention as `conflicts_service`'s synthetic data
and the old `docket_feed.py`'s synthetic docket: `send` is the one function a
real integration replaces, and nothing calling this module needs to change
when that happens. No firm has a real SMTP account or WhatsApp Business API
credential wired up yet, so the default backend is a local stub which durably
records what *would* have been sent instead of calling anything external. That's
intentional for this round, not an oversight — it makes the service fully
testable today and gives a real integration point for later.

Production deployments should set NOTIFY_CHANNEL=smtp (or smtp+whatsapp)
along with SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD to enable the real
SMTP backend. The stub backend remains the fallback when SMTP is not configured.
"""

import json
import logging
import os
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SENT_LOG_PATH = os.path.join(os.path.dirname(__file__), "sent_log.json")

# SMTP configuration (production-ready when env vars are set)
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)
NOTIFY_CHANNEL = os.environ.get("NOTIFY_CHANNEL", "stub")


def _is_smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def _load_log() -> list[dict]:
    if not os.path.exists(SENT_LOG_PATH):
        return []
    with open(SENT_LOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_log(entries: list[dict]) -> None:
    with open(SENT_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def _log_entry(entry: dict) -> None:
    entries = _load_log()
    entries.append(entry)
    _save_log(entries)


def _send_smtp(to: str, subject: str | None, body: str) -> None:
    """Send email via SMTP. Raises smtplib.SMTPException on failure."""
    msg = MIMEText(body)
    msg["Subject"] = subject or "(no subject)"
    msg["From"] = SMTP_FROM
    msg["To"] = to

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


def send(tenant_id: str, channel: str, to: str, subject: str | None, body: str) -> dict:
    """Send a notification via the configured backend(s).

    Routes to SMTP for email channel when configured, falls back to the
    local stub otherwise. WhatsApp channel always uses the stub today
    (WhatsApp Business API integration deferred).
    """
    entry = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "channel": channel,
        "to": to,
        "subject": subject,
        "body": body,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        if channel == "email" and _is_smtp_configured() and "smtp" in NOTIFY_CHANNEL:
            _send_smtp(to, subject, body)
            entry["status"] = "sent"
            entry["backend"] = "smtp"
            logger.info("Sent email to %s via SMTP", to)
        else:
            entry["status"] = "sent"
            entry["backend"] = "stub"
            logger.info("Stub delivery: %s to %s via %s", subject, to, channel)
    except Exception as exc:
        entry["status"] = "failed"
        entry["error"] = str(exc)
        logger.error("Delivery failed for %s: %s", entry["id"], exc)

    _log_entry(entry)
    return entry


def get_log() -> list[dict]:
    return _load_log()
