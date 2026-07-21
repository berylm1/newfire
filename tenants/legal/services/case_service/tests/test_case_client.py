import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from case_service import client


@patch("case_service.client.requests.post")
def test_create_case_omits_unset_optional_fields(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "abc-123"}
    mock_post.return_value = mock_response

    record = client.create_case(tenant_id="acme-legal", client_name="Jane Doe")

    mock_post.assert_called_once_with(
        f"{client.BASE_URL}/cases",
        json={
            "tenant_id": "acme-legal",
            "client_name": "Jane Doe",
            "case_type": "",
            "assigned_attorney": "",
            "notes": "",
        },
        timeout=5,
    )
    mock_response.raise_for_status.assert_called_once()
    assert record == mock_response.json.return_value


@patch("case_service.client.requests.post")
def test_create_case_includes_provided_optional_fields(mock_post):
    mock_response = MagicMock()
    mock_post.return_value = mock_response

    client.create_case(
        tenant_id="acme-legal",
        client_name="Jane Doe",
        contact={"email": "jane@example.com"},
        key_dates={"filing_deadline": "2026-08-01"},
        fee_status={"status": "paid"},
        documents={"passport_copy": True},
        financial_snapshot={"funds_available": 10000},
    )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["contact"] == {"email": "jane@example.com"}
    assert payload["key_dates"] == {"filing_deadline": "2026-08-01"}
    assert payload["fee_status"] == {"status": "paid"}
    assert payload["documents"] == {"passport_copy": True}
    assert payload["financial_snapshot"] == {"funds_available": 10000}


@patch("case_service.client.requests.get")
def test_list_cases_without_filter(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_get.return_value = mock_response

    result = client.list_cases("acme-legal")

    mock_get.assert_called_once_with(f"{client.BASE_URL}/cases/acme-legal", params={}, timeout=5)
    assert result == []


@patch("case_service.client.requests.get")
def test_list_cases_with_case_type_filter(mock_get):
    mock_response = MagicMock()
    mock_get.return_value = mock_response

    client.list_cases("acme-legal", case_type="asylum")

    mock_get.assert_called_once_with(
        f"{client.BASE_URL}/cases/acme-legal", params={"case_type": "asylum"}, timeout=5
    )


@patch("case_service.client.requests.get")
def test_get_case_returns_parsed_json(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "abc-123"}
    mock_get.return_value = mock_response

    result = client.get_case("acme-legal", "abc-123")

    mock_get.assert_called_once_with(f"{client.BASE_URL}/cases/acme-legal/abc-123", timeout=5)
    assert result == mock_response.json.return_value


@patch("case_service.client.requests.patch")
def test_update_case_only_sends_provided_fields(mock_patch):
    mock_response = MagicMock()
    mock_patch.return_value = mock_response

    client.update_case("acme-legal", "abc-123", assigned_attorney="New Attorney")

    mock_patch.assert_called_once_with(
        f"{client.BASE_URL}/cases/acme-legal/abc-123",
        json={"assigned_attorney": "New Attorney"},
        timeout=5,
    )
