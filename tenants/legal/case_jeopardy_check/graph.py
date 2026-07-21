"""Case Jeopardy Check — requirement #5 from Mr. Patrick's product-direction
meeting, wired up around playbooks.py's rules engine. Loads one case, runs
its case-type playbook, best-effort attaches a supporting citation from
rag_service for each flag found, and drafts a short report for the
attorney.

No human_approval_interrupt here, unlike citation_checker and
intake_conflict_check. Like daily_briefing, this never leaves the firm —
it's advisory information reaching the attorney about their own case, not a
client-facing draft, so it doesn't need the same gate (see the
autonomy-tiering direction in the immigration-tenant-pivot notes). Flags are
logged to activity_log_service instead, the same shared feed
daily_briefing already reads from — no new delivery plumbing needed for
these to show up in the morning briefing.
"""

import os
import time
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from activity_log_service.client import log_event
from case_service.client import get_case
from playbooks import run_checks
from rag_service.client import search as rag_search

DEFAULT_MODEL = "gemma4-26b-64k"
DEFAULT_BASE_URL = "http://100.88.112.5:11434/v1"

# Below this cosine-similarity score, a rag_service match is treated as
# irrelevant rather than attached as a citation — an unrelated top-1 result
# from a sparse or empty corpus is worse than no citation at all in a legal
# context.
RAG_RELEVANCE_THRESHOLD = 0.75


class WorkflowState(TypedDict, total=False):
    tenant_id: str
    case_id: str
    model: str
    case: dict
    flags: list[dict]
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


def check_playbook_node(state: WorkflowState) -> WorkflowState:
    flags = run_checks(state["case"])
    return {"flags": flags}


def rag_lookup_node(state: WorkflowState) -> WorkflowState:
    # Best-effort like recall_node in intake_conflict_check — a citation is
    # a nice-to-have on top of a flag that's already true on its own, not a
    # reason to fail the whole check if rag_service has nothing indexed yet
    # or is unreachable.
    flags = state.get("flags", [])
    for flag in flags:
        citation = None
        try:
            results = rag_search(flag["detail"], top_k=1)
        except Exception:
            results = []
        if results and results[0]["score"] >= RAG_RELEVANCE_THRESHOLD:
            citation = results[0]["metadata"].get("citation") or results[0]["text"][:120]
        flag["citation"] = citation
    return {"flags": flags}


def draft_report_node(state: WorkflowState) -> WorkflowState:
    client_name = state["case"].get("client_name", "this client")
    flags = state.get("flags", [])
    if not flags:
        return {
            "model": os.environ.get("LLM_MODEL", DEFAULT_MODEL),
            "draft": f"No jeopardy flags found for {client_name}.",
            "latency_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    lines = []
    for f in flags:
        citation = f" (see {f['citation']})" if f.get("citation") else ""
        lines.append(f"- ({f['urgency']} urgency, {f['rule']}) {f['detail']}{citation}")
    items = "\n".join(lines)

    report_prompt = (
        f"Draft a short case-jeopardy report for an attorney about {client_name}'s case. "
        "List each issue below in plain language, ordered by urgency. Be direct — this is "
        "for the attorney to act on, not a formal memo.\n\n"
        f"Flags:\n{items}"
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


def log_flags_node(state: WorkflowState) -> WorkflowState:
    client_name = state["case"].get("client_name", "this client")
    for flag in state.get("flags", []):
        log_event(
            event_type="case_jeopardy_flag",
            urgency=flag["urgency"],
            summary=f"{client_name}: {flag['detail']}",
        )
    return {"output": state["draft"]}


builder = StateGraph(WorkflowState)
builder.add_node("input", input_node)
builder.add_node("load_case", load_case_node)
builder.add_node("check_playbook", check_playbook_node)
builder.add_node("rag_lookup", rag_lookup_node)
builder.add_node("draft_report", draft_report_node)
builder.add_node("log_flags", log_flags_node)
builder.add_edge(START, "input")
builder.add_edge("input", "load_case")
builder.add_edge("load_case", "check_playbook")
builder.add_edge("check_playbook", "rag_lookup")
builder.add_edge("rag_lookup", "draft_report")
builder.add_edge("draft_report", "log_flags")
builder.add_edge("log_flags", END)

graph = builder.compile(checkpointer=InMemorySaver())
