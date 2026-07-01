import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient

from activity_log_service import main


def _test_client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "LOG_PATH", str(tmp_path / "activity_log.jsonl"))
    return TestClient(main.app)


def test_health_returns_ok():
    client = TestClient(main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_event_returns_record_with_submitted_fields(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.post(
        "/events",
        json={"event_type": "email_sent", "urgency": "low", "summary": "sent intake confirmation"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "email_sent"
    assert body["urgency"] == "low"
    assert body["summary"] == "sent intake confirmation"
    assert "timestamp" in body


def test_create_event_missing_field_returns_422(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.post("/events", json={"event_type": "email_sent", "urgency": "low"})

    assert response.status_code == 422


def test_get_todays_events_returns_empty_list_when_no_log_file(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.get("/events/today")

    assert response.status_code == 200
    assert response.json() == []


def test_get_todays_events_returns_only_todays_events_most_recent_first(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    log_path = tmp_path / "activity_log.jsonl"
    old_record = {
        "type": "call",
        "urgency": "low",
        "summary": "old call",
        "timestamp": "2020-01-01T00:00:00+00:00",
    }
    log_path.write_text(json.dumps(old_record) + "\n", encoding="utf-8")

    client.post("/events", json={"event_type": "call", "urgency": "high", "summary": "urgent client call"})
    client.post("/events", json={"event_type": "email_sent", "urgency": "low", "summary": "follow up email"})

    response = client.get("/events/today")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["summary"] == "follow up email"
    assert body[1]["summary"] == "urgent client call"
