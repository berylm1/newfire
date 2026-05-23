import asyncpg
import json
import logging
from typing import Optional
from .config import settings

log = logging.getLogger("openclaw.db")

_pool: Optional[asyncpg.Pool] = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool
    log.info("connecting pool host=%s db=%s user=%s schema=%s",
             settings.db_host, settings.db_name, settings.db_user, settings.db_schema)
    _pool = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        min_size=1,
        max_size=10,
        server_settings={"search_path": f"{settings.db_schema},public"},
    )
    return _pool


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialized")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def upsert_developer(email: str, display_name: Optional[str] = None) -> dict:
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            insert into openclaw.developers (email, display_name)
            values ($1, $2)
            on conflict (email) do update
                set last_seen_at = now(),
                    display_name = coalesce(excluded.display_name, openclaw.developers.display_name)
            returning email, display_name, first_seen_at, last_seen_at
            """,
            email, display_name,
        )
        return dict(row)


async def record_dispatch(
    owner_email: str,
    prompt_snippet: str,
    picked_tool: str,
    picked_reason: str,
    project_id: Optional[int] = None,
) -> int:
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            insert into openclaw.dispatches
                (owner_email, project_id, prompt_snippet, picked_tool, picked_reason)
            values ($1, $2, $3, $4, $5)
            returning id
            """,
            owner_email, project_id, prompt_snippet, picked_tool, picked_reason,
        )
        return row["id"]


async def create_run(
    dispatch_id: int,
    owner_email: str,
    tool: str,
    prompt: str,
    workspace_path: Optional[str] = None,
) -> int:
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            insert into openclaw.runs (dispatch_id, owner_email, tool, prompt, status, workspace_path)
            values ($1, $2, $3, $4, 'pending', $5)
            returning id
            """,
            dispatch_id, owner_email, tool, prompt, workspace_path,
        )
        return row["id"]


async def update_run_running(run_id: int) -> None:
    async with pool().acquire() as conn:
        await conn.execute("update openclaw.runs set status='running' where id=$1", run_id)


async def complete_run(
    run_id: int,
    status: str,
    output: Optional[str] = None,
    error: Optional[str] = None,
    model: Optional[str] = None,
    duration_ms: Optional[int] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    finish_reason: Optional[str] = None,
    truncated: Optional[bool] = None,
    files_written: Optional[list] = None,
    workspace_path: Optional[str] = None,
) -> None:
    async with pool().acquire() as conn:
        await conn.execute(
            """
            update openclaw.runs
               set status=$2,
                   output=$3,
                   error=$4,
                   model=coalesce($5, model),
                   duration_ms=$6,
                   tokens_in=$7,
                   tokens_out=$8,
                   finish_reason=$9,
                   truncated=coalesce($10, truncated),
                   files_written=$11::jsonb,
                   workspace_path=coalesce($12, workspace_path),
                   finished_at=now()
             where id=$1
            """,
            run_id, status, output, error, model, duration_ms, tokens_in, tokens_out,
            finish_reason, truncated,
            json.dumps(files_written) if files_written is not None else None,
            workspace_path,
        )


async def get_run(run_id: int, owner_email: str) -> Optional[dict]:
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            select id, dispatch_id, owner_email, tool, model, prompt, status,
                   output, error, started_at, finished_at, duration_ms,
                   tokens_in, tokens_out, finish_reason, truncated,
                   workspace_path, files_written
              from openclaw.runs
             where id=$1 and owner_email=$2
            """,
            run_id, owner_email,
        )
        if not row:
            return None
        d = dict(row)
        if d.get("files_written") is not None:
            d["files_written"] = json.loads(d["files_written"]) if isinstance(d["files_written"], str) else d["files_written"]
        return d


async def list_recent_runs(owner_email: str, limit: int = 25) -> list[dict]:
    async with pool().acquire() as conn:
        rows = await conn.fetch(
            """
            select id, tool, model, status, truncated,
                   substring(prompt, 1, 120) as prompt_snippet,
                   started_at, finished_at, duration_ms
              from openclaw.runs
             where owner_email=$1
          order by started_at desc
             limit $2
            """,
            owner_email, limit,
        )
        return [dict(r) for r in rows]
