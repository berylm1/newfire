import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from activity_log_service import client


@patch("activity_log_service.client.requests.post")
def test_log_event_posts_to_events_endpoint_with_payload(mock_post):
    mock_response = MagicMock()
    mock_post.return_value = mock_response

    client.log_event("email_sent", "low", "sent intake confirmation")

    mock_post.assert_called_once_with(
        f"{client.BASE_URL}/events",
        json={"event_type": "email_sent", "urgency": "low", "summary": "sent intake confirmation"},
        timeout=5,
    )
    mock_response.raise_for_status.assert_called_once()


@patch("activity_log_service.client.requests.get")
def test_get_todays_events_returns_parsed_json(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"type": "call", "urgency": "high", "summary": "urgent client call", "timestamp": "2026-07-01T00:00:00+00:00"}
    ]
    mock_get.return_value = mock_response

    events = client.get_todays_events()

    mock_get.assert_called_once_with(f"{client.BASE_URL}/events/today", timeout=5)
    mock_response.raise_for_status.assert_called_once()
    assert events == mock_response.json.return_value
