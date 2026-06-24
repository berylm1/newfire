import os
import time
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from grants_gov import search_opportunities
from fit_scoring import score_opportunities

DEFAULT_MODEL = "gemma4-26b-64k"
DEFAULT_BASE_URL = "http://100.88.112.5:11434/v1"
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
    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.environ.get("LLM_API_KEY", "ollama")
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    return ChatOpenAI(api_key=api_key, base_url=base_url, model=model)


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
        "model": os.environ.get("LLM_MODEL", DEFAULT_MODEL),
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
