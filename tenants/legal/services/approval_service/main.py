"""Approval service — owns the human-in-the-loop approval queue for the legal
tenant's agents.

Agents that pause on a `human_approval_interrupt` node (intake conflict-check,
citation checker) used to rely on a human sitting at a terminal running the
agent's `run.py` and answering an `input()` prompt in the same process. That
only works when a human happens to be there synchronously — it breaks for any
agent triggered non-interactively (the gateway, a cron job), where there's no
TTY and the graph's in-memory state disappears the moment the process exits.

This service is the durable queue standing in for that terminal: an agent
submits a draft here and exits, a reviewer decides on it whenever they get to
it (from any process, at any time), and a separate resume script picks up
decided-but-not-yet-resumed approvals and replays them into the paused graph.
It doesn't make the decision or touch the graph itself — it just remembers
what's pending and what was decided, the same durability job LOG_PATH does
for the activity feed.

Swappable like the rest of this tenant: point STORE_PATH at a real database
and nothing calling this service needs to change.
"""

import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

STORE_PATH = os.path.join(os.path.dirname(__file__), "approvals.json")

app = FastAPI(title="Approval Service")


class ApprovalIn(BaseModel):
    tenant_id: str
    thread_id: str
    kind: str
    draft: str
    context: dict = {}


class DecisionIn(BaseModel):
    approved: bool
    decided_by: str


def _load() -> dict[str, dict]:
    if not os.path.exists(STORE_PATH):
        return {}
    with open(STORE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save(approvals: dict[str, dict]) -> None:
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(approvals, f, indent=2)


@app.post("/approvals")
def create_approval(approval: ApprovalIn) -> dict:
    approvals = _load()
    record = {
        "id": str(uuid.uuid4()),
        "tenant_id": approval.tenant_id,
        "thread_id": approval.thread_id,
        "kind": approval.kind,
        "draft": approval.draft,
        "context": approval.context,
        "status": "pending",
        "decided_by": None,
        "decided_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resumed": False,
    }
    approvals[record["id"]] = record
    _save(approvals)
    return record


@app.get("/approvals/pending")
def get_pending_approvals(tenant_id: str | None = None) -> list[dict]:
    approvals = _load()
    results = [a for a in approvals.values() if a["status"] == "pending"]
    if tenant_id is not None:
        results = [a for a in results if a["tenant_id"] == tenant_id]
    return results


@app.get("/approvals/resumable")
def get_resumable_approvals() -> list[dict]:
    approvals = _load()
    return [a for a in approvals.values() if a["status"] != "pending" and not a["resumed"]]


@app.get("/approvals/{approval_id}")
def get_approval(approval_id: str) -> dict:
    approvals = _load()
    record = approvals.get(approval_id)
    if record is None:
        raise HTTPException(status_code=404, detail="approval not found")
    return record


@app.post("/approvals/{approval_id}/decide")
def decide_approval(approval_id: str, decision: DecisionIn) -> dict:
    approvals = _load()
    record = approvals.get(approval_id)
    if record is None:
        raise HTTPException(status_code=404, detail="approval not found")
    if record["status"] != "pending":
        raise HTTPException(status_code=409, detail="approval already decided")

    record["status"] = "approved" if decision.approved else "rejected"
    record["decided_by"] = decision.decided_by
    record["decided_at"] = datetime.now(timezone.utc).isoformat()
    approvals[approval_id] = record
    _save(approvals)
    return record


@app.post("/approvals/{approval_id}/mark_resumed")
def mark_approval_resumed(approval_id: str) -> dict:
    approvals = _load()
    record = approvals.get(approval_id)
    if record is None:
        raise HTTPException(status_code=404, detail="approval not found")

    record["resumed"] = True
    approvals[approval_id] = record
    _save(approvals)
    return record


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
