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
        f"/memory/{tenant_id}/notes",
        json={"client_key": client_key, "note": note, "matter_type": matter_type, "source": source},
    )


def _get_memory(client, tenant_id, client_key):
    return client.get(f"/memory/{tenant_id}", params={"client_key": client_key})


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

    response = _get_memory(client, "acme-legal", "Someone Unseen")

    assert response.status_code == 200
    assert response.json() == {"client_key": "Someone Unseen", "notes": []}


def test_get_client_memory_returns_notes_for_known_client(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    _add_note(client, note="First note.")

    response = _get_memory(client, "acme-legal", "Marcus Whitfield")

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

    response = _get_memory(client, "acme-legal", "Marcus Whitfield")

    notes = response.json()["notes"]
    assert [n["note"] for n in notes] == ["First note.", "Second note.", "Third note."]


def test_same_client_key_isolated_across_tenants(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    _add_note(client, tenant_id="acme-legal", client_key="Jordan Reyes", note="acme-legal's note")
    _add_note(client, tenant_id="other-firm", client_key="Jordan Reyes", note="other-firm's note")

    acme_memory = _get_memory(client, "acme-legal", "Jordan Reyes").json()
    other_memory = _get_memory(client, "other-firm", "Jordan Reyes").json()

    assert [n["note"] for n in acme_memory["notes"]] == ["acme-legal's note"]
    assert [n["note"] for n in other_memory["notes"]] == ["other-firm's note"]


def test_add_note_missing_field_returns_422(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.post("/memory/acme-legal/notes", json={"client_key": "Marcus Whitfield", "matter_type": "llc_formation"})

    assert response.status_code == 422


def test_client_key_with_slash_works(tmp_path, monkeypatch):
    # Regression test: client_key used to be a URL path segment, which broke
    # outright for any name containing "/" -- a common construct in legal
    # entity names ("Jane Doe d/b/a Acme Consulting"). Moving client_key to
    # the request body / query param sidesteps the ambiguity entirely.
    client = _test_client(tmp_path, monkeypatch)

    response = _add_note(client, client_key="Jane Doe d/b/a Acme Consulting", note="First matter.")
    assert response.status_code == 200
    assert response.json()["client_key"] == "Jane Doe d/b/a Acme Consulting"

    fetched = _get_memory(client, "acme-legal", "Jane Doe d/b/a Acme Consulting")
    assert fetched.status_code == 200
    assert len(fetched.json()["notes"]) == 1
