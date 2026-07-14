import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from notify_service import client


@patch("notify_service.client.requests.post")
def test_send_notification_posts_payload_and_returns_record(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "abc-123", "status": "sent"}
    mock_post.return_value = mock_response

    record = client.send_notification(
        tenant_id="acme-legal", channel="email", to="attorney@example.com", body="text", subject="Morning briefing"
    )

    mock_post.assert_called_once_with(
        f"{client.BASE_URL}/notify",
        json={
            "tenant_id": "acme-legal",
            "channel": "email",
            "to": "attorney@example.com",
            "subject": "Morning briefing",
            "body": "text",
        },
        timeout=5,
    )
    mock_response.raise_for_status.assert_called_once()
    assert record == mock_response.json.return_value


@patch("notify_service.client.requests.post")
def test_send_notification_defaults_subject_to_none(mock_post):
    mock_response = MagicMock()
    mock_post.return_value = mock_response

    client.send_notification(tenant_id="acme-legal", channel="whatsapp", to="+15551234567", body="text")

    assert mock_post.call_args.kwargs["json"]["subject"] is None


@patch("notify_service.client.requests.get")
def test_get_notify_log_without_filter(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_get.return_value = mock_response

    result = client.get_notify_log()

    mock_get.assert_called_once_with(f"{client.BASE_URL}/notify/log", params={}, timeout=5)
    assert result == []


@patch("notify_service.client.requests.get")
def test_get_notify_log_with_tenant_filter(mock_get):
    mock_response = MagicMock()
    mock_get.return_value = mock_response

    client.get_notify_log(tenant_id="acme-legal")

    mock_get.assert_called_once_with(
        f"{client.BASE_URL}/notify/log", params={"tenant_id": "acme-legal"}, timeout=5
    )
