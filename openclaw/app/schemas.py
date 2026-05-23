from pydantic import BaseModel, Field
from typing import Any, Optional


class WhoAmIResponse(BaseModel):
    email: str
    display_name: Optional[str] = None
    first_seen_at: str
    last_seen_at: str


class DispatchRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    project_id: Optional[int] = None
    execute: bool = False
    max_tokens: int = Field(default=2048, ge=64, le=8192)


class DispatchAlternative(BaseModel):
    tool: str
    url: str


class DispatchResponse(BaseModel):
    dispatch_id: int
    suggested_tool: str
    suggested_url: str
    alternatives: list[DispatchAlternative]
    reason: str
    run_id: Optional[int] = None


class FileWritten(BaseModel):
    filename: str
    language: Optional[str] = None
    size: int
    source: Optional[str] = None  # header, first_line, fallback
    path: Optional[str] = None


class RunResponse(BaseModel):
    id: int
    dispatch_id: int
    tool: str
    model: Optional[str] = None
    status: str
    prompt: str
    output: Optional[str] = None
    error: Optional[str] = None
    started_at: str
    finished_at: Optional[str] = None
    duration_ms: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    finish_reason: Optional[str] = None
    truncated: bool = False
    workspace_path: Optional[str] = None
    files_written: Optional[list[FileWritten]] = None


class RunSummary(BaseModel):
    id: int
    tool: str
    model: Optional[str] = None
    status: str
    truncated: bool = False
    prompt_snippet: str
    started_at: str
    finished_at: Optional[str] = None
    duration_ms: Optional[int] = None
