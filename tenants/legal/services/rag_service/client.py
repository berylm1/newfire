"""Client for the RAG service — same drop-in style as the activity log and
conflicts service clients (client.py alongside main.py, one function per
endpoint, base URL from an env var).
"""

import os

import requests

BASE_URL = os.environ.get("RAG_SERVICE_URL", "http://localhost:8003")


def add_document(text: str, metadata: dict | None = None) -> str:
    response = requests.post(
        f"{BASE_URL}/documents",
        json={"text": text, "metadata": metadata or {}},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["id"]


def search(query: str, top_k: int = 5) -> list[dict]:
    response = requests.post(
        f"{BASE_URL}/search",
        json={"query": query, "top_k": top_k},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def delete_document(document_id: str) -> None:
    requests.delete(f"{BASE_URL}/documents/{document_id}", timeout=10).raise_for_status()
