import logging
import os

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
from ..tools.codeblocks import parse_blocks, write_workspace

router = APIRouter()
log = logging.getLogger("openclaw.dispatch")

WORKSPACE_ROOT = "/workspaces"


def _url_for_tool(tool: str) -> str:
    return {
        "openhands": settings.openhands_url,
        "opencode": settings.opencode_url,
        "direct": settings.opencode_url,
    }.get(tool, settings.opencode_url)


async def _execute_run(run_id: int, tool: str, prompt: str, max_tokens: int,
                       workspace_path: str) -> None:
    await update_run_running(run_id)
    try:
        result = await run_inference_with_retry(
            tool=tool, prompt=prompt, max_tokens=max_tokens,
        )
        # Extract code blocks and materialize them on CephFS.
        blocks, readme_prose = parse_blocks(result["output"] or "")
        try:
            files_written = write_workspace(workspace_path, prompt, result["output"] or "",
                                            blocks, readme_prose)
        except Exception as e:
            log.warning("workspace write failed for run %d: %s", run_id, e)
            files_written = []

        # Strip body from the metadata we persist; full body sits on disk now.
        files_meta = [{
            "filename": b["filename"],
            "language": b["language"],
            "size": b["size"],
            "source": b["source"],
            "path": b.get("path"),
        } for b in files_written]

        await complete_run(
            run_id=run_id,
            status="succeeded",
            output=result["output"],
            model=result["model"],
            duration_ms=result["duration_ms"],
            tokens_in=result["tokens_in"],
            tokens_out=result["tokens_out"],
            finish_reason=result.get("finish_reason"),
            truncated=result.get("truncated"),
            files_written=files_meta,
            workspace_path=workspace_path,
        )
        log.info("run %d done in %dms, %d files, finish=%s",
                 run_id, result["duration_ms"], len(files_meta),
                 result.get("finish_reason"))
    except Exception as e:
        log.exception("run %d failed", run_id)
        await complete_run(
            run_id=run_id, status="failed", error=f"{e.__class__.__name__}: {e}",
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
        # Each run gets a workspace under /workspaces (CephFS bind mount inside the container).
        # The DB still records the workspace_path as the in-container path; the host path
        # is the same logical location via the bind mount.
        # Workspace id uses the dispatch id since the run id is only known after insert.
        workspace_path_placeholder = os.path.join(WORKSPACE_ROOT, f"dispatch-{dispatch_id}")
        run_id = await create_run(
            dispatch_id=dispatch_id,
            owner_email=email,
            tool=picked,
            prompt=body.prompt,
            workspace_path=workspace_path_placeholder,
        )
        # Replace placeholder with run-id based path for clarity.
        workspace_path = os.path.join(WORKSPACE_ROOT, f"run-{run_id}")
        background_tasks.add_task(
            _execute_run, run_id, picked, body.prompt, body.max_tokens, workspace_path,
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
