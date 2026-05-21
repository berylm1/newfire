# Superlinked RAG Service — Technical Blueprint
**Tenant:** Funmi (immigration law) · **Host:** Minisforum control plane · **Service:** `superlinked-rag` on `:8200`

---

## 0. Architecture at a glance

```
APISIX :9080 ──(X-Consumer-Username: funmi)──▶ newfire_backend ──▶ superlinked-rag :8200
                                                                        │
                                                                        ├── SIE bge-m3 :8089   (embeddings, primary)
                                                                        ├── Ollama nomic :11434 (fallback only, NOT mixed)
                                                                        ├── Redis :6379        (Superlinked executor backend)
                                                                        └── Postgres           (ingest manifest / idempotency)
```

One Superlinked app per tenant index namespace. `tenant_id` is a hard pre-filter built into the index, not a soft query weight.

---

## 1. Superlinked Schema

File: `superlinked_rag/app/schema.py`

```python
from datetime import timedelta
from superlinked import framework as sl

class LegalDocument(sl.Schema):
    doc_id:       sl.IdField
    tenant_id:    sl.String          # hard filter, never weighted
    title:        sl.String
    body_text:    sl.String          # chunk text, not full doc
    jurisdiction: sl.String          # "US-9CIR", "US-BIA", "US-INA", "UK-UT-IAC", ...
    doc_type:     sl.String          # "statute" | "case" | "memo" | "brief" | "regulation"
    date_filed:   sl.Timestamp
    citation:     sl.String          # bluebook string, returned but not indexed
    source_doc:   sl.String          # parent doc id for chunk grouping
    chunk_idx:    sl.Integer

legal_doc = LegalDocument()

# --- Spaces -----------------------------------------------------------------
# bge-m3 = 1024-dim. Lock the model name; mismatched dims corrupt the index.
text_space = sl.TextSimilaritySpace(
    text=legal_doc.body_text,
    model="BAAI/bge-m3",            # served via SIE :8089
)

# Half-life tuned to immigration practice: policy shifts on ~3y cycles;
# 2024 precedent should clearly outrank 2018 at equal text sim.
recency_space = sl.RecencySpace(
    timestamp=legal_doc.date_filed,
    period_time_list=[
        sl.PeriodTime(timedelta(days=365),  weight=1.0),   # last year: strongest
        sl.PeriodTime(timedelta(days=365*3), weight=0.6),
        sl.PeriodTime(timedelta(days=365*10), weight=0.2),
    ],
    negative_filter=-0.5,   # docs older than 10y get a real penalty, not 0
)

jurisdiction_space = sl.CategoricalSimilaritySpace(
    category_input=legal_doc.jurisdiction,
    categories=[
        "US-SCOTUS","US-BIA","US-AAO","US-INA","US-CFR",
        "US-1CIR","US-2CIR","US-3CIR","US-4CIR","US-5CIR",
        "US-6CIR","US-7CIR","US-8CIR","US-9CIR","US-10CIR","US-11CIR","US-DCCIR",
        "UK-UT-IAC","CA-IRB","OTHER",
    ],
    negative_filter=-0.2,
    uncategorized_as_category=True,
)

doc_type_space = sl.CategoricalSimilaritySpace(
    category_input=legal_doc.doc_type,
    categories=["statute","regulation","case","memo","brief","policy"],
    negative_filter=0.0,
    uncategorized_as_category=False,
)

# --- Index ------------------------------------------------------------------
# tenant_id is a HARD FILTER field, NOT a space. Bake it in at index time.
index = sl.Index(
    spaces=[text_space, recency_space, jurisdiction_space, doc_type_space],
    fields=[legal_doc.tenant_id, legal_doc.doc_type,
            legal_doc.jurisdiction, legal_doc.date_filed],
)
```

### Default query (legal preset)

```python
query = (
    sl.Query(index, weights={
        text_space:         sl.Param("w_text",   default=0.55),
        recency_space:      sl.Param("w_recency",default=0.25),
        jurisdiction_space: sl.Param("w_jur",    default=0.12),
        doc_type_space:     sl.Param("w_type",   default=0.08),
    })
    .find(legal_doc)
    .similar(text_space.text, sl.Param("query_text"))
    .similar(jurisdiction_space.category, sl.Param("pref_jurisdiction"))
    .similar(doc_type_space.category,     sl.Param("pref_doc_type"))
    .filter(legal_doc.tenant_id == sl.Param("tenant_id"))      # HARD
    .filter(legal_doc.date_filed  >= sl.Param("date_after",  default=0))
    .filter(legal_doc.jurisdiction == sl.Param("jur_eq", default=None))
    .filter(legal_doc.doc_type     == sl.Param("type_eq", default=None))
    .limit(sl.Param("top_k", default=8))
    .select_all()
)
```

Weights chosen for immigration practice: text 0.55 (relevance still dominates), recency 0.25, jurisdiction 0.12, doc_type 0.08.

---

## 2. Ingestion Pipeline

### 2.1 Source layout

```
/data/tenants/funmi/incoming/   # drop zone
/data/tenants/funmi/processed/  # moved here after ingest
/data/tenants/funmi/manifest.db # sqlite: sha256 -> doc_id
```

### 2.2 Chunking — 512 tokens, 64 overlap

```python
import tiktoken
from pypdf import PdfReader

ENC = tiktoken.get_encoding("cl100k_base")
CHUNK, OVERLAP = 512, 64

def chunk_text(text: str):
    toks = ENC.encode(text)
    i = 0
    while i < len(toks):
        window = toks[i:i+CHUNK]
        yield ENC.decode(window)
        i += CHUNK - OVERLAP
```

### 2.3 Embeddings — bge-m3 via SIE :8089

```python
EMBED_URL = "http://sie:8089/embed"
EMBED_DIM = 1024
EMBED_MODEL = "bge-m3"
```

Hard rule: if SIE is down, 503. Never runtime-fallback to nomic (768 vs 1024 dim mismatch corrupts the index).

### 2.4 Storage — Redis-Stack (RediSearch required)

```python
from superlinked import framework as sl
from superlinked.framework.dsl.storage.redis import RedisVectorDatabase

vector_db = RedisVectorDatabase(
    host="redis-rag", port=6379, default_query_limit=50,
)
```

### 2.5 Idempotency

SHA256 of file bytes → manifest.db. Re-ingest of same SHA is no-op.

---

## 3. Query API (FastAPI)

`POST /rag/query`, `POST /rag/ingest`, `GET /healthz`. Auth via `X-Consumer-Username` header (set by APISIX from consumer key). Enforce `header_user == body.tenant_id` → 403 on mismatch.

```python
class Filters(BaseModel):
    jurisdiction: Optional[str] = None
    date_after:   Optional[int] = None
    doc_type:     Optional[str] = None

class Weights(BaseModel):
    text: float = 0.55
    recency: float = 0.25
    jurisdiction: float = 0.12
    doc_type: float = 0.08

class RagQuery(BaseModel):
    tenant_id: str
    query: str = Field(..., min_length=3)
    top_k: int = 8
    filters: Filters = Filters()
    weights: Weights = Weights()
    pref_jurisdiction: Optional[str] = None
    pref_doc_type: Optional[str] = None
```

Returns ranked Citation objects: doc_id, source_doc, title, citation, jurisdiction, doc_type, date_filed, chunk_idx, score, snippet.

APISIX overlay route for `/rag/*` with `key-auth` plugin and `proxy-rewrite` to inject `X-Consumer-Username: $consumer_name`.

---

## 4. docker-compose (overlay)

Port 8200 (verified non-conflicting). Redis on internal 6379 (no host bind).

```yaml
version: "3.9"
services:
  superlinked-rag:
    build: { context: ../superlinked_rag, dockerfile: Dockerfile }
    image: newfire/superlinked-rag:0.1
    container_name: superlinked-rag
    restart: unless-stopped
    ports: ["8200:8200"]
    environment:
      EMBED_URL: "http://sie:8089/embed"
      EMBED_MODEL: "bge-m3"
      EMBED_DIM: "1024"
      REDIS_HOST: "redis-rag"
      REDIS_PORT: "6379"
    depends_on:
      redis-rag: { condition: service_healthy }
    networks: [newfire_net]
    volumes: ["/data/tenants:/data/tenants:ro"]

  redis-rag:
    image: redis/redis-stack-server:7.2.0-v10
    container_name: redis-rag
    restart: unless-stopped
    command: ["redis-stack-server","--appendonly","yes","--save","60","1000"]
    volumes: ["redis_rag_data:/data"]
    healthcheck:
      test: ["CMD","redis-cli","ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    networks: [newfire_net]

  rag-ingest-worker:
    build: { context: ../superlinked_rag, dockerfile: Dockerfile.worker }
    container_name: rag-ingest-worker
    restart: unless-stopped
    environment:
      RAG_API: "http://superlinked-rag:8200"
      WATCH_ROOT: "/data/tenants"
    volumes: ["/data/tenants:/data/tenants"]
    depends_on: [superlinked-rag]
    networks: [newfire_net]

volumes:
  redis_rag_data:

networks:
  newfire_net:
    external: true
```

Dockerfile:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential poppler-utils && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8200
CMD ["uvicorn","app.api:app","--host","0.0.0.0","--port","8200","--workers","2"]
```

requirements.txt:

```
superlinked>=12.0.0
fastapi>=0.110
uvicorn[standard]>=0.27
redis>=5.0
pypdf>=4.0
tiktoken>=0.7
httpx>=0.27
pydantic>=2.6
```

---

## 5. Three pitfalls

### Pitfall 1 — Embedding dimension drift (bge-m3=1024 vs nomic=768)
Superlinked bakes dim into index on first write. If anyone "temporarily" repoints EMBED_URL to Ollama during SIE outage, vectors become silently unsearchable garbage; error surfaces only as poor relevance. **Mitigation:** fail-closed at startup. Fetch SIE healthz, assert model name and dim. Store `rag:embed:fingerprint` in Redis on first ingest; refuse boot on mismatch. Never implement runtime fallback.

### Pitfall 2 — tenant_id as filter is not enough
Even with `.filter(tenant_id==...)`, ANN search ranks across all tenants first then filters, leaking recall budget and risking <top_k on small tenants. **Mitigation:** per-tenant Redis index namespace (`index_name=f"legal_{tenant_id}"`). One executor per tenant, lazy-loaded dict. Tenant deletion = `FT.DROPINDEX` (GDPR-friendly).

### Pitfall 3 — RecencySpace with missing dates collapses ranking
Half of immigration corpus (memos, policy PDFs) have no machine-readable date. Superlinked treats `0`/`None` as epoch 1970, dropping docs below the negative_filter floor — they vanish even on perfect text match. **Mitigation:** in ingest worker, default missing `date_filed` to **file mtime** (not epoch, not now). Flag `date_inferred=true` in citation. Use `negative_filter=-0.5` (not `-1.0`) so undated docs remain retrievable on high text sim.

---

## 6. Builder checklist

1. Scaffold `superlinked_rag/app/{schema.py, api.py, ingest.py, embed.py, __init__.py}`.
2. Write `Dockerfile`, `Dockerfile.worker`, `requirements.txt`.
3. Add `docker-compose.superlinked.yml` overlay.
4. Add `apisix_route_rag.yaml`.
5. Add `README.md` with bring-up commands + smoke test curl.
6. Add `scripts/smoke_test.sh` that hits /healthz and posts a sample query.
