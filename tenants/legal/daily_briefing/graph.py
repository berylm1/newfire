import os
import time
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from docket_feed import get_todays_docket

DEFAULT_MODEL = "gemma4-26b-64k"
DEFAULT_BASE_URL = "http://100.88.112.5:11434/v1"


class WorkflowState(TypedDict, total=False):
    tenant_id: str
    model: str
    docket: list[dict]
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


def fetch_docket_node(state: WorkflowState) -> WorkflowState:
    return {"docket": get_todays_docket()}


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
        "model": os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        "output": str(response.content),
        "latency_ms": latency_ms,
        "input_tokens": int(usage.get("input_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
    }


builder = StateGraph(WorkflowState)
builder.add_node("input", input_node)
builder.add_node("fetch_docket", fetch_docket_node)
builder.add_node("draft_briefing", draft_briefing_node)
builder.add_edge(START, "input")
builder.add_edge("input", "fetch_docket")
builder.add_edge("fetch_docket", "draft_briefing")
builder.add_edge("draft_briefing", END)

graph = builder.compile(checkpointer=InMemorySaver())
