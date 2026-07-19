import json
import os
import re
import sqlite3
import sys
import time
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from approval_service.client import create_approval
from courtlistener import verify_citation

# Ensure tenant root is on path so shared/ imports resolve
_tenant_root = str(__import__("pathlib").Path(__file__).resolve().parent.parent)
if _tenant_root not in sys.path:
    sys.path.insert(0, _tenant_root)

from shared.llm_config import LLM_BASE_URL, LLM_MODEL, require_api_key

CHECKPOINT_DB_PATH = os.path.join(os.path.dirname(__file__), "checkpoints.db")


class WorkflowState(TypedDict, total=False):
    tenant_id: str
    thread_id: str  # LangGraph checkpointer thread id — also handed to the approval queue so a later process can resume this exact run
    prompt: str  # the draft brief text — never modified by this workflow
    model: str
    citations_found: list[str]
    verification_results: list[dict]
    draft: str
    output: str
    approved: bool
    approval_id: str
    latency_ms: int
    input_tokens: int
    output_tokens: int


def _llm() -> ChatOpenAI:
    return ChatOpenAI(api_key=require_api_key(), base_url=LLM_BASE_URL, model=LLM_MODEL)


def input_node(state: WorkflowState) -> WorkflowState:
    return state


def extract_citations_node(state: WorkflowState) -> WorkflowState:
    llm = _llm()
    extraction_prompt = (
        "Extract every case citation and statute referenced in this legal "
        "brief. Respond with ONLY a JSON object, no other text:\n"
        '{"citations": ["case name or citation", ...]}\n\n'
        f"Brief:\n{state['prompt']}"
    )
    response = llm.invoke(extraction_prompt)
    text = str(response.content)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        parsed = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        parsed = {}

    return {"citations_found": parsed.get("citations", [])}


def verify_citations_node(state: WorkflowState) -> WorkflowState:
    results = [verify_citation(c) for c in state.get("citations_found", [])]
    return {"verification_results": results}


def draft_report_node(state: WorkflowState) -> WorkflowState:
    llm = _llm()
    results = state.get("verification_results", [])
    lines = []
    for r in results:
        if r.get("error"):
            lines.append(f"- {r['query']}: LOOKUP FAILED ({r['error']}) — could not verify, needs manual check")
        elif r["verified"]:
            lines.append(
                f"- {r['query']}: VERIFIED — matches \"{r['matched_case_name']}\" "
                f"({', '.join(r.get('citations', []))}), {r.get('court')}, filed {r.get('date_filed')}"
            )
        else:
            lines.append(f"- {r['query']}: NOT FOUND — no matching case in CourtListener, flag for attorney review")
    summary = "\n".join(lines) or "No citations were extracted from this brief."

    report_prompt = (
        "Draft a short citation-check report for an attorney reviewing this "
        "brief. List every citation and its verification status below. Do "
        "NOT rewrite or edit the brief itself — only report findings and "
        "flag anything unverifiable for the attorney to handle.\n\n"
        f"Citation check results:\n{summary}"
    )
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


def human_approval_interrupt(state: WorkflowState) -> WorkflowState:
    approval = create_approval(
        tenant_id=state["tenant_id"],
        thread_id=state["thread_id"],
        kind="citation_report",
        draft=state["draft"],
        context={"verification_results": state.get("verification_results", [])},
    )
    approved = bool(
        interrupt(
            {
                "draft": state["draft"],
                "verification_results": state.get("verification_results", []),
                "approval_id": approval["id"],
            }
        )
    )
    return {"approved": approved, "approval_id": approval["id"]}


def output_node(state: WorkflowState) -> WorkflowState:
    return {"output": state["draft"] if state["approved"] else ""}


builder = StateGraph(WorkflowState)
builder.add_node("input", input_node)
builder.add_node("extract_citations", extract_citations_node)
builder.add_node("verify_citations", verify_citations_node)
builder.add_node("draft_report", draft_report_node)
builder.add_node("human_approval_interrupt", human_approval_interrupt)
builder.add_node("output", output_node)
builder.add_edge(START, "input")
builder.add_edge("input", "extract_citations")
builder.add_edge("extract_citations", "verify_citations")
builder.add_edge("verify_citations", "draft_report")
builder.add_edge("draft_report", "human_approval_interrupt")
builder.add_edge("human_approval_interrupt", "output")
builder.add_edge("output", END)

_conn = sqlite3.connect(CHECKPOINT_DB_PATH, check_same_thread=False)
_checkpointer = SqliteSaver(_conn)
_checkpointer.setup()

graph = builder.compile(checkpointer=_checkpointer)
