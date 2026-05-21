"""
Filesystem watcher, polling loop over /data/tenants/*/incoming/.
Ingests files via the RAG API, then moves them to processed/.
"""

import base64
import logging
import os
import shutil
import time
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

RAG_API = os.environ.get("RAG_API", "http://superlinked-rag:8200")
WATCH_ROOT = os.environ.get("WATCH_ROOT", "/data/tenants")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "10"))

SUPPORTED_EXT = {".pdf", ".txt", ".md"}


def _infer_metadata(path: Path) -> dict:
    """
    Best-effort metadata from filename/path.
    date_filed is intentionally omitted so ingest.py defaults to file mtime
    (Pitfall 3 mitigation: avoids epoch-0 negative_filter penalty).
    """
    stat = path.stat()
    return {
        "title": path.stem,
        "jurisdiction": "OTHER",
        "doc_type": "memo",
        "citation": "",
        "date_filed": None,
        "source_doc": path.name,
        "mtime": int(stat.st_mtime),
    }


def _ingest_file(path: Path, tenant_id: str) -> bool:
    content = path.read_bytes()
    meta = _infer_metadata(path)
    payload = {
        "tenant_id": tenant_id,
        "filename": path.name,
        "content_b64": base64.b64encode(content).decode(),
        **meta,
    }
    try:
        resp = httpx.post(
            f"{RAG_API}/rag/ingest",
            json=payload,
            headers={"X-Consumer-Username": tenant_id},
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("skipped"):
            log.info("SKIP already-ingested: %s", path)
        else:
            log.info("OK chunks=%d: %s", data.get("chunks_ingested", 0), path)
        return True
    except Exception as exc:
        log.error("FAIL %s: %s", path, exc)
        return False


def _move_to_processed(path: Path, tenant_id: str) -> None:
    processed = Path(WATCH_ROOT) / tenant_id / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    dest = processed / path.name
    if dest.exists():
        dest = processed / f"{path.stem}_{int(time.time())}{path.suffix}"
    shutil.move(str(path), str(dest))
    log.info("MOVED -> %s", dest)


def poll_once() -> None:
    root = Path(WATCH_ROOT)
    if not root.is_dir():
        return
    for tenant_dir in sorted(root.iterdir()):
        if not tenant_dir.is_dir():
            continue
        tenant_id = tenant_dir.name
        incoming = tenant_dir / "incoming"
        if not incoming.is_dir():
            continue
        for file_path in sorted(incoming.iterdir()):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in SUPPORTED_EXT:
                continue
            if _ingest_file(file_path, tenant_id):
                _move_to_processed(file_path, tenant_id)


def main() -> None:
    log.info(
        "RAG ingest worker started. WATCH_ROOT=%s POLL_INTERVAL=%ss",
        WATCH_ROOT,
        POLL_INTERVAL,
    )
    while True:
        try:
            poll_once()
        except Exception as exc:
            log.error("poll_once error: %s", exc)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
