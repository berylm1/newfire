import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient

from visa_bulletin_service import main

SAMPLE_BULLETIN = {
    "bulletin_month": "August 2026",
    "family_sponsored": {
        "F2A": {
            "All Chargeability Areas Except Those Listed": "2026-07-22",
            "CHINA-mainland born": "2026-07-22",
            "INDIA": "2026-07-22",
            "MEXICO": "2025-07-22",
            "PHILIPPINES": "2026-07-22",
        },
        "F4": {
            "All Chargeability Areas Except Those Listed": "2009-09-01",
            "CHINA-mainland born": "2009-09-01",
            "INDIA": "2006-11-01",
            "MEXICO": "2001-04-08",
            "PHILIPPINES": "2007-08-01",
        },
    },
    "employment_based": {
        "EB-2": {
            "All Chargeability Areas Except Those Listed": "C",
            "CHINA-mainland born": "2021-09-01",
            "INDIA": "U",
            "MEXICO": "C",
            "PHILIPPINES": "C",
        },
    },
}


def _test_client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "CACHE_PATH", str(tmp_path / "bulletin_cache.json"))
    return TestClient(main.app)


def _seed_cache(tmp_path, monkeypatch, data=None):
    monkeypatch.setattr(main, "CACHE_PATH", str(tmp_path / "bulletin_cache.json"))
    main._save_cache(data or SAMPLE_BULLETIN)


def test_health_returns_ok():
    client = TestClient(main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_bulletin_current_serves_from_cache_without_fetching(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026), ("July", 2026), ("June", 2026)])

    def fail_if_called(month_name, year):
        raise AssertionError("should not fetch when a matching cache entry exists")

    monkeypatch.setattr(main, "_fetch_and_parse", fail_if_called)
    client = TestClient(main.app)

    response = client.get("/bulletin/current")

    assert response.status_code == 200
    assert response.json()["bulletin_month"] == "August 2026"


def test_bulletin_current_fetches_when_cache_is_for_a_stale_month(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch, data={**SAMPLE_BULLETIN, "bulletin_month": "January 2026"})
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026), ("July", 2026), ("June", 2026)])
    fetched = {"August 2026": {**SAMPLE_BULLETIN, "bulletin_month": "August 2026"}}
    monkeypatch.setattr(main, "_fetch_and_parse", lambda month_name, year: fetched.get(f"{month_name} {year}"))
    client = TestClient(main.app)

    response = client.get("/bulletin/current")

    assert response.status_code == 200
    assert response.json()["bulletin_month"] == "August 2026"


def test_bulletin_current_tries_candidates_in_order_until_one_succeeds(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "CACHE_PATH", str(tmp_path / "bulletin_cache.json"))
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026), ("July", 2026), ("June", 2026)])
    attempts = []

    def fake_fetch(month_name, year):
        attempts.append((month_name, year))
        if (month_name, year) == ("July", 2026):
            return {**SAMPLE_BULLETIN, "bulletin_month": "July 2026"}
        return None  # August not published yet

    monkeypatch.setattr(main, "_fetch_and_parse", fake_fetch)
    client = TestClient(main.app)

    response = client.get("/bulletin/current")

    assert response.status_code == 200
    assert response.json()["bulletin_month"] == "July 2026"
    assert attempts == [("August", 2026), ("July", 2026)]


def test_bulletin_current_falls_back_to_stale_cache_when_all_fetches_fail(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch, data={**SAMPLE_BULLETIN, "bulletin_month": "January 2026"})
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026), ("July", 2026), ("June", 2026)])
    monkeypatch.setattr(main, "_fetch_and_parse", lambda month_name, year: None)
    client = TestClient(main.app)

    response = client.get("/bulletin/current")

    assert response.status_code == 200
    body = response.json()
    assert body["bulletin_month"] == "January 2026"
    assert body["stale"] is True


def test_bulletin_current_raises_503_when_nothing_cached_and_fetch_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "CACHE_PATH", str(tmp_path / "bulletin_cache.json"))
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026)])
    monkeypatch.setattr(main, "_fetch_and_parse", lambda month_name, year: None)
    client = TestClient(main.app)

    response = client.get("/bulletin/current")

    assert response.status_code == 503


def test_check_priority_date_before_cutoff_is_not_current(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026)])
    client = TestClient(main.app)

    response = client.post("/check", json={"category": "F4", "country": "Mexico", "priority_date": "2005-01-01"})

    assert response.status_code == 200
    body = response.json()
    assert body["current"] is False
    assert body["cutoff"] == "2001-04-08"


def test_check_priority_date_past_cutoff_is_current(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026)])
    client = TestClient(main.app)

    response = client.post("/check", json={"category": "F4", "country": "Mexico", "priority_date": "1999-01-01"})

    assert response.status_code == 200
    assert response.json()["current"] is True


def test_check_priority_date_c_marker_is_always_current(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026)])
    client = TestClient(main.app)

    response = client.post(
        "/check", json={"category": "EB-2", "country": "All Chargeability Areas Except Those Listed", "priority_date": "2026-01-01"}
    )

    assert response.status_code == 200
    assert response.json()["current"] is True
    assert response.json()["cutoff"] == "C"


def test_check_priority_date_u_marker_is_never_current(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026)])
    client = TestClient(main.app)

    response = client.post("/check", json={"category": "EB-2", "country": "India", "priority_date": "1990-01-01"})

    assert response.status_code == 200
    assert response.json()["current"] is False
    assert response.json()["cutoff"] == "U"


def test_check_priority_date_unrecognized_country_defaults_to_all_chargeability(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026)])
    client = TestClient(main.app)

    response = client.post("/check", json={"category": "F4", "country": "Nigeria", "priority_date": "1999-01-01"})

    assert response.status_code == 200
    assert response.json()["country"] == "All Chargeability Areas Except Those Listed"


def test_check_priority_date_missing_country_defaults_to_all_chargeability(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026)])
    client = TestClient(main.app)

    response = client.post("/check", json={"category": "F4", "priority_date": "1999-01-01"})

    assert response.status_code == 200
    assert response.json()["country"] == "All Chargeability Areas Except Those Listed"


def test_check_priority_date_country_name_is_case_insensitive(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026)])
    client = TestClient(main.app)

    response = client.post("/check", json={"category": "F4", "country": "mexico", "priority_date": "1999-01-01"})

    assert response.status_code == 200
    assert response.json()["cutoff"] == "2001-04-08"


def test_check_priority_date_unknown_category_returns_422(tmp_path, monkeypatch):
    _seed_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "_candidate_months", lambda today: [("August", 2026)])
    client = TestClient(main.app)

    response = client.post("/check", json={"category": "EB-9", "priority_date": "1999-01-01"})

    assert response.status_code == 422
