import json
import os
import re
import time
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from conflicts_service.client import check_conflicts

DEFAULT_MODEL = "gemma4-26b-64k"
DEFAULT_BASE_URL = "http://100.88.112.5:11434/v1"


class WorkflowState(TypedDict, total=False):
    tenant_id: str
    prompt: str  # raw prospective-client intake email
    model: str
    party_names: list[str]
    matter_type: str
    conflicts: list[dict]
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


def extract_node(state: WorkflowState) -> WorkflowState:
    llm = _llm()
    extraction_prompt = (
        "Extract the following from this prospective-client intake email. "
        "Respond with ONLY a JSON object, no other text:\n"
        '{"party_names": ["..."], "matter_type": "..."}\n\n'
        "party_names should include every person or company named in the email "
        "(the prospective client and any other parties involved in the matter).\n\n"
        f"Email:\n{state['prompt']}"
    )
    response = llm.invoke(extraction_prompt)
    text = str(response.content)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        parsed = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        parsed = {}

    return {
        "party_names": parsed.get("party_names", []),
        "matter_type": parsed.get("matter_type", "unknown"),
    }


def conflict_check_node(state: WorkflowState) -> WorkflowState:
    conflicts = check_conflicts(state.get("party_names", []))
    return {"conflicts": conflicts}


def draft_memo_node(state: WorkflowState) -> WorkflowState:
    llm = _llm()
    conflicts = state.get("conflicts", [])
    conflicts_summary = (
        "\n".join(
            f"- {c['queried_name']}: matches existing record '{c['name']}' "
            f"({c['role']}, matter: {c['matter']})"
            for c in conflicts
        )
        or "No conflicts found."
    )
    memo_prompt = (
        "Draft a short intake memo for a partner to review, based on this "
        "prospective-client matter. Include: matter type, parties involved, "
        "conflict-check results, and a recommendation on whether to proceed "
        "to engagement or escalate the conflict for partner review.\n\n"
        f"Matter type: {state.get('matter_type', 'unknown')}\n"
        f"Parties: {', '.join(state.get('party_names', [])) or 'none extracted'}\n"
        f"Conflict check results:\n{conflicts_summary}\n\n"
        f"Original intake email:\n{state['prompt']}"
    )
    started = time.perf_counter()
    response = llm.invoke(memo_prompt)
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
    approved = bool(interrupt({"draft": state["draft"], "conflicts": state.get("conflicts", [])}))
    return {"approved": approved}


def output_node(state: WorkflowState) -> WorkflowState:
    return {"output": state["draft"] if state["approved"] else ""}


builder = StateGraph(WorkflowState)
builder.add_node("input", input_node)
builder.add_node("extract", extract_node)
builder.add_node("conflict_check", conflict_check_node)
builder.add_node("draft_memo", draft_memo_node)
builder.add_node("human_approval_interrupt", human_approval_interrupt)
builder.add_node("output", output_node)
builder.add_edge(START, "input")
builder.add_edge("input", "extract")
builder.add_edge("extract", "conflict_check")
builder.add_edge("conflict_check", "draft_memo")
builder.add_edge("draft_memo", "human_approval_interrupt")
builder.add_edge("human_approval_interrupt", "output")
builder.add_edge("output", END)

graph = builder.compile(checkpointer=InMemorySaver())
