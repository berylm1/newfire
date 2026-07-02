import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from approval_service import client


@patch("approval_service.client.requests.post")
def test_create_approval_posts_payload_and_returns_record(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "abc-123", "status": "pending"}
    mock_post.return_value = mock_response

    record = client.create_approval(
        tenant_id="acme-legal",
        thread_id="thread-1",
        kind="intake_memo",
        draft="draft text",
        context={"conflicts": []},
    )

    mock_post.assert_called_once_with(
        f"{client.BASE_URL}/approvals",
        json={
            "tenant_id": "acme-legal",
            "thread_id": "thread-1",
            "kind": "intake_memo",
            "draft": "draft text",
            "context": {"conflicts": []},
        },
        timeout=5,
    )
    mock_response.raise_for_status.assert_called_once()
    assert record == mock_response.json.return_value


@patch("approval_service.client.requests.post")
def test_create_approval_defaults_context_to_empty_dict(mock_post):
    mock_response = MagicMock()
    mock_post.return_value = mock_response

    client.create_approval(tenant_id="acme-legal", thread_id="thread-1", kind="citation_report", draft="draft")

    assert mock_post.call_args.kwargs["json"]["context"] == {}


@patch("approval_service.client.requests.get")
def test_get_pending_approvals_without_tenant_id_omits_param(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_get.return_value = mock_response

    result = client.get_pending_approvals()

    mock_get.assert_called_once_with(f"{client.BASE_URL}/approvals/pending", params={}, timeout=5)
    mock_response.raise_for_status.assert_called_once()
    assert result == []


@patch("approval_service.client.requests.get")
def test_get_pending_approvals_with_tenant_id_passes_param(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": "abc-123"}]
    mock_get.return_value = mock_response

    result = client.get_pending_approvals(tenant_id="acme-legal")

    mock_get.assert_called_once_with(
        f"{client.BASE_URL}/approvals/pending", params={"tenant_id": "acme-legal"}, timeout=5
    )
    assert result == [{"id": "abc-123"}]


@patch("approval_service.client.requests.get")
def test_get_approval_returns_record(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "abc-123", "status": "pending"}
    mock_get.return_value = mock_response

    record = client.get_approval("abc-123")

    mock_get.assert_called_once_with(f"{client.BASE_URL}/approvals/abc-123", timeout=5)
    mock_response.raise_for_status.assert_called_once()
    assert record == mock_response.json.return_value


@patch("approval_service.client.requests.post")
def test_decide_approval_posts_decision(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "abc-123", "status": "approved"}
    mock_post.return_value = mock_response

    record = client.decide_approval("abc-123", approved=True, decided_by="reviewer")

    mock_post.assert_called_once_with(
        f"{client.BASE_URL}/approvals/abc-123/decide",
        json={"approved": True, "decided_by": "reviewer"},
        timeout=5,
    )
    mock_response.raise_for_status.assert_called_once()
    assert record == mock_response.json.return_value


@patch("approval_service.client.requests.get")
def test_get_resumable_approvals_returns_parsed_json(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": "abc-123", "status": "approved", "resumed": False}]
    mock_get.return_value = mock_response

    result = client.get_resumable_approvals()

    mock_get.assert_called_once_with(f"{client.BASE_URL}/approvals/resumable", timeout=5)
    mock_response.raise_for_status.assert_called_once()
    assert result == mock_response.json.return_value


@patch("approval_service.client.requests.post")
def test_mark_approval_resumed_posts_to_endpoint(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "abc-123", "resumed": True}
    mock_post.return_value = mock_response

    record = client.mark_approval_resumed("abc-123")

    mock_post.assert_called_once_with(f"{client.BASE_URL}/approvals/abc-123/mark_resumed", timeout=5)
    mock_response.raise_for_status.assert_called_once()
    assert record == mock_response.json.return_value
