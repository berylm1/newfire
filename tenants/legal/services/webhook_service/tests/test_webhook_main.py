import hashlib
import hmac
import itertools
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient

from webhook_service import main

_tenant_ids = itertools.count()


def _sign(secret: str, raw_body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def _test_client(tmp_path, monkeypatch, secrets: dict | None = None):
    monkeypatch.setattr(main, "STORE_PATH", str(tmp_path / "webhook_events.json"))
    secrets_path = tmp_path / "webhook_secrets.json"
    secrets_path.write_text(json.dumps(secrets if secrets is not None else {}))
    monkeypatch.setattr(main, "SECRETS_PATH", str(secrets_path))
    return TestClient(main.app)


def _tenant(secret: str = "test-secret") -> tuple[str, str]:
    # Real tenants are onboarded once with a stable id, but distinct tests
    # posting events shouldn't collide on a shared default id — each test
    # that creates events gets its own tenant_id.
    tenant_id = f"tenant-{next(_tenant_ids)}"
    return tenant_id, secret


def _post_webhook(client, tenant_id, source, secret, payload):
    raw_body = json.dumps(payload).encode("utf-8")
    signature = _sign(secret, raw_body)
    return client.post(
        f"/webhooks/{tenant_id}/{source}",
        content=raw_body,
        headers={"X-Webhook-Signature": signature, "Content-Type": "application/json"},
    )


def test_health_returns_ok():
    client = TestClient(main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_with_valid_signature_is_accepted(tmp_path, monkeypatch):
    tenant_id, secret = _tenant()
    client = _test_client(tmp_path, monkeypatch, secrets={tenant_id: secret})

    response = _post_webhook(client, tenant_id, "email", secret, {"from": "a@b.com", "subject": "hi", "body": "text"})

    assert response.status_code == 202
    body = response.json()
    assert body["tenant_id"] == tenant_id
    assert body["source"] == "email"
    assert body["payload"] == {"from": "a@b.com", "subject": "hi", "body": "text"}
    assert body["processed"] is False
    assert "id" in body
    assert "received_at" in body


def test_webhook_with_missing_signature_returns_401(tmp_path, monkeypatch):
    tenant_id, secret = _tenant()
    client = _test_client(tmp_path, monkeypatch, secrets={tenant_id: secret})
    raw_body = json.dumps({"foo": "bar"}).encode("utf-8")

    response = client.post(
        f"/webhooks/{tenant_id}/email", content=raw_body, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 401


def test_webhook_with_wrong_signature_returns_401(tmp_path, monkeypatch):
    tenant_id, secret = _tenant()
    client = _test_client(tmp_path, monkeypatch, secrets={tenant_id: secret})
    raw_body = json.dumps({"foo": "bar"}).encode("utf-8")

    response = client.post(
        f"/webhooks/{tenant_id}/email",
        content=raw_body,
        headers={"X-Webhook-Signature": "0" * 64, "Content-Type": "application/json"},
    )

    assert response.status_code == 401


def test_webhook_signed_with_wrong_secret_returns_401(tmp_path, monkeypatch):
    tenant_id, secret = _tenant()
    client = _test_client(tmp_path, monkeypatch, secrets={tenant_id: secret})
    raw_body = json.dumps({"foo": "bar"}).encode("utf-8")
    wrong_signature = _sign("not-the-real-secret", raw_body)

    response = client.post(
        f"/webhooks/{tenant_id}/email",
        content=raw_body,
        headers={"X-Webhook-Signature": wrong_signature, "Content-Type": "application/json"},
    )

    assert response.status_code == 401


def test_webhook_for_unknown_tenant_returns_401(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch, secrets={})
    raw_body = json.dumps({"foo": "bar"}).encode("utf-8")
    signature = _sign("whatever", raw_body)

    response = client.post(
        "/webhooks/no-such-tenant/email",
        content=raw_body,
        headers={"X-Webhook-Signature": signature, "Content-Type": "application/json"},
    )

    assert response.status_code == 401


def test_webhook_stores_event_retrievable_by_id(tmp_path, monkeypatch):
    tenant_id, secret = _tenant()
    client = _test_client(tmp_path, monkeypatch, secrets={tenant_id: secret})
    created = _post_webhook(client, tenant_id, "contact_form", secret, {"name": "someone"}).json()

    response = client.get(f"/events/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_event_missing_returns_404(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.get("/events/does-not-exist")

    assert response.status_code == 404


def test_get_pending_events_excludes_processed(tmp_path, monkeypatch):
    tenant_id, secret = _tenant()
    client = _test_client(tmp_path, monkeypatch, secrets={tenant_id: secret})
    pending = _post_webhook(client, tenant_id, "email", secret, {"body": "one"}).json()
    processed = _post_webhook(client, tenant_id, "email", secret, {"body": "two"}).json()
    client.post(f"/events/{processed['id']}/mark_processed")

    response = client.get("/events/pending", params={"tenant_id": tenant_id})

    assert response.status_code == 200
    ids = [e["id"] for e in response.json()]
    assert pending["id"] in ids
    assert processed["id"] not in ids


def test_get_pending_events_filters_by_tenant_id(tmp_path, monkeypatch):
    tenant_a, secret_a = _tenant()
    tenant_b, secret_b = _tenant()
    client = _test_client(tmp_path, monkeypatch, secrets={tenant_a: secret_a, tenant_b: secret_b})
    _post_webhook(client, tenant_a, "email", secret_a, {"body": "a"})
    event_b = _post_webhook(client, tenant_b, "email", secret_b, {"body": "b"}).json()

    response = client.get("/events/pending", params={"tenant_id": tenant_b})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == event_b["id"]


def test_get_pending_events_filters_by_source(tmp_path, monkeypatch):
    tenant_id, secret = _tenant()
    client = _test_client(tmp_path, monkeypatch, secrets={tenant_id: secret})
    _post_webhook(client, tenant_id, "email", secret, {"body": "a"})
    contact_form = _post_webhook(client, tenant_id, "contact_form", secret, {"body": "b"}).json()

    response = client.get("/events/pending", params={"tenant_id": tenant_id, "source": "contact_form"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == contact_form["id"]


def test_mark_event_processed_transitions_and_is_excluded_from_pending(tmp_path, monkeypatch):
    tenant_id, secret = _tenant()
    client = _test_client(tmp_path, monkeypatch, secrets={tenant_id: secret})
    created = _post_webhook(client, tenant_id, "email", secret, {"body": "x"}).json()

    response = client.post(f"/events/{created['id']}/mark_processed")

    assert response.status_code == 200
    assert response.json()["processed"] is True
    pending_ids = [e["id"] for e in client.get("/events/pending").json()]
    assert created["id"] not in pending_ids


def test_mark_event_processed_missing_returns_404(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.post("/events/does-not-exist/mark_processed")

    assert response.status_code == 404


def test_mark_event_processed_twice_returns_409(tmp_path, monkeypatch):
    tenant_id, secret = _tenant()
    client = _test_client(tmp_path, monkeypatch, secrets={tenant_id: secret})
    created = _post_webhook(client, tenant_id, "email", secret, {"body": "x"}).json()
    client.post(f"/events/{created['id']}/mark_processed")

    response = client.post(f"/events/{created['id']}/mark_processed")

    assert response.status_code == 409
