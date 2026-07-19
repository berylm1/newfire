import os
import sys
import time
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from grants_gov import search_opportunities
from fit_scoring import score_opportunities

# Ensure tenant root is on path so shared/ imports resolve
_tenant_root = str(__import__("pathlib").Path(__file__).resolve().parent.parent)
if _tenant_root not in sys.path:
    sys.path.insert(0, _tenant_root)

from shared.llm_config import LLM_BASE_URL, LLM_MODEL, require_api_key

TOP_N = 6


class WorkflowState(TypedDict, total=False):
    tenant_id: str
    mission_keywords: list[str]
    model: str
    top_opportunities: list[dict]
    fetch_errors: list[str]
    draft: str
    output: str
    approved: bool
    latency_ms: int
    input_tokens: int
    output_tokens: int


def _llm() -> ChatOpenAI:
    return ChatOpenAI(api_key=require_api_key(), base_url=LLM_BASE_URL, model=LLM_MODEL)


def input_node(state: WorkflowState) -> WorkflowState:
    return state


def fetch_opportunities_node(state: WorkflowState) -> WorkflowState:
    hits_by_keyword = {}
    errors = []
    for keyword in state["mission_keywords"]:
        try:
            hits_by_keyword[keyword] = search_opportunities(keyword, rows=10)
        except Exception as exc:
            errors.append(f"{keyword}: {exc}")
            hits_by_keyword[keyword] = []

    if errors and not any(hits_by_keyword.values()):
        # Every keyword failed and nothing came back at all — this is a fetch
        # failure, not a genuine "no opportunities this week" result. Don't
        # let it through silently as an empty digest.
        raise RuntimeError(f"Grants.gov fetch failed for all keywords: {'; '.join(errors)}")

    scored = score_opportunities(hits_by_keyword)
    return {"top_opportunities": scored[:TOP_N], "fetch_errors": errors}


def draft_digest_node(state: WorkflowState) -> WorkflowState:
    llm = _llm()
    opportunities = state.get("top_opportunities", [])
    listing = (
        "\n".join(
            f"- {o['title']} ({o['agency']}) — closes {o.get('closeDate') or 'TBD (forecasted)'}, "
            f"matched mission keywords: {', '.join(o['matched_keywords'])}, fit score {o['fit_score']}"
            for o in opportunities
        )
        or "No opportunities found this week."
    )
    digest_prompt = (
        "Draft a short Monday-morning grant digest for an Executive Director, "
        "based on this week's matched funding opportunities below. Keep it "
        "scannable — a one-line summary, then the list with a one-sentence "
        "note per item on why it's a good fit. Do not draft any outreach to "
        "funders; this digest is for internal review only.\n\n"
        f"Opportunities:\n{listing}"
    )
    started = time.perf_counter()
    response = llm.invoke(digest_prompt)
    latency_ms = int((time.perf_counter() - started) * 1000)
    usage = response.usage_metadata or {}

    return {
        "model": LLM_MODEL,
        "draft": str(response.content),
        "latency_ms": latency_ms,
        "input_tokens": int(usage.get("input_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
    }


def human_approval_interrupt(state: WorkflowState) -> WorkflowState:
    approved = bool(interrupt({"draft": state["draft"], "opportunities": state.get("top_opportunities", [])}))
    return {"approved": approved}


def output_node(state: WorkflowState) -> WorkflowState:
    return {"output": state["draft"] if state["approved"] else ""}


builder = StateGraph(WorkflowState)
builder.add_node("input", input_node)
builder.add_node("fetch_opportunities", fetch_opportunities_node)
builder.add_node("draft_digest", draft_digest_node)
builder.add_node("human_approval_interrupt", human_approval_interrupt)
builder.add_node("output", output_node)
builder.add_edge(START, "input")
builder.add_edge("input", "fetch_opportunities")
builder.add_edge("fetch_opportunities", "draft_digest")
builder.add_edge("draft_digest", "human_approval_interrupt")
builder.add_edge("human_approval_interrupt", "output")
builder.add_edge("output", END)

graph = builder.compile(checkpointer=InMemorySaver())
