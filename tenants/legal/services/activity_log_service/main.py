"""Activity Log service — owns the shared feed across the legal tenant's agents.

Pulled out of tenants/legal/shared/activity_log.py, which every agent imported
directly as a Python module. That worked but isn't a real service boundary:
every consumer needed the same filesystem layout, and a process running
somewhere else (a gateway-triggered handler, eventually) couldn't write to it
at all. This is the same log_event / get_todays_events interface, now reachable
over HTTP so any agent — local or remote — can write to and read from one
shared feed without importing this module's internals.

Swappable like the rest of this tenant: point LOG_PATH at a real database and
nothing calling this service needs to change.
"""

import json
import os
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel

LOG_PATH = os.path.join(os.path.dirname(__file__), "activity_log.jsonl")

app = FastAPI(title="Activity Log Service")


class EventIn(BaseModel):
    event_type: str
    urgency: str
    summary: str


@app.post("/events")
def create_event(event: EventIn) -> dict:
    record = {
        "type": event.event_type,
        "urgency": event.urgency,
        "summary": event.summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return record


@app.get("/events/today")
def get_todays_events() -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []

    today = datetime.now(timezone.utc).date().isoformat()
    events = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record["timestamp"].startswith(today):
                events.append(record)

    events.reverse()
    return events


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
