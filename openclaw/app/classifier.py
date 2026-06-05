"""
Two-stage dispatch classifier per spec section 6.

Stage A: zero-cost keyword fast-path. Returns (tool, reason) or None if the
prompt is ambiguous.

Stage B: source-controlled routing logic with an optional LiteLLM/OpenAI-style
classifier call. If the model endpoint is unavailable or returns an invalid
answer, Stage B falls back to deterministic domain rules instead of a stub.
"""
import logging
import re
from typing import Any

import httpx

from .config import settings

log = logging.getLogger("openclaw.classifier")

ALLOWED_TOOLS = {"openhands", "opencode", "direct"}

# Stage A keyword sets (case-insensitive contains).
OPENHANDS_TRIGGERS = (
    "build end to end", "build end-to-end", "implement end to end",
    "implement end-to-end", "ship me", "autonomously", "no questions",
    "do it all", "from scratch and run", "build the whole",
)
OPENCODE_TRIGGERS = (
    "edit this file", "open this file", "open ", "look at line",
    "what does this do", "what does this function do", "refactor this",
    "fix the bug in", "review the diff",
)


MULTI_STEP_SIGNALS = (
    " then ", " after that", "and then", "steps:", "step 1", "step 2",
    "1.", "2.", " and run ", " and deploy", " and ship",
)

AUTONOMOUS_VERBS = (
    " build ", "build me ", " add ", " implement ", " create ",
    " deploy ", " ship ", " run the migration", " run the script",
)

CODE_INSPECTION_TERMS = (
    "function", "class", "module", "file", "diff", "bug", "test",
    "route", "endpoint", "schema", "migration", "repository",
)

STAGE_B_SYSTEM_PROMPT = (
    "Classify the developer's intent. Reply with one of: openhands, opencode, direct. "
    "Pick openhands when the user wants the system to autonomously build or modify "
    "multiple files. Pick opencode for interactive code editing or single-file "
    "inspection. Pick direct for a one-off Q&A that doesn't need either tool."
)


def _normalize_prompt(prompt: str) -> str:
    return f" {prompt.lower().strip()} "


def _has_multi_step(p: str) -> bool:
    return any(s in p for s in MULTI_STEP_SIGNALS)


def stage_a(prompt: str) -> tuple[str, str] | None:
    p = _normalize_prompt(prompt)
    for needle in OPENHANDS_TRIGGERS:
        if needle in p:
            return ("openhands", f"stage_a: matched openhands trigger '{needle}'")
    # If an opencode trigger AND a multi-step signal both exist, defer to
    # Stage B so the broader intent wins over the single-file verb.
    for needle in OPENCODE_TRIGGERS:
        if needle in p:
            if _has_multi_step(p):
                return None
            return ("opencode", f"stage_a: matched opencode trigger '{needle}'")
    # Ambiguous pure questions intentionally defer to Stage B so the classifier
    # can choose opencode for code inspection or direct for general Q&A.
    return None


def _parse_tool_response(content: str) -> str | None:
    """Extract a valid tool from model output without trusting extra prose."""
    cleaned = (content or "").strip().lower()
    if cleaned in ALLOWED_TOOLS:
        return cleaned
    tokens = re.findall(r"[a-z_]+", cleaned)
    matches = [token for token in tokens if token in ALLOWED_TOOLS]
    if len(matches) == 1:
        return matches[0]
    return None


def _extract_choice_content(data: dict[str, Any]) -> str:
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


async def _call_stage_b_model(prompt: str) -> tuple[str, str] | None:
    """Call a LiteLLM/OpenAI-compatible classifier endpoint when configured."""
    if not settings.litellm_url or not settings.litellm_model:
        return None

    body = {
        "model": settings.litellm_model,
        "messages": [
            {"role": "system", "content": STAGE_B_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 8,
    }
    headers = {}
    if settings.litellm_api_key:
        headers["Authorization"] = f"Bearer {settings.litellm_api_key}"

    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.post(
            f"{settings.litellm_url.rstrip('/')}/v1/chat/completions",
            json=body,
            headers=headers,
        )
        response.raise_for_status()
        tool = _parse_tool_response(_extract_choice_content(response.json()))
        if tool:
            return (tool, f"stage_b_llm: LiteLLM classifier returned '{tool}'")
        return None


def _deterministic_stage_b(prompt: str) -> tuple[str, str]:
    """Deterministic Stage B fallback with explicit routing semantics."""
    p = _normalize_prompt(prompt)
    if _has_multi_step(p):
        return ("openhands", "stage_b_rules: multi-step language detected")
    if any(v in p for v in AUTONOMOUS_VERBS):
        return ("openhands", "stage_b_rules: autonomous implementation verb detected")
    if p.strip().endswith("?"):
        if any(term in p for term in CODE_INSPECTION_TERMS):
            return ("opencode", "stage_b_rules: code inspection question")
        return ("direct", "stage_b_rules: one-off direct question")
    return ("opencode", "stage_b_rules: default interactive coding lane")


async def stage_b(prompt: str) -> tuple[str, str]:
    """Route ambiguous prompts using model classification with deterministic fallback."""
    try:
        model_choice = await _call_stage_b_model(prompt)
        if model_choice is not None:
            return model_choice
    except Exception as e:  # noqa: BLE001 - classifier must fail safe into rules.
        log.warning("Stage B model classifier failed; using deterministic rules: %s", e)
    return _deterministic_stage_b(prompt)


async def classify(prompt: str) -> tuple[str, str]:
    """Return (picked_tool, picked_reason)."""
    a = stage_a(prompt)
    if a is not None:
        return a
    return await stage_b(prompt)
