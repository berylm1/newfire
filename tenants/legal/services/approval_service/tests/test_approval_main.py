import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient

from approval_service import main


def _test_client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STORE_PATH", str(tmp_path / "approvals.json"))
    return TestClient(main.app)


def _create(client, tenant_id="acme-legal", thread_id="thread-1", kind="intake_memo", draft="draft text"):
    return client.post(
        "/approvals",
        json={"tenant_id": tenant_id, "thread_id": thread_id, "kind": kind, "draft": draft, "context": {"conflicts": []}},
    )


def test_health_returns_ok():
    client = TestClient(main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_approval_returns_pending_record(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = _create(client)

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "acme-legal"
    assert body["thread_id"] == "thread-1"
    assert body["kind"] == "intake_memo"
    assert body["draft"] == "draft text"
    assert body["context"] == {"conflicts": []}
    assert body["status"] == "pending"
    assert body["decided_by"] is None
    assert body["decided_at"] is None
    assert body["resumed"] is False
    assert "id" in body
    assert "created_at" in body


def test_create_approval_missing_field_returns_422(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.post("/approvals", json={"tenant_id": "acme-legal"})

    assert response.status_code == 422


def test_get_pending_approvals_returns_only_pending(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create(client).json()
    other = _create(client, tenant_id="other-firm").json()
    client.post(f"/approvals/{other['id']}/decide", json={"approved": True, "decided_by": "reviewer"})

    response = client.get("/approvals/pending")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == created["id"]


def test_get_pending_approvals_filters_by_tenant_id(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    _create(client, tenant_id="acme-legal")
    _create(client, tenant_id="other-firm")

    response = client.get("/approvals/pending", params={"tenant_id": "other-firm"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["tenant_id"] == "other-firm"


def test_get_approval_returns_record(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create(client).json()

    response = client.get(f"/approvals/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_approval_missing_returns_404(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.get("/approvals/does-not-exist")

    assert response.status_code == 404


def test_decide_approval_sets_status_and_decided_fields(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create(client).json()

    response = client.post(f"/approvals/{created['id']}/decide", json={"approved": True, "decided_by": "reviewer"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["decided_by"] == "reviewer"
    assert body["decided_at"] is not None


def test_decide_approval_rejected_sets_status_rejected(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create(client).json()

    response = client.post(f"/approvals/{created['id']}/decide", json={"approved": False, "decided_by": "reviewer"})

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_decide_approval_missing_returns_404(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.post("/approvals/does-not-exist/decide", json={"approved": True, "decided_by": "reviewer"})

    assert response.status_code == 404


def test_decide_approval_already_decided_returns_409(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create(client).json()
    client.post(f"/approvals/{created['id']}/decide", json={"approved": True, "decided_by": "reviewer"})

    response = client.post(f"/approvals/{created['id']}/decide", json={"approved": False, "decided_by": "someone-else"})

    assert response.status_code == 409


def test_get_resumable_approvals_returns_decided_not_resumed(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    pending = _create(client).json()
    decided = _create(client).json()
    client.post(f"/approvals/{decided['id']}/decide", json={"approved": True, "decided_by": "reviewer"})

    response = client.get("/approvals/resumable")

    assert response.status_code == 200
    body = response.json()
    ids = [a["id"] for a in body]
    assert decided["id"] in ids
    assert pending["id"] not in ids


def test_mark_approval_resumed_removes_it_from_resumable(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    decided = _create(client).json()
    client.post(f"/approvals/{decided['id']}/decide", json={"approved": True, "decided_by": "reviewer"})

    mark_response = client.post(f"/approvals/{decided['id']}/mark_resumed")
    resumable = client.get("/approvals/resumable").json()

    assert mark_response.status_code == 200
    assert mark_response.json()["resumed"] is True
    assert decided["id"] not in [a["id"] for a in resumable]


def test_mark_approval_resumed_missing_returns_404(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.post("/approvals/does-not-exist/mark_resumed")

    assert response.status_code == 404
