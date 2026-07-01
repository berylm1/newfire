import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient

from conflicts_service import main

client = TestClient(main.app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_check_conflicts_returns_match_for_known_party():
    response = client.post("/check", json={"party_names": ["Marcus Whitfield"]})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["queried_name"] == "Marcus Whitfield"
    assert body[0]["role"] == "former_client"
    assert body[0]["matter"] == "Whitfield Properties LLC formation"


def test_check_conflicts_matches_on_partial_name():
    response = client.post("/check", json={"party_names": ["whitfield"]})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Marcus Whitfield"


def test_check_conflicts_returns_empty_list_when_no_match():
    response = client.post("/check", json={"party_names": ["Someone Unrelated"]})

    assert response.status_code == 200
    assert response.json() == []


def test_check_conflicts_skips_blank_names():
    response = client.post("/check", json={"party_names": [""]})

    assert response.status_code == 200
    assert response.json() == []


def test_check_conflicts_missing_field_returns_422():
    response = client.post("/check", json={})

    assert response.status_code == 422
