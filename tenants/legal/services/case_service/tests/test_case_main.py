import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient

from case_service import main


def _test_client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STORE_PATH", str(tmp_path / "cases.json"))
    return TestClient(main.app)


def _create_case(client, tenant_id="acme-legal", client_name="Jane Doe", **fields):
    return client.post("/cases", json={"tenant_id": tenant_id, "client_name": client_name, **fields})


def test_health_returns_ok():
    client = TestClient(main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_case_applies_defaults(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = _create_case(client)

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "acme-legal"
    assert body["client_name"] == "Jane Doe"
    assert body["contact"] == {}
    assert body["case_type"] == ""
    assert body["key_dates"] == {}
    assert body["fee_status"] == {"total_fee": None, "amount_paid": None, "status": "unpaid", "notes": ""}
    assert body["documents"] == {}
    assert body["financial_snapshot"] == {}
    assert body["visa_bulletin_tracking"] == {}
    assert body["assigned_attorney"] == ""
    assert body["notes"] == ""
    assert "id" in body
    assert body["created_at"] == body["updated_at"]


def test_create_case_accepts_full_record(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = _create_case(
        client,
        client_name="Priya Raman",
        contact={"email": "priya@example.com"},
        case_type="marriage_based_green_card",
        key_dates={"filing_deadline": "2026-08-01"},
        fee_status={"total_fee": 3500, "amount_paid": 1000, "status": "partial", "notes": "deposit received"},
        assigned_attorney="J. Alvarez",
        notes="Initial consult done.",
    )

    body = response.json()
    assert body["contact"] == {"email": "priya@example.com"}
    assert body["case_type"] == "marriage_based_green_card"
    assert body["key_dates"] == {"filing_deadline": "2026-08-01"}
    assert body["fee_status"]["status"] == "partial"
    assert body["assigned_attorney"] == "J. Alvarez"


def test_create_case_missing_required_field_returns_422(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.post("/cases", json={"tenant_id": "acme-legal"})

    assert response.status_code == 422


def test_list_cases_scopes_to_tenant(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    _create_case(client, tenant_id="acme-legal", client_name="A")
    _create_case(client, tenant_id="other-firm", client_name="B")

    response = client.get("/cases/acme-legal")

    assert response.status_code == 200
    names = [c["client_name"] for c in response.json()]
    assert names == ["A"]


def test_list_cases_with_no_cases_returns_empty_list(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.get("/cases/acme-legal")

    assert response.status_code == 200
    assert response.json() == []


def test_list_cases_filters_by_case_type(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    _create_case(client, client_name="A", case_type="asylum")
    _create_case(client, client_name="B", case_type="change_of_status")

    response = client.get("/cases/acme-legal", params={"case_type": "asylum"})

    assert response.status_code == 200
    names = [c["client_name"] for c in response.json()]
    assert names == ["A"]


def test_get_case_returns_record(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create_case(client, client_name="A").json()

    response = client.get(f"/cases/acme-legal/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_case_missing_returns_404(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.get("/cases/acme-legal/does-not-exist")

    assert response.status_code == 404


def test_get_case_wrong_tenant_returns_404(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create_case(client, tenant_id="acme-legal", client_name="A").json()

    response = client.get(f"/cases/other-firm/{created['id']}")

    assert response.status_code == 404


def test_patch_merges_key_dates_without_erasing_others(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create_case(
        client, client_name="A", key_dates={"visa_expiration": "2026-08-01", "priority_date": "2023-05-01"}
    ).json()

    response = client.patch(f"/cases/acme-legal/{created['id']}", json={"key_dates": {"filing_deadline": "2026-07-20"}})

    assert response.status_code == 200
    key_dates = response.json()["key_dates"]
    assert key_dates == {
        "visa_expiration": "2026-08-01",
        "priority_date": "2023-05-01",
        "filing_deadline": "2026-07-20",
    }


def test_patch_merges_fee_status_without_erasing_others(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create_case(
        client, client_name="A", fee_status={"total_fee": 3500, "amount_paid": 0, "status": "unpaid", "notes": ""}
    ).json()

    response = client.patch(f"/cases/acme-legal/{created['id']}", json={"fee_status": {"amount_paid": 1500, "status": "partial"}})

    assert response.status_code == 200
    fee_status = response.json()["fee_status"]
    assert fee_status == {"total_fee": 3500, "amount_paid": 1500, "status": "partial", "notes": ""}


def test_patch_merges_documents_without_erasing_others(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create_case(client, client_name="A", documents={"passport_copy": True, "i94_record": False}).json()

    response = client.patch(f"/cases/acme-legal/{created['id']}", json={"documents": {"i94_record": True}})

    assert response.status_code == 200
    assert response.json()["documents"] == {"passport_copy": True, "i94_record": True}


def test_patch_merges_financial_snapshot_without_erasing_others(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create_case(client, client_name="A", financial_snapshot={"funds_available": 10000}).json()

    response = client.patch(f"/cases/acme-legal/{created['id']}", json={"financial_snapshot": {"program_cost": 12000}})

    assert response.status_code == 200
    assert response.json()["financial_snapshot"] == {"funds_available": 10000, "program_cost": 12000}


def test_patch_merges_visa_bulletin_tracking_without_erasing_others(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create_case(
        client, client_name="A", visa_bulletin_tracking={"category": "F2A", "country": "Mexico"}
    ).json()

    response = client.patch(
        f"/cases/acme-legal/{created['id']}", json={"visa_bulletin_tracking": {"priority_date": "2023-05-01"}}
    )

    assert response.status_code == 200
    assert response.json()["visa_bulletin_tracking"] == {
        "category": "F2A",
        "country": "Mexico",
        "priority_date": "2023-05-01",
    }


def test_patch_updates_scalar_field_and_bumps_updated_at(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create_case(client, client_name="A").json()

    response = client.patch(f"/cases/acme-legal/{created['id']}", json={"assigned_attorney": "New Attorney"})

    assert response.status_code == 200
    body = response.json()
    assert body["assigned_attorney"] == "New Attorney"
    assert body["updated_at"] >= body["created_at"]


def test_patch_missing_case_returns_404(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)

    response = client.patch("/cases/acme-legal/does-not-exist", json={"notes": "x"})

    assert response.status_code == 404


def test_patch_wrong_tenant_returns_404(tmp_path, monkeypatch):
    client = _test_client(tmp_path, monkeypatch)
    created = _create_case(client, tenant_id="acme-legal", client_name="A").json()

    response = client.patch(f"/cases/other-firm/{created['id']}", json={"notes": "x"})

    assert response.status_code == 404
