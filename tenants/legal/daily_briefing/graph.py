import os
import sys
import time
from datetime import datetime, timezone
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

# Ensure tenant root is on path so shared/ imports resolve
_tenant_root = str(__import__("pathlib").Path(__file__).resolve().parent.parent)
if _tenant_root not in sys.path:
    sys.path.insert(0, _tenant_root)

from activity_log_service.client import get_todays_events
from case_service.client import list_cases
from notify_service.client import send_notification
from shared.llm_config import LLM_BASE_URL, LLM_MODEL, require_api_key
from tenant_config import get_attorney_contact

# How close a key_date has to be before it's worth surfacing at all. Real
# urgency-tiering (a filing deadline behaves differently than a priority
# date) is a later phase — this just needs to turn "close" into "high" and
# everything else into a lower tier so nothing near-term gets buried.
KEY_DATE_WINDOW_DAYS = 14


class WorkflowState(TypedDict, total=False):
    tenant_id: str
    model: str
    docket: list[dict]
    output: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    notify_id: str


def _urgency_for_days_remaining(days_remaining: int) -> str:
    # Overdue is at least as urgent as "due in 3 days" — a visa that already
    # expired unnoticed is the exact crisis this is meant to catch, not a
    # lower priority than one still counting down.
    if days_remaining <= 3:
        return "high"
    if days_remaining <= 7:
        return "medium"
    return "low"


def _docket_items_from_cases(cases: list[dict]) -> list[dict]:
    """Turn each case's key_dates into docket-style items for any date within
    KEY_DATE_WINDOW_DAYS — closer dates get higher urgency. This replaces the
    old hardcoded docket_feed.py sample data with the real per-case dates
    now on file in case_service.

    A date already in the past is surfaced too, not excluded — an already-
    expired visa is still on file and still unresolved, and staying silent
    about it would read as "nothing urgent" when the opposite is true. There
    is no lower bound on the window for this reason; only the upper bound
    (KEY_DATE_WINDOW_DAYS) limits what's included.
    """
    today = datetime.now(timezone.utc).date()
    items = []
    for case in cases:
        for date_label, date_str in (case.get("key_dates") or {}).items():
            try:
                target_date = datetime.fromisoformat(date_str).date()
            except (ValueError, TypeError):
                continue

            days_remaining = (target_date - today).days
            if days_remaining <= KEY_DATE_WINDOW_DAYS:
                label = date_label.replace("_", " ")
                if days_remaining < 0:
                    days_overdue = -days_remaining
                    plural = "" if days_overdue == 1 else "s"
                    summary = (
                        f"{label.capitalize()} for {case['client_name']} was "
                        f"{days_overdue} day{plural} ago and still needs attention."
                    )
                else:
                    plural = "" if days_remaining == 1 else "s"
                    summary = (
                        f"{label.capitalize()} for {case['client_name']} is in "
                        f"{days_remaining} day{plural}."
                    )
                items.append(
                    {
                        "type": "key_date",
                        "urgency": _urgency_for_days_remaining(days_remaining),
                        "summary": summary,
                    }
                )
    return items


def _llm() -> ChatOpenAI:
    return ChatOpenAI(api_key=require_api_key(), base_url=LLM_BASE_URL, model=LLM_MODEL)


def input_node(state: WorkflowState) -> WorkflowState:
    return state


def fetch_docket_node(state: WorkflowState) -> WorkflowState:
    real_events = get_todays_events()
    cases = list_cases(state["tenant_id"])
    return {"docket": real_events + _docket_items_from_cases(cases)}


def draft_briefing_node(state: WorkflowState) -> WorkflowState:
    llm = _llm()
    docket = state.get("docket", [])
    items = "\n".join(f"- ({d['urgency']} urgency, {d['type']}) {d['summary']}" for d in docket)

    briefing_prompt = (
        "Draft a short morning briefing for an attorney, based on the items "
        "below. Order it by urgency, not by category. Be direct and plain — "
        "this is for the attorney to read in under a minute before their day "
        "starts, not a formal memo. No greeting, no sign-off, just the list "
        "with enough context per item to know what to do next.\n\n"
        f"Today's items:\n{items}"
    )
    started = time.perf_counter()
    response = llm.invoke(briefing_prompt)
    latency_ms = int((time.perf_counter() - started) * 1000)
    usage = response.usage_metadata or {}

    return {
        "model": LLM_MODEL,
        "output": str(response.content),
        "latency_ms": latency_ms,
        "input_tokens": int(usage.get("input_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
    }


def send_briefing_node(state: WorkflowState) -> WorkflowState:
    # The briefing goes to the attorney, not a client — assigned_attorney on
    # a case is a free-text name, not a place to hang contact info, so this
    # reads from the tenant-level config instead (see tenant_config.py).
    contact = get_attorney_contact(state["tenant_id"])
    result = send_notification(
        tenant_id=state["tenant_id"],
        channel=contact["channel"],
        to=contact["to"],
        subject="Morning briefing",
        body=state["output"],
    )
    return {"notify_id": result["id"]}


builder = StateGraph(WorkflowState)
builder.add_node("input", input_node)
builder.add_node("fetch_docket", fetch_docket_node)
builder.add_node("draft_briefing", draft_briefing_node)
builder.add_node("send_briefing", send_briefing_node)
builder.add_edge(START, "input")
builder.add_edge("input", "fetch_docket")
builder.add_edge("fetch_docket", "draft_briefing")
builder.add_edge("draft_briefing", "send_briefing")
builder.add_edge("send_briefing", END)

graph = builder.compile(checkpointer=InMemorySaver())
