from fastapi import APIRouter, Depends, HTTPException

from ..auth import authenticate
from ..db import get_run, list_recent_runs
from ..schemas import RunResponse, RunSummary

router = APIRouter()


def _iso(dt) -> str | None:
    return dt.isoformat() if dt is not None else None


@router.get("/v1/runs/{run_id}", response_model=RunResponse)
async def get_run_route(run_id: int, email: str = Depends(authenticate)) -> RunResponse:
    row = await get_run(run_id, email)
    if row is None:
        raise HTTPException(404, f"run {run_id} not found for {email}")
    return RunResponse(
        id=row["id"],
        dispatch_id=row["dispatch_id"],
        tool=row["tool"],
        model=row["model"],
        status=row["status"],
        prompt=row["prompt"],
        output=row["output"],
        error=row["error"],
        started_at=_iso(row["started_at"]),
        finished_at=_iso(row["finished_at"]),
        duration_ms=row["duration_ms"],
        tokens_in=row["tokens_in"],
        tokens_out=row["tokens_out"],
    )


@router.get("/v1/runs", response_model=list[RunSummary])
async def list_runs(email: str = Depends(authenticate)) -> list[RunSummary]:
    rows = await list_recent_runs(email)
    return [
        RunSummary(
            id=r["id"],
            tool=r["tool"],
            model=r["model"],
            status=r["status"],
            prompt_snippet=r["prompt_snippet"],
            started_at=_iso(r["started_at"]),
            finished_at=_iso(r["finished_at"]),
            duration_ms=r["duration_ms"],
        )
        for r in rows
    ]
