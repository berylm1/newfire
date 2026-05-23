from fastapi import APIRouter, Depends, HTTPException

from ..auth import authenticate
from ..db import get_run, list_recent_runs
from ..schemas import FileWritten, RunResponse, RunSummary

router = APIRouter()


def _iso(dt) -> str | None:
    return dt.isoformat() if dt is not None else None


@router.get("/v1/runs/{run_id}", response_model=RunResponse)
async def get_run_route(run_id: int, email: str = Depends(authenticate)) -> RunResponse:
    row = await get_run(run_id, email)
    if row is None:
        raise HTTPException(404, f"run {run_id} not found for {email}")
    files = None
    if row.get("files_written"):
        files = [FileWritten(**f) for f in row["files_written"]]
    return RunResponse(
        id=row["id"],
        dispatch_id=row["dispatch_id"],
        tool=row["tool"],
        model=row.get("model"),
        status=row["status"],
        prompt=row["prompt"],
        output=row.get("output"),
        error=row.get("error"),
        started_at=_iso(row["started_at"]),
        finished_at=_iso(row.get("finished_at")),
        duration_ms=row.get("duration_ms"),
        tokens_in=row.get("tokens_in"),
        tokens_out=row.get("tokens_out"),
        finish_reason=row.get("finish_reason"),
        truncated=bool(row.get("truncated")),
        workspace_path=row.get("workspace_path"),
        files_written=files,
    )


@router.get("/v1/runs", response_model=list[RunSummary])
async def list_runs(email: str = Depends(authenticate)) -> list[RunSummary]:
    rows = await list_recent_runs(email)
    return [
        RunSummary(
            id=r["id"],
            tool=r["tool"],
            model=r.get("model"),
            status=r["status"],
            truncated=bool(r.get("truncated")),
            prompt_snippet=r["prompt_snippet"],
            started_at=_iso(r["started_at"]),
            finished_at=_iso(r.get("finished_at")),
            duration_ms=r.get("duration_ms"),
        )
        for r in rows
    ]
