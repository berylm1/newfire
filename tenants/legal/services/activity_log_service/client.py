"""Client for the Activity Log service — drop-in replacement for the old
direct import of tenants/legal/shared/activity_log.py.

Same function names and signatures (log_event, get_todays_events) so agents
only need to change their import line, not their calling code.
"""

import os

import requests

BASE_URL = os.environ.get("ACTIVITY_LOG_SERVICE_URL", "http://localhost:8001")


def log_event(event_type: str, urgency: str, summary: str) -> None:
    requests.post(
        f"{BASE_URL}/events",
        json={"event_type": event_type, "urgency": urgency, "summary": summary},
        timeout=5,
    ).raise_for_status()


def get_todays_events() -> list[dict]:
    response = requests.get(f"{BASE_URL}/events/today", timeout=5)
    response.raise_for_status()
    return response.json()
