import os
import time
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt


DEFAULT_MODEL = "gemma4-26b-64k"
DEFAULT_BASE_URL = "http://100.88.112.5:11434/v1"
TENANT_MODELS: dict[str, str] = {}


class WorkflowState(TypedDict, total=False):
    tenant_id: str
    prompt: str
    model: str
    draft: str
    output: str
    approved: bool
    latency_ms: int
    input_tokens: int
    output_tokens: int


def input_node(state: WorkflowState) -> WorkflowState:
    return state


def llm_call(state: WorkflowState) -> WorkflowState:
    model = TENANT_MODELS.get(state["tenant_id"], DEFAULT_MODEL)
    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.environ.get("LLM_API_KEY", "ollama")
    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    started = time.perf_counter()
    response = llm.invoke(state["prompt"])
    latency_ms = int((time.perf_counter() - started) * 1000)
    usage = response.usage_metadata or {}

    return {
        "model": model,
        "draft": str(response.content),
        "latency_ms": latency_ms,
        "input_tokens": int(usage.get("input_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
    }


def human_approval_interrupt(state: WorkflowState) -> WorkflowState:
    approved = bool(interrupt({"draft": state["draft"]}))
    return {"approved": approved}


def output_node(state: WorkflowState) -> WorkflowState:
    return {"output": state["draft"] if state["approved"] else ""}


builder = StateGraph(WorkflowState)
builder.add_node("input", input_node)
builder.add_node("llm_call", llm_call)
builder.add_node("human_approval_interrupt", human_approval_interrupt)
builder.add_node("output", output_node)
builder.add_edge(START, "input")
builder.add_edge("input", "llm_call")
builder.add_edge("llm_call", "human_approval_interrupt")
builder.add_edge("human_approval_interrupt", "output")
builder.add_edge("output", END)

graph = builder.compile(checkpointer=InMemorySaver())
