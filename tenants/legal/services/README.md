# Legal tenant — shared services

Two small internal services, split out of code that used to be imported
directly as Python modules across agents. Each agent process now calls these
over HTTP instead of importing `shared/activity_log.py` or
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

Both are swappable the same way the rest of this tenant is: point the storage
inside `main.py` at a real database and nothing calling the service needs to
change.

## Running locally

```
pip install -r requirements.txt
uvicorn activity_log_service.main:app --port 8001 &
uvicorn conflicts_service.main:app --port 8002 &
```

Agents pick these up automatically via `ACTIVITY_LOG_SERVICE_URL` /
`CONFLICTS_SERVICE_URL` (default to `http://localhost:8001` /
`http://localhost:8002`). No code changes needed in the agents beyond
importing `client.py` from each service instead of the old shared modules.
