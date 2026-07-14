import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from client_hub_service import client


@patch("client_hub_service.client.requests.get")
def test_get_hub_without_filter(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": "case-1"}]
    mock_get.return_value = mock_response

    result = client.get_hub("acme-legal")

    mock_get.assert_called_once_with(f"{client.BASE_URL}/hub/acme-legal", params={}, timeout=5)
    mock_response.raise_for_status.assert_called_once()
    assert result == [{"id": "case-1"}]


@patch("client_hub_service.client.requests.get")
def test_get_hub_with_case_type_filter(mock_get):
    mock_response = MagicMock()
    mock_get.return_value = mock_response

    client.get_hub("acme-legal", case_type="asylum")

    mock_get.assert_called_once_with(
        f"{client.BASE_URL}/hub/acme-legal", params={"case_type": "asylum"}, timeout=5
    )


@patch("client_hub_service.client.requests.post")
def test_send_client_email_posts_payload_and_returns_record(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "notify-1", "status": "sent"}
    mock_post.return_value = mock_response

    result = client.send_client_email(
        "acme-legal", "case-1", subject="Document request", body="Please send your passport copy."
    )

    mock_post.assert_called_once_with(
        f"{client.BASE_URL}/hub/acme-legal/case-1/email",
        json={"subject": "Document request", "body": "Please send your passport copy."},
        timeout=5,
    )
    mock_response.raise_for_status.assert_called_once()
    assert result == mock_response.json.return_value
