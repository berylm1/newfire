import base64
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .embed import REDIS_HOST, REDIS_PORT, startup_check
from .ingest import ingest_document
from .schema import index, legal_doc
from .schema import query as legal_query

try:
    from superlinked import framework as sl
    from superlinked.framework.dsl.storage.redis import RedisVectorDatabase
except ImportError as _e:  # pragma: no cover (only fails outside container)
    raise RuntimeError(f"superlinked package not installed: {_e}") from _e


# Per-tenant executor cache (Pitfall 2 mitigation: one Redis index per tenant)
_executor_cache: dict[str, tuple] = {}
_cache_lock = threading.Lock()


def _get_executor(tenant_id: str) -> tuple:
    """Return (source, app) for tenant, lazily initialising with its own Redis index."""
    with _cache_lock:
        if tenant_id not in _executor_cache:
            vector_db = RedisVectorDatabase(
                host=REDIS_HOST,
                port=REDIS_PORT,
                default_query_limit=50,
                index_name=f"legal_{tenant_id}",  # Pitfall 2: isolated ANN space per tenant
            )
            source = sl.InMemorySource(legal_doc)
            executor = sl.InMemoryExecutor(
                sources=[source],
                indices=[index],
                vector_database=vector_db,
            )
            sl_app = executor.run()
            _executor_cache[tenant_id] = (source, sl_app)
    return _executor_cache[tenant_id]


def _assert_tenant(header_user: Optional[str], body_tenant: str) -> None:
    if header_user != body_tenant:
        raise HTTPException(
            status_code=403,
            detail=(
                f"X-Consumer-Username '{header_user}' does not match "
                f"tenant_id '{body_tenant}'"
            ),
        )


# Request and Response models

class Filters(BaseModel):
    jurisdiction: Optional[str] = None
    date_after: Optional[int] = None
    doc_type: Optional[str] = None


class Weights(BaseModel):
    text: float = 0.55
    recency: float = 0.25
    jurisdiction: float = 0.12
    doc_type: float = 0.08


class RagQuery(BaseModel):
    tenant_id: str
    query: str = Field(..., min_length=3)
    top_k: int = 8
    filters: Filters = Field(default_factory=Filters)
    weights: Weights = Field(default_factory=Weights)
    pref_jurisdiction: Optional[str] = None
    pref_doc_type: Optional[str] = None


class Citation(BaseModel):
    doc_id: str
    source_doc: str
    title: str
    citation: str
    jurisdiction: str
    doc_type: str
    date_filed: int
    chunk_idx: int
    score: float
    snippet: str


class QueryResponse(BaseModel):
    tenant_id: str
    results: list[Citation]


class IngestRequest(BaseModel):
    tenant_id: str
    filename: str
    content_b64: str  # base64-encoded file bytes
    title: str
    jurisdiction: str
    doc_type: str
    citation: str = ""
    date_filed: Optional[int] = None
    source_doc: str = ""
    mtime: Optional[int] = None


class IngestResponse(BaseModel):
    tenant_id: str
    source_doc: str
    chunks_ingested: int
    skipped: bool


# App

@asynccontextmanager
async def lifespan(application: FastAPI):
    # Pitfall 1: fail-closed at startup, asserts SIE dim and Redis fingerprint
    startup_check()
    yield


app = FastAPI(title="Superlinked RAG", version="0.1", lifespan=lifespan)


# Endpoints

@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


def _entry_fields(entry: Any) -> dict:
    """Extract field dict from a Superlinked result entry regardless of API version."""
    obj = getattr(entry, "stored_object", entry)
    if isinstance(obj, dict):
        return obj
    return {
        field: getattr(obj, field, None)
        for field in (
            "doc_id", "source_doc", "title", "citation",
            "jurisdiction", "doc_type", "date_filed", "chunk_idx", "body_text",
        )
    }


@app.post("/rag/query", response_model=QueryResponse)
async def rag_query(
    body: RagQuery,
    x_consumer_username: Optional[str] = Header(None),
) -> QueryResponse:
    _assert_tenant(x_consumer_username, body.tenant_id)
    _, sl_app = _get_executor(body.tenant_id)

    result = sl_app.query(
        legal_query,
        query_text=body.query,
        tenant_id=body.tenant_id,
        top_k=body.top_k,
        w_text=body.weights.text,
        w_recency=body.weights.recency,
        w_jur=body.weights.jurisdiction,
        w_type=body.weights.doc_type,
        pref_jurisdiction=body.pref_jurisdiction or "",
        pref_doc_type=body.pref_doc_type or "",
        date_after=body.filters.date_after or 0,
        jur_eq=body.filters.jurisdiction,
        type_eq=body.filters.doc_type,
    )

    citations: list[Citation] = []

    # Handle result as iterable of entries (Superlinked v12+ standard)
    entries = getattr(result, "entries", result)
    for entry in entries:
        fields = _entry_fields(entry)
        body_text = str(fields.get("body_text") or "")
        citations.append(
            Citation(
                doc_id=str(fields.get("doc_id") or ""),
                source_doc=str(fields.get("source_doc") or ""),
                title=str(fields.get("title") or ""),
                citation=str(fields.get("citation") or ""),
                jurisdiction=str(fields.get("jurisdiction") or ""),
                doc_type=str(fields.get("doc_type") or ""),
                date_filed=int(fields.get("date_filed") or 0),
                chunk_idx=int(fields.get("chunk_idx") or 0),
                score=float(getattr(entry, "score", 0.0)),
                snippet=body_text[:300],
            )
        )

    return QueryResponse(tenant_id=body.tenant_id, results=citations)


@app.post("/rag/ingest", response_model=IngestResponse)
async def rag_ingest(
    body: IngestRequest,
    x_consumer_username: Optional[str] = Header(None),
) -> IngestResponse:
    _assert_tenant(x_consumer_username, body.tenant_id)

    content = base64.b64decode(body.content_b64)
    effective_mtime = body.mtime or int(time.time())
    source_doc = body.source_doc or body.filename

    records = ingest_document(
        content=content,
        filename=body.filename,
        tenant_id=body.tenant_id,
        title=body.title,
        jurisdiction=body.jurisdiction,
        doc_type=body.doc_type,
        citation=body.citation,
        date_filed=body.date_filed,
        source_doc=source_doc,
        mtime=effective_mtime,
    )

    if records is None:
        return IngestResponse(
            tenant_id=body.tenant_id,
            source_doc=source_doc,
            chunks_ingested=0,
            skipped=True,
        )

    source, _ = _get_executor(body.tenant_id)
    source.put(records)

    return IngestResponse(
        tenant_id=body.tenant_id,
        source_doc=source_doc,
        chunks_ingested=len(records),
        skipped=False,
    )
