import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient

from notify_service import backends, main


def _test_client(tmp_path, monkeypatch):
    monkeypatch.setattr(backends, "SENT_LOG_PATH", str(tmp_path / "sent_log.json"))
    return TestClient(main.app)


def _notify(client, tenant_id="acme-legal", channel="email", to="attorney@example.com", body="text", subject=None):
    return client.post(
        "/notify", json={"tenant_id": tenant_id, "channel": channel, "to": to, "subject": subject, "body": body}
    )


def test_health_returns_ok():
    client = TestClient(main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_notify_email_returns_sent_record(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = _notify(client, channel="email", to="attorney@example.com", subject="Morning briefing", body="text")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sent"
    assert body["channel"] == "email"
    assert body["to"] == "attorney@example.com"
    assert body["subject"] == "Morning briefing"
    assert body["body"] == "text"
    assert "id" in body
    assert "sent_at" in body


def test_notify_whatsapp_is_a_supported_channel(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = _notify(client, channel="whatsapp", to="+15551234567")

    assert response.status_code == 200
    assert response.json()["channel"] == "whatsapp"


def test_notify_unsupported_channel_returns_422(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = _notify(client, channel="carrier_pigeon")

    assert response.status_code == 422


def test_notify_missing_required_field_returns_422(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.post("/notify", json={"tenant_id": "acme-legal", "channel": "email", "to": "a@b.com"})

    assert response.status_code == 422


def test_notify_does_not_call_any_external_service(tmp_path, monkeypatch):
    # The whole point of the stub backend: no network call, no external
    # dependency, just a durable local record of the attempt.
    client = _test_client(tmp_path, monkeypatch)

    response = _notify(client)

    assert response.status_code == 200
    assert os.path.exists(str(tmp_path / "sent_log.json"))


def test_get_notify_log_returns_all_entries(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    _notify(client, tenant_id="acme-legal", body="first")
    _notify(client, tenant_id="acme-legal", body="second")

    response = client.get("/notify/log")

    assert response.status_code == 200
    bodies = [e["body"] for e in response.json()]
    assert bodies == ["first", "second"]


def test_get_notify_log_filters_by_tenant_id(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    _notify(client, tenant_id="acme-legal", body="acme's message")
    _notify(client, tenant_id="other-firm", body="other firm's message")

    response = client.get("/notify/log", params={"tenant_id": "acme-legal"})

    assert response.status_code == 200
    bodies = [e["body"] for e in response.json()]
    assert bodies == ["acme's message"]


def test_get_notify_log_empty_when_nothing_sent(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.get("/notify/log")

    assert response.status_code == 200
    assert response.json() == []
