#!/usr/bin/env python3
"""Feed queued webhook events into the intake/conflict-check agent.

webhook_service has no idea what an "email" event is for — it just verifies,
stores, and queues whatever a signed request sends. This script is the
piece that gives `source="email"` events somewhere to go: it polls `GET
/events/pending?source=email` for the legal tenant, and for each one, writes
the event's body text out to a temp file and invokes
`intake_conflict_check/run.py --email <tmpfile>` as a subprocess — the same
entry point a human runs by hand today, just triggered by a queued event
instead of a person.

Expected payload shape for `source="email"` events (whatever sent the
webhook is responsible for producing this, e.g. a small relay in front of a
firm's actual email provider):
    {"from": "...", "subject": "...", "body": "..."}
Only `body` (falling back to `text`) is used here — `from`/`subject` are
carried along in the payload for whatever future consumer wants them, but
the intake agent today just wants email text to run its extraction on.

An event is marked processed regardless of whether the subprocess succeeds
— one bad email shouldn't wedge the rest of the queue. A subprocess failure
is logged to the activity feed instead of raised, so a human finds out
without the poller crashing mid-run.

One-shot by design — run it by hand, from a cron job, or a systemd timer
(`python3 process_webhook_events.py`). It does not loop or sleep on its own.

In production, both `WEBHOOK_SERVICE_URL` (http://127.0.0.1:8105) and
`ACTIVITY_LOG_SERVICE_URL` (http://127.0.0.1:8101) must be set explicitly —
their client defaults are dev ports, not the offset production ones. Missed
this exact thing once already on webhook_service's own unit; every event
still got queued, but the activity-log call silently no-op'd.
"""

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from webhook_service.client import get_pending_events, mark_event_processed

TENANT_ID = "legal"
RUN_PY = os.path.join(os.path.dirname(__file__), "..", "intake_conflict_check", "run.py")


def _email_body(payload: dict) -> str:
    return payload.get("body") or payload.get("text") or ""


def process_one(event: dict) -> None:
    body = _email_body(event["payload"])

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    try:
        tmp.write(body)
        tmp.close()

        result = subprocess.run([sys.executable, RUN_PY, "--email", tmp.name])
        if result.returncode != 0:
            from activity_log_service.client import log_event

            log_event(
                "webhook_processing_failed",
                "medium",
                f"intake_conflict_check failed processing webhook event {event['id']} (exit code {result.returncode}).",
            )
    finally:
        os.unlink(tmp.name)

    # Marked processed either way — a failed run still needs a human to
    # notice via the activity log, not an infinite retry of the same event.
    mark_event_processed(event["id"])
    print(f"Processed webhook event {event['id']}")


def main() -> None:
    pending = get_pending_events(tenant_id=TENANT_ID, source="email")
    if not pending:
        print("No pending email webhook events.")
        return

    for event in pending:
        process_one(event)


if __name__ == "__main__":
    main()
