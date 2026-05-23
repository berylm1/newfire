"""
Two-stage dispatch classifier per spec section 6.

Stage A: zero-cost keyword fast-path. Returns (tool, reason) or None if the
prompt is ambiguous.

Stage B: LLM classifier via LiteLLM. Returns (tool, reason). In PR 1 this is
a conservative stub that prefers OpenCode for interactive intent; the real
LLM call lands in PR 2 once LiteLLM connectivity is verified.
"""
import logging
import re
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


def _has_multi_step(p: str) -> bool:
    return any(s in p for s in MULTI_STEP_SIGNALS)


def stage_a(prompt: str) -> tuple[str, str] | None:
    p = prompt.lower().strip()
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
    # Pure question with no imperative -> opencode.
    if p.endswith("?") and not re.search(r"\b(build|implement|create|deploy|ship)\b", p):
        return ("opencode", "stage_a: question without imperative")
    return None


async def stage_b(prompt: str) -> tuple[str, str]:
    """
    PR 1 stub: deterministic fallback.
    Prefers openhands for multi-step intent or build/deploy/ship verbs,
    opencode for interactive shape.
    PR 2 will replace with a real LiteLLM call.
    """
    p = prompt.lower()
    if _has_multi_step(p):
        return ("openhands", "stage_b_stub: multi-step language detected")
    # build/deploy/ship verbs imply autonomous execution.
    autonomous_verbs = (" build ", "build me ", " add ", " deploy ", " ship ",
                        " run the migration", " run the script")
    if any(v in p for v in autonomous_verbs):
        return ("openhands", "stage_b_stub: autonomous verb detected")
    return ("opencode", "stage_b_stub: default interactive lane (real LLM in PR 2)")


async def classify(prompt: str) -> tuple[str, str]:
    """Return (picked_tool, picked_reason)."""
    a = stage_a(prompt)
    if a is not None:
        return a
    return await stage_b(prompt)
