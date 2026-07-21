"""Visa Bulletin Check — requirement #10 from Mr. Patrick's product-
direction meeting: track a client's priority date against the State
Department's monthly Visa Bulletin and flag when it becomes current.
`visa_bulletin_service` owns the real bulletin data and the is-current
comparison; this graph is the per-case wiring — same shape as
`case_jeopardy_check`, one case in, a short attorney-facing note out.

No human_approval_interrupt here, for the same reason as
case_jeopardy_check: this never leaves the firm, it's advisory information
reaching the attorney about their own case.

Unlike case_jeopardy_check, this only logs to activity_log_service when
the priority date is actually current — not every day a case is checked
and still waiting. A green-card case can sit "not current" for years; a
daily "still waiting" event for every such case would bury the one thing
that's actually worth an attorney's attention: it becoming current.
"""

import os
import time
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from activity_log_service.client import log_event
from case_service.client import get_case
from visa_bulletin_service.client import check_priority_date

DEFAULT_MODEL = "gemma4-26b-64k"
DEFAULT_BASE_URL = "http://100.88.112.5:11434/v1"


class WorkflowState(TypedDict, total=False):
    tenant_id: str
    case_id: str
    model: str
    case: dict
    tracked: bool
    check_result: dict
    draft: str
    output: str
    latency_ms: int
    input_tokens: int
    output_tokens: int


def _llm() -> ChatOpenAI:
    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.environ.get("LLM_API_KEY", "ollama")
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    return ChatOpenAI(api_key=api_key, base_url=base_url, model=model)


def input_node(state: WorkflowState) -> WorkflowState:
    return state


def load_case_node(state: WorkflowState) -> WorkflowState:
    case = get_case(state["tenant_id"], state["case_id"])
    return {"case": case}


def check_bulletin_node(state: WorkflowState) -> WorkflowState:
    tracking = state["case"].get("visa_bulletin_tracking") or {}
    category = tracking.get("category")
    priority_date = tracking.get("priority_date")
    if not category or not priority_date:
        # Nothing to check -- most case types (asylum, naturalization,
        # non-immigrant H-1B) have no priority date at all.
        return {"tracked": False}

    result = check_priority_date(category=category, priority_date=priority_date, country=tracking.get("country"))
    return {"tracked": True, "check_result": result}


def draft_report_node(state: WorkflowState) -> WorkflowState:
    client_name = state["case"].get("client_name", "this client")

    if not state.get("tracked"):
        return {
            "model": os.environ.get("LLM_MODEL", DEFAULT_MODEL),
            "draft": f"No priority date on file to track for {client_name}.",
            "latency_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    result = state["check_result"]
    if not result["current"]:
        return {
            "model": os.environ.get("LLM_MODEL", DEFAULT_MODEL),
            "draft": (
                f"{client_name}'s priority date is not yet current. Category {result['category']} "
                f"({result['country']}) is at {result['cutoff']} as of the {result['bulletin_month']} bulletin."
            ),
            "latency_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    report_prompt = (
        f"Draft a short, direct note for an attorney: {client_name}'s priority date has just become "
        f"current on the {result['bulletin_month']} Visa Bulletin, category {result['category']} "
        f"({result['country']}), cutoff {result['cutoff']}. Say what this means and that next steps "
        "should be discussed with the client soon. One or two sentences, no formal memo."
    )
    llm = _llm()
    started = time.perf_counter()
    response = llm.invoke(report_prompt)
    latency_ms = int((time.perf_counter() - started) * 1000)
    usage = response.usage_metadata or {}

    return {
        "model": os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        "draft": str(response.content),
        "latency_ms": latency_ms,
        "input_tokens": int(usage.get("input_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
    }


def log_flag_node(state: WorkflowState) -> WorkflowState:
    if state.get("tracked") and state["check_result"]["current"]:
        client_name = state["case"].get("client_name", "this client")
        log_event(
            event_type="priority_date_current",
            urgency="high",
            summary=f"{client_name}: priority date is now current ({state['draft']})",
        )
    return {"output": state["draft"]}


builder = StateGraph(WorkflowState)
builder.add_node("input", input_node)
builder.add_node("load_case", load_case_node)
builder.add_node("check_bulletin", check_bulletin_node)
builder.add_node("draft_report", draft_report_node)
builder.add_node("log_flag", log_flag_node)
builder.add_edge(START, "input")
builder.add_edge("input", "load_case")
builder.add_edge("load_case", "check_bulletin")
builder.add_edge("check_bulletin", "draft_report")
builder.add_edge("draft_report", "log_flag")
builder.add_edge("log_flag", END)

graph = builder.compile(checkpointer=InMemorySaver())
