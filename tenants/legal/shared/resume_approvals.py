#!/usr/bin/env python3
"""Replay decided approvals back into their paused LangGraph runs.

Both `intake_conflict_check` and `citation_checker` pause on a
`human_approval_interrupt` node and submit the draft to approval_service
instead of blocking on `input()`. Nothing resumes those graphs on its own —
this script is that missing half: it polls `GET /approvals/resumable` for
approvals that have been decided but not yet replayed, resumes each one's
graph with `Command(resume=...)` against the same sqlite checkpoint file the
original run used, does the same post-approval bookkeeping `run.py` used to
do inline (logging unresolved conflicts/citations to the activity feed), and
marks the approval resumed so it isn't picked up twice.

One-shot by design — run it by hand, from a cron job, or a systemd timer
(`python3 resume_approvals.py`). It does not loop or sleep on its own.
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from langgraph.types import Command

from approval_service.client import get_resumable_approvals, mark_approval_resumed


def _load_intake_conflict_check_graph():
    path = os.path.join(os.path.dirname(__file__), "..", "intake_conflict_check")
    sys.path.insert(0, path)
    import graph as intake_conflict_check_graph

    return intake_conflict_check_graph.graph


def _load_citation_checker_graph():
    path = os.path.join(os.path.dirname(__file__), "..", "citation_checker")
    sys.path.insert(0, path)
    import graph as citation_checker_graph

    return citation_checker_graph.graph


GRAPH_LOADERS = {
    "intake_memo": _load_intake_conflict_check_graph,
    "citation_report": _load_citation_checker_graph,
}


def _finalize_intake_conflict_check(result: dict) -> None:
    conflicts = result.get("conflicts", [])
    if conflicts:
        from activity_log_service.client import log_event

        names = ", ".join(c["name"] for c in conflicts)
        log_event(
            "conflict_flag",
            "high",
            f"New intake ({result.get('matter_type', 'unspecified matter')}) flagged a conflict: {names}. Needs a decision before this matter proceeds.",
        )

    _remember_intake_conflict_check(result)


def _remember_intake_conflict_check(result: dict) -> None:
    # Runs regardless of approve/reject — a rejected intake is exactly the kind
    # of outcome a future intake for the same party should know about. Best-
    # effort like the activity-log call above: a memory_service hiccup here
    # shouldn't crash the resume script or block marking the approval resumed.
    party_names = result.get("party_names", [])
    if not party_names:
        return

    try:
        from memory_service.client import add_note

        matter_type = result.get("matter_type", "unspecified matter")
        conflicts = result.get("conflicts", [])
        approved = result.get("approved", False)
        date = datetime.now(timezone.utc).date().isoformat()
        note = (
            f"Intake matter ({matter_type}): "
            f"{'conflict flagged, ' if conflicts else ''}"
            f"{'approved' if approved else 'rejected'} on {date}."
        )
        for party in party_names:
            add_note(
                tenant_id=result["tenant_id"],
                client_key=party,
                note=note,
                matter_type=matter_type,
                source="intake_conflict_check",
            )
    except Exception:
        pass


def _finalize_citation_checker(result: dict) -> None:
    unverified = [r["query"] for r in result.get("verification_results", []) if not r.get("verified")]
    if not unverified:
        return

    from activity_log_service.client import log_event

    log_event(
        "citation_review",
        "medium",
        f"Citation check flagged {len(unverified)} citation(s) needing manual review before filing: {', '.join(unverified)}.",
    )


FINALIZERS = {
    "intake_memo": _finalize_intake_conflict_check,
    "citation_report": _finalize_citation_checker,
}


def resume_one(approval: dict) -> None:
    kind = approval["kind"]
    load_graph = GRAPH_LOADERS.get(kind)
    if load_graph is None:
        print(f"Skipping approval {approval['id']}: unknown kind {kind!r}")
        return

    graph = load_graph()
    config = {"configurable": {"thread_id": approval["thread_id"]}}
    result = graph.invoke(Command(resume=(approval["status"] == "approved")), config=config)

    finalize = FINALIZERS[kind]
    finalize(result)

    mark_approval_resumed(approval["id"])
    print(f"Resumed approval {approval['id']} ({kind}, {approval['status']}) for thread {approval['thread_id']}")


def main() -> None:
    resumable = get_resumable_approvals()
    if not resumable:
        print("No resumable approvals.")
        return

    for approval in resumable:
        resume_one(approval)


if __name__ == "__main__":
    main()
