import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import requests
from fastapi.testclient import TestClient

from client_hub_service import main


def _test_client(raise_server_exceptions: bool = True) -> TestClient:
    return TestClient(main.app, raise_server_exceptions=raise_server_exceptions)


def _make_http_error(status_code: int) -> requests.exceptions.HTTPError:
    response = requests.Response()
    response.status_code = status_code
    return requests.exceptions.HTTPError(response=response)


def test_health_returns_ok():
    client = _test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_browser_origin(monkeypatch):
    # The only service in the tenant meant to be hit directly from a
    # browser demo page — confirm the middleware is actually wired, not
    # just imported.
    monkeypatch.setattr(main, "list_cases", lambda tenant_id, case_type=None: [])
    client = _test_client()

    response = client.get("/hub/acme-legal", headers={"Origin": "http://localhost:8500"})

    assert response.headers["access-control-allow-origin"] == "*"


def test_get_hub_computes_outstanding_balance(monkeypatch):
    cases = [
        {
            "id": "case-1",
            "client_name": "Priya Raman",
            "fee_status": {"total_fee": 3500, "amount_paid": 1000, "status": "partial", "notes": ""},
        }
    ]
    monkeypatch.setattr(main, "list_cases", lambda tenant_id, case_type=None: cases)
    client = _test_client()

    response = client.get("/hub/acme-legal")

    assert response.status_code == 200
    assert response.json()[0]["outstanding_balance"] == 2500


def test_get_hub_outstanding_balance_is_none_when_fee_unset(monkeypatch):
    cases = [
        {
            "id": "case-1",
            "client_name": "A",
            "fee_status": {"total_fee": None, "amount_paid": None, "status": "unpaid", "notes": ""},
        }
    ]
    monkeypatch.setattr(main, "list_cases", lambda tenant_id, case_type=None: cases)
    client = _test_client()

    response = client.get("/hub/acme-legal")

    assert response.json()[0]["outstanding_balance"] is None


def test_get_hub_passes_tenant_and_case_type_through(monkeypatch):
    seen = {}

    def fake_list_cases(tenant_id, case_type=None):
        seen["tenant_id"] = tenant_id
        seen["case_type"] = case_type
        return []

    monkeypatch.setattr(main, "list_cases", fake_list_cases)
    client = _test_client()

    client.get("/hub/acme-legal", params={"case_type": "asylum"})

    assert seen == {"tenant_id": "acme-legal", "case_type": "asylum"}


def test_get_hub_empty_list_when_no_cases(monkeypatch):
    monkeypatch.setattr(main, "list_cases", lambda tenant_id, case_type=None: [])
    client = _test_client()

    response = client.get("/hub/acme-legal")

    assert response.status_code == 200
    assert response.json() == []


def test_send_client_email_sends_via_notify_and_logs(monkeypatch):
    case = {"id": "case-1", "client_name": "Priya Raman", "contact": {"email": "priya@example.com"}}
    sent = {}
    logged = {}
    monkeypatch.setattr(main, "get_case", lambda tenant_id, case_id: case)
    monkeypatch.setattr(main, "send_notification", lambda **kwargs: sent.update(kwargs) or {"id": "notify-1", "status": "sent"})
    monkeypatch.setattr(main, "log_event", lambda **kwargs: logged.update(kwargs))
    client = _test_client()

    response = client.post(
        "/hub/acme-legal/case-1/email",
        json={"subject": "Document request", "body": "Please send your passport copy."},
    )

    assert response.status_code == 200
    assert response.json() == {"id": "notify-1", "status": "sent"}
    assert sent == {
        "tenant_id": "acme-legal",
        "channel": "email",
        "to": "priya@example.com",
        "subject": "Document request",
        "body": "Please send your passport copy.",
    }
    assert logged["event_type"] == "client_email_sent"
    assert "Priya Raman" in logged["summary"]
    assert "Document request" in logged["summary"]


def test_send_client_email_missing_case_returns_404(monkeypatch):
    def raise_404(tenant_id, case_id):
        raise _make_http_error(404)

    monkeypatch.setattr(main, "get_case", raise_404)
    client = _test_client()

    response = client.post("/hub/acme-legal/does-not-exist/email", json={"subject": "x", "body": "y"})

    assert response.status_code == 404


def test_send_client_email_no_email_on_file_returns_422(monkeypatch):
    case = {"id": "case-1", "client_name": "A", "contact": {}}
    monkeypatch.setattr(main, "get_case", lambda tenant_id, case_id: case)
    client = _test_client()

    response = client.post("/hub/acme-legal/case-1/email", json={"subject": "x", "body": "y"})

    assert response.status_code == 422


def test_send_client_email_missing_contact_dict_returns_422(monkeypatch):
    case = {"id": "case-1", "client_name": "A"}
    monkeypatch.setattr(main, "get_case", lambda tenant_id, case_id: case)
    client = _test_client()

    response = client.post("/hub/acme-legal/case-1/email", json={"subject": "x", "body": "y"})

    assert response.status_code == 422


def test_send_client_email_missing_required_field_returns_422(monkeypatch):
    client = _test_client()

    response = client.post("/hub/acme-legal/case-1/email", json={"subject": "x"})

    assert response.status_code == 422


def test_send_client_email_unexpected_upstream_error_propagates(monkeypatch):
    def raise_500(tenant_id, case_id):
        raise _make_http_error(500)

    monkeypatch.setattr(main, "get_case", raise_500)
    client = _test_client(raise_server_exceptions=False)

    response = client.post("/hub/acme-legal/case-1/email", json={"subject": "x", "body": "y"})

    assert response.status_code == 500
