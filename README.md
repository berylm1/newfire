# Superlinked RAG Service

FastAPI service providing multi-modal retrieval-augmented generation for legal documents, running on port 8200.

## Why Superlinked over Qdrant for legal documents

Qdrant is a pure vector store: you get text similarity and nothing else out of the box. For immigration law, relevance is shaped by at least three orthogonal signals that must be composed at query time.

Superlinked bakes those signals directly into the index through typed spaces:

| Signal | Space | Weight (default) |
|---|---|---|
| Semantic text match | TextSimilaritySpace (bge-m3, 1024-dim) | 0.55 |
| Document recency | RecencySpace with 1y/3y/10y half-life tiers | 0.25 |
| Jurisdiction affinity | CategoricalSimilaritySpace (20 jurisdictions) | 0.12 |
| Document type preference | CategoricalSimilaritySpace (6 types) | 0.08 |

A 2024 BIA precedent decision will outrank an equally-relevant 2018 case automatically, without requiring application-level re-ranking logic. Callers can shift weights per query (e.g. bump `w_recency` for time-sensitive motions) without re-indexing.

## Bring-up steps

**Prerequisites:** Docker with Compose v2, the `newfire_net` external network already created, and `/data/tenants/<tenant>/incoming/` writable.

```bash
# Create the overlay network if it does not exist yet
docker network create newfire_net 2>/dev/null || true

# Build and start all three services
docker compose -f docker-compose.superlinked.yml up -d

# Tail logs to confirm startup check passes
docker logs -f superlinked-rag
```

The API is ready when you see `Application startup complete` in the logs. The embed fingerprint check runs at boot and will abort with a clear error if the SIE model or dimension does not match the stored fingerprint.

## Smoke test

```bash
export RAG_BASE=http://localhost:8200
export TENANT=funmi
bash scripts/smoke_test.sh
```

Expected output:

```
=== healthz ===
OK (200)
=== ingest ===
Ingest response: {"tenant_id":"funmi","source_doc":"smoke_test.txt","chunks_ingested":1,"skipped":false}
OK (chunks=1 skipped=False)
=== query ===
OK (results=1)
=== all checks passed ===
```

Quick manual healthcheck:

```bash
curl http://localhost:8200/healthz
```

## Three pitfalls (verbatim from architecture blueprint)

### Pitfall 1: Embedding dimension drift (bge-m3=1024 vs nomic=768)

Superlinked bakes dim into index on first write. If anyone "temporarily" repoints EMBED_URL to Ollama during SIE outage, vectors become silently unsearchable garbage; error surfaces only as poor relevance. **Mitigation:** fail-closed at startup. Fetch SIE healthz, assert model name and dim. Store `rag:embed:fingerprint` in Redis on first ingest; refuse boot on mismatch. Never implement runtime fallback.

### Pitfall 2: tenant_id as filter is not enough

Even with `.filter(tenant_id==...)`, ANN search ranks across all tenants first then filters, leaking recall budget and risking fewer than top_k results on small tenants. **Mitigation:** per-tenant Redis index namespace (`index_name=f"legal_{tenant_id}"`). One executor per tenant, lazy-loaded dict. Tenant deletion equals `FT.DROPINDEX` (GDPR-friendly).

### Pitfall 3: RecencySpace with missing dates collapses ranking

Half of immigration corpus (memos, policy PDFs) have no machine-readable date. Superlinked treats `0`/`None` as epoch 1970, dropping docs below the negative_filter floor and they vanish even on perfect text match. **Mitigation:** in ingest worker, default missing `date_filed` to **file mtime** (not epoch, not now). Flag `date_inferred=true` in citation. Use `negative_filter=-0.5` (not `-1.0`) so undated docs remain retrievable on high text sim.

## File layout

```
superlinked_rag/
  app/
    schema.py       Superlinked spaces and index definition
    embed.py        SIE client and startup fingerprint check
    ingest.py       Chunking, PDF extraction, idempotency manifest
    api.py          FastAPI endpoints (/rag/query, /rag/ingest, /healthz)
    worker.py       Polling filesystem watcher for /data/tenants/*/incoming/
  Dockerfile        API container (uvicorn on :8200)
  Dockerfile.worker Worker container (polling loop)
  requirements.txt  Pinned Python dependencies
docker-compose.superlinked.yml  Overlay compose file
apisix_route_rag.yaml           APISIX route with key-auth
scripts/smoke_test.sh           End-to-end health check
```
