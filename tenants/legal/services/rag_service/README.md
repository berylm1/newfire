# RAG Service

Vector search over a tenant's own document corpus — the piece that lets an
agent answer from case documents and precedent instead of only what fits in
its context window.

Documents get embedded and stored in Qdrant. A search request embeds the
query the same way and returns the closest matches by cosine similarity.

## Endpoints

`POST /documents` — body `{"text": "...", "metadata": {...}}`, embeds and
stores the document, returns `{"id": "<uuid>"}`.

`POST /search` — body `{"query": "...", "top_k": 5}`, returns a list of
`{"id", "score", "text", "metadata"}` ordered by relevance.

`DELETE /documents/{id}` — removes a stored document by id.

`GET /health` — liveness check.

## Embeddings

Uses the tenant's existing self-hosted Ollama instance on the DGX
(`100.88.112.5:11434`, same box `shared/document_vision.py` talks to for
vision) with the `nomic-embed-text` model — confirmed installed and reachable
from the gateway box, 768-dimension vectors. Configurable via
`OLLAMA_EMBEDDING_BASE_URL` and `EMBEDDING_MODEL` if that ever changes.

No local fallback embedding model was needed since the DGX endpoint is
reachable and already used elsewhere in this tenant.

## Storage

Qdrant, running as a Docker container on the gateway box bound to
`127.0.0.1:6333` (REST) / `127.0.0.1:6334` (gRPC) — not exposed publicly, same
as the other two services in this directory. Collection name defaults to
`legal_documents`, created automatically on first startup if it doesn't
already exist. Point at a different instance with `QDRANT_URL`.

## Running locally

```
pip install -r requirements.txt
uvicorn rag_service.main:app --port 8003
```

Agents pick this up via `RAG_SERVICE_URL` (defaults to
`http://localhost:8003`). Import `client.py` for `add_document`, `search`,
and `delete_document`.

In production this runs as `legal-rag.service` on port 8103, same pattern as
`legal-activity-log` (8101) and `legal-conflicts` (8102).
