import hashlib
import io
import os
import sqlite3
import time
from pathlib import Path

import tiktoken
from pypdf import PdfReader

ENC = tiktoken.get_encoding("cl100k_base")
CHUNK_SIZE = 512
OVERLAP = 64
MANIFEST_ROOT = os.environ.get("MANIFEST_ROOT", "/data/tenants")


def _manifest_conn(tenant_id: str) -> sqlite3.Connection:
    db_path = Path(MANIFEST_ROOT) / tenant_id / "manifest.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS docs "
        "(sha256 TEXT PRIMARY KEY, source_doc TEXT, ingested_at INTEGER)"
    )
    conn.commit()
    return conn


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extract_text(content: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return content.decode("utf-8", errors="replace")


def chunk_text(text: str):
    tokens = ENC.encode(text)
    i = 0
    while i < len(tokens):
        window = tokens[i : i + CHUNK_SIZE]
        yield ENC.decode(window)
        i += CHUNK_SIZE - OVERLAP


def ingest_document(
    *,
    content: bytes,
    filename: str,
    tenant_id: str,
    title: str,
    jurisdiction: str,
    doc_type: str,
    citation: str,
    date_filed: int | None,
    source_doc: str,
    mtime: int,
) -> list[dict] | None:
    """
    Extract, chunk, and build Superlinked records for one document.

    Returns None if the sha256 is already in the manifest (idempotent).

    Pitfall 3 mitigation: when date_filed is absent, default to file mtime
    (not epoch-0).  Epoch-0 triggers negative_filter=-0.5, making docs
    invisible even on high text similarity.  mtime keeps them retrievable.
    Flag the citation string so callers know the date was inferred.
    """
    sha = _sha256(content)
    conn = _manifest_conn(tenant_id)
    try:
        if conn.execute("SELECT 1 FROM docs WHERE sha256=?", (sha,)).fetchone():
            return None

        date_inferred = date_filed is None
        effective_date = date_filed if date_filed is not None else mtime
        flagged_citation = f"{citation} [date-inferred]" if date_inferred else citation

        text = _extract_text(content, filename)
        doc_id_base = sha[:16]

        records = [
            {
                "doc_id": f"{doc_id_base}_{idx}",
                "tenant_id": tenant_id,
                "title": title,
                "body_text": chunk,
                "jurisdiction": jurisdiction,
                "doc_type": doc_type,
                "date_filed": effective_date,
                "citation": flagged_citation,
                "source_doc": source_doc,
                "chunk_idx": idx,
            }
            for idx, chunk in enumerate(chunk_text(text))
            if chunk.strip()
        ]

        conn.execute(
            "INSERT INTO docs (sha256, source_doc, ingested_at) VALUES (?,?,?)",
            (sha, source_doc, int(time.time())),
        )
        conn.commit()
        return records
    finally:
        conn.close()
