"""RAG service — gives agents a way to search a tenant's own document corpus
instead of being limited to whatever fits in the context window.

Documents get embedded with the same self-hosted Ollama instance the rest of
this tenant already talks to (nomic-embed-text on the DGX, see
shared/document_vision.py for the vision-model equivalent) and stored in
Qdrant. Search embeds the query the same way and returns the closest matches
by cosine distance.

Swappable like the rest of this tenant: point QDRANT_URL at a different
instance or EMBEDDING_MODEL at a different model and nothing calling this
service needs to change.
"""

import json
import os
import urllib.request
import uuid

from fastapi import FastAPI
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

OLLAMA_BASE_URL = os.environ.get("OLLAMA_EMBEDDING_BASE_URL", "http://100.88.112.5:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_SIZE = 768

QDRANT_URL = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333")
COLLECTION_NAME = os.environ.get("RAG_COLLECTION", "legal_documents")

app = FastAPI(title="RAG Service")
qdrant = QdrantClient(url=QDRANT_URL)

if not qdrant.collection_exists(COLLECTION_NAME):
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBEDDING_SIZE, distance=Distance.COSINE),
    )


def embed(text: str) -> list[float]:
    payload = {"model": EMBEDDING_MODEL, "prompt": text}
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["embedding"]


class DocumentIn(BaseModel):
    text: str
    metadata: dict = {}


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@app.post("/documents")
def create_document(document: DocumentIn) -> dict:
    doc_id = str(uuid.uuid4())
    vector = embed(document.text)
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[{"id": doc_id, "vector": vector, "payload": {"text": document.text, **document.metadata}}],
    )
    return {"id": doc_id}


@app.post("/search")
def search(request: SearchRequest) -> list[dict]:
    vector = embed(request.query)
    results = qdrant.query_points(collection_name=COLLECTION_NAME, query=vector, limit=request.top_k).points
    return [
        {
            "id": str(point.id),
            "score": point.score,
            "text": point.payload.get("text"),
            "metadata": {k: v for k, v in point.payload.items() if k != "text"},
        }
        for point in results
    ]


@app.delete("/documents/{document_id}")
def delete_document(document_id: str) -> dict:
    qdrant.delete(collection_name=COLLECTION_NAME, points_selector=[document_id])
    return {"deleted": document_id}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
