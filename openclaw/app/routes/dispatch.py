import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends

from ..auth import authenticate
from ..classifier import classify
from ..config import settings
from ..db import (
    complete_run,
    create_run,
    record_dispatch,
    update_run_running,
    upsert_developer,
)
from ..schemas import DispatchAlternative, DispatchRequest, DispatchResponse
from ..tools.llm import run_inference_with_retry

router = APIRouter()
log = logging.getLogger("openclaw.dispatch")


def _url_for_tool(tool: str) -> str:
    return {
        "openhands": settings.openhands_url,
        "opencode": settings.opencode_url,
        "direct": settings.opencode_url,
    }.get(tool, settings.opencode_url)


async def _execute_run(run_id: int, tool: str, prompt: str, max_tokens: int) -> None:
    """Background task: drive the LLM, record the result."""
    await update_run_running(run_id)
    try:
        result = await run_inference_with_retry(
            tool=tool, prompt=prompt, max_tokens=max_tokens,
        )
        await complete_run(
            run_id=run_id,
            status="succeeded",
            output=result["output"],
            model=result["model"],
            duration_ms=result["duration_ms"],
            tokens_in=result["tokens_in"],
            tokens_out=result["tokens_out"],
        )
        log.info("run %d succeeded in %dms", run_id, result["duration_ms"])
    except Exception as e:
        log.exception("run %d failed", run_id)
        await complete_run(
            run_id=run_id,
            status="failed",
            error=f"{e.__class__.__name__}: {e}",
        )


@router.post("/v1/dispatch", response_model=DispatchResponse)
async def dispatch(
    body: DispatchRequest,
    background_tasks: BackgroundTasks,
    email: str = Depends(authenticate),
) -> DispatchResponse:
    await upsert_developer(email)
    picked, reason = await classify(body.prompt)
    snippet = body.prompt[:200]
    dispatch_id = await record_dispatch(
        owner_email=email,
        prompt_snippet=snippet,
        picked_tool=picked,
        picked_reason=reason,
        project_id=body.project_id,
    )

    run_id = None
    if body.execute:
        run_id = await create_run(
            dispatch_id=dispatch_id,
            owner_email=email,
            tool=picked,
            prompt=body.prompt,
        )
        # Fire and forget; client polls /v1/runs/{id} for status + output.
        background_tasks.add_task(
            _execute_run, run_id, picked, body.prompt, body.max_tokens,
        )

    others = [t for t in ("openhands", "opencode") if t != picked]
    return DispatchResponse(
        dispatch_id=dispatch_id,
        suggested_tool=picked,
        suggested_url=_url_for_tool(picked),
        alternatives=[
            DispatchAlternative(tool=t, url=_url_for_tool(t)) for t in others
        ],
        reason=reason,
        run_id=run_id,
    )
