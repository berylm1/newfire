"""Tests for rag_service main module."""
from unittest.mock import MagicMock, patch, AsyncMock
import pytest


@pytest.fixture(autouse=True)
def mock_qdrant():
    """Mock QdrantClient to avoid requiring a real Qdrant instance."""
    with patch("rag_service.main.QdrantClient") as mock:
        instance = MagicMock()
        instance.collection_exists.return_value = True
        mock.return_value = instance
        yield instance


@pytest.fixture(autouse=True)
def mock_embed():
    """Mock the embed function to return a deterministic vector."""
    with patch("rag_service.main.embed", return_value=[0.1] * 768):
        yield


class TestHealthEndpoint:
    def test_health_returns_ok(self, mock_qdrant):
        from fastapi.testclient import TestClient
        from rag_service.main import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestSearchEndpoint:
    @patch("rag_service.main.qdrant", new_callable=lambda: MagicMock())
    def test_search_returns_results(self, mock_qdrant_client, mock_qdrant, mock_embed):
        from fastapi.testclient import TestClient
        from rag_service.main import app

        mock_qdrant_client.search.return_value = [
            MagicMock(score=0.95, payload={"content": "test document", "filename": "test.txt"}),
        ]

        client = TestClient(app)
        response = client.post("/search", json={"query": "test query", "tenant_id": "legal"})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1


class TestAddDocumentEndpoint:
    @patch("rag_service.main.qdrant", new_callable=lambda: MagicMock())
    def test_add_document_succeeds(self, mock_qdrant_client, mock_qdrant, mock_embed):
        from fastapi.testclient import TestClient
        from rag_service.main import app

        mock_qdrant_client.upsert.return_value = MagicMock(status="completed")

        client = TestClient(app)
        response = client.post("/documents", json={
            "tenant_id": "legal",
            "filename": "test.txt",
            "content": "This is test content",
        })
        assert response.status_code in (200, 201)
