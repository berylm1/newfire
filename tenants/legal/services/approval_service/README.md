# Approval Service

Durable queue standing in for the human who used to sit at a terminal and
answer `input()` when an agent's `human_approval_interrupt` node paused. An
agent submits a draft here and exits; a reviewer decides whenever they get to
it, from any process; a separate resume script (`shared/resume_approvals.py`)
picks up decided approvals and replays the decision into the paused graph.

This service never makes a decision and never touches a graph — it only
remembers what's pending and what was decided.

## Endpoints

`POST /approvals` — body `{"tenant_id", "thread_id", "kind", "draft",
"context"}`, creates a pending approval and returns the full record
(`id`, `status: "pending"`, timestamps).

`GET /approvals/pending?tenant_id=` — list pending approvals, optionally
filtered by tenant.

`GET /approvals/{id}` — fetch one approval by id. 404 if it doesn't exist.

`POST /approvals/{id}/decide` — body `{"approved": bool, "decided_by":
"..."}`. Sets `status` to `"approved"` or `"rejected"` and stamps
`decided_at`. 404 if the id doesn't exist, 409 if it's already been decided —
decisions aren't revisable through this endpoint.

`GET /approvals/resumable` — approvals that have been decided but not yet
replayed into their graph (`status != "pending"` and `resumed == False`).
This is what `resume_approvals.py` polls.

`POST /approvals/{id}/mark_resumed` — sets `resumed: true`. Called once the
resume script has successfully replayed a decision, so the same approval
doesn't get resumed twice.

`GET /health` — liveness check.

## Storage

JSON file (`approvals.json`, same simplicity level as the activity log),
keyed by approval id. Fine for the queue depths a single firm's HITL
approvals will ever reach; point `STORE_PATH` at a real database if that
changes and nothing calling this service needs to change.

## Running locally

```
pip install -r requirements.txt
uvicorn approval_service.main:app --port 8004
```

Agents and the resume script pick this up via `APPROVAL_SERVICE_URL`
(defaults to `http://localhost:8004`). Import `client.py` for
`create_approval`, `get_pending_approvals`, `get_approval`, `decide_approval`,
`get_resumable_approvals`, and `mark_approval_resumed`.

In production this runs as `legal-approval.service` on port 8104, same
pattern as `legal-activity-log` (8101), `legal-conflicts` (8102), and
`legal-rag` (8103).
