from fastapi import APIRouter
from ..db import pool

router = APIRouter()


@router.get("/v1/health")
async def health() -> dict:
    out = {"status": "ok"}
    try:
        async with pool().acquire() as conn:
            v = await conn.fetchval("select 1")
            out["db"] = "ok" if v == 1 else "unexpected"
    except Exception as e:
        out["status"] = "degraded"
        out["db"] = f"error: {e.__class__.__name__}"
    return out
