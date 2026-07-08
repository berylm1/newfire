import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient

from memory_service import main


def _test_client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STORE_PATH", str(tmp_path / "memory_notes.json"))
    return TestClient(main.app)


def _add_note(client, tenant_id="acme-legal", client_key="Marcus Whitfield", note="note text", matter_type=None, source="intake_conflict_check"):
    return client.post(
        f"/memory/{tenant_id}/{client_key}/notes",
        json={"note": note, "matter_type": matter_type, "source": source},
    )


def test_health_returns_ok():
    client = TestClient(main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_add_note_returns_created_record(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = _add_note(client, note="Prior matter, no conflict.", matter_type="llc_formation")

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "acme-legal"
    assert body["client_key"] == "Marcus Whitfield"
    assert body["note"] == "Prior matter, no conflict."
    assert body["matter_type"] == "llc_formation"
    assert body["source"] == "intake_conflict_check"
    assert "id" in body
    assert "created_at" in body


def test_get_client_memory_with_no_history_returns_200_with_empty_list(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.get("/memory/acme-legal/Someone Unseen")

    assert response.status_code == 200
    assert response.json() == {"client_key": "Someone Unseen", "notes": []}


def test_get_client_memory_returns_notes_for_known_client(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    _add_note(client, note="First note.")

    response = client.get("/memory/acme-legal/Marcus Whitfield")

    assert response.status_code == 200
    body = response.json()
    assert body["client_key"] == "Marcus Whitfield"
    assert len(body["notes"]) == 1
    assert body["notes"][0]["note"] == "First note."


def test_multiple_notes_accumulate_in_chronological_order(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    _add_note(client, note="First note.")
    _add_note(client, note="Second note.")
    _add_note(client, note="Third note.")

    response = client.get("/memory/acme-legal/Marcus Whitfield")

    notes = response.json()["notes"]
    assert [n["note"] for n in notes] == ["First note.", "Second note.", "Third note."]


def test_same_client_key_isolated_across_tenants(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    _add_note(client, tenant_id="acme-legal", client_key="Jordan Reyes", note="acme-legal's note")
    _add_note(client, tenant_id="other-firm", client_key="Jordan Reyes", note="other-firm's note")

    acme_memory = client.get("/memory/acme-legal/Jordan Reyes").json()
    other_memory = client.get("/memory/other-firm/Jordan Reyes").json()

    assert [n["note"] for n in acme_memory["notes"]] == ["acme-legal's note"]
    assert [n["note"] for n in other_memory["notes"]] == ["other-firm's note"]


def test_add_note_missing_field_returns_422(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.post("/memory/acme-legal/Marcus Whitfield/notes", json={"matter_type": "llc_formation"})

    assert response.status_code == 422
