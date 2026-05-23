"""
Inference backend for executor mode.

PR 3: capture finish_reason so the UI can warn when output was truncated.
"""
import asyncio
import logging
import time

import httpx

log = logging.getLogger("openclaw.tools.llm")

ROUTER_URL = "http://100.88.112.5:9094"

MODEL_BY_TOOL = {
    "openhands": "qwen3-coder-30b",
    "opencode": "qwen-coder-7b",
    "direct": "gemma3-4b",
}

SYSTEM_BY_TOOL = {
    "openhands": (
        "You are an autonomous senior engineer working inside the NewFire homelab. "
        "Break the user's brief into steps, then produce a complete plan AND the "
        "code or commands needed to execute it. Use fenced code blocks with the "
        "language tag (```python, ```bash, etc.). When you write a file, name it "
        "with a markdown header above the fence: '## filename.ext' or 'filename: name.ext'. "
        "Do not ask clarifying questions; make reasonable assumptions and state them."
    ),
    "opencode": (
        "You are a focused coding assistant. Answer the user's question or perform "
        "the edit they describe. Use fenced code blocks with the language tag "
        "(```python, ```bash, etc.). When you write a file, name it with a "
        "markdown header above the fence: '## filename.ext' or 'filename: name.ext'. "
        "Be concise."
    ),
    "direct": (
        "You are a helpful assistant for the NewFire engineering team. Answer "
        "directly and briefly. Use fenced code blocks for any code."
    ),
}


async def run_inference(
    tool: str,
    prompt: str,
    max_tokens: int = 2048,
    temperature: float = 0.2,
    timeout_seconds: int = 600,
) -> dict:
    """Returns {output, model, tokens_in, tokens_out, duration_ms, finish_reason, truncated}."""
    model = MODEL_BY_TOOL.get(tool, "gemma3-4b")
    system = SYSTEM_BY_TOOL.get(tool, SYSTEM_BY_TOOL["direct"])
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    started = time.time()
    log.info("run_inference tool=%s model=%s prompt_chars=%d max_tokens=%d",
             tool, model, len(prompt), max_tokens)
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        r = await client.post(f"{ROUTER_URL}/v1/chat/completions", json=body)
        r.raise_for_status()
        data = r.json()
    elapsed_ms = int((time.time() - started) * 1000)
    content = ""
    finish_reason = None
    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice.get("finish_reason")
    except (KeyError, IndexError):
        pass
    usage = data.get("usage") or {}
    truncated = finish_reason == "length"
    return {
        "output": content,
        "model": model,
        "tokens_in": usage.get("prompt_tokens"),
        "tokens_out": usage.get("completion_tokens"),
        "duration_ms": elapsed_ms,
        "finish_reason": finish_reason,
        "truncated": truncated,
    }


async def run_inference_with_retry(tool: str, prompt: str, **kw) -> dict:
    for attempt in (1, 2):
        try:
            return await run_inference(tool, prompt, **kw)
        except httpx.HTTPError as e:
            log.warning("inference attempt %d failed: %s", attempt, e)
            if attempt == 2:
                raise
            await asyncio.sleep(1.5)
    raise RuntimeError("unreachable")
