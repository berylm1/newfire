import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from webhook_service import client


def test_sign_payload_matches_known_hmac_sha256_vector():
    # Known vector: HMAC-SHA256("key", "The quick brown fox jumps over the lazy dog")
    # https://en.wikipedia.org/wiki/HMAC#Examples (verified against Python's hmac/hashlib directly)
    digest = client.sign_payload("key", b"The quick brown fox jumps over the lazy dog")

    assert digest == "f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8"


def test_sign_payload_is_deterministic_and_secret_sensitive():
    body = b'{"body": "hello"}'

    assert client.sign_payload("secret-a", body) == client.sign_payload("secret-a", body)
    assert client.sign_payload("secret-a", body) != client.sign_payload("secret-b", body)


@patch("webhook_service.client.requests.get")
def test_get_pending_events_without_filters_omits_params(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_get.return_value = mock_response

    result = client.get_pending_events()

    mock_get.assert_called_once_with(f"{client.BASE_URL}/events/pending", params={}, timeout=5)
    mock_response.raise_for_status.assert_called_once()
    assert result == []


@patch("webhook_service.client.requests.get")
def test_get_pending_events_with_filters_passes_params(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": "abc-123"}]
    mock_get.return_value = mock_response

    result = client.get_pending_events(tenant_id="acme-legal", source="email")

    mock_get.assert_called_once_with(
        f"{client.BASE_URL}/events/pending",
        params={"tenant_id": "acme-legal", "source": "email"},
        timeout=5,
    )
    assert result == [{"id": "abc-123"}]


@patch("webhook_service.client.requests.get")
def test_get_event_returns_record(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "abc-123", "processed": False}
    mock_get.return_value = mock_response

    record = client.get_event("abc-123")

    mock_get.assert_called_once_with(f"{client.BASE_URL}/events/abc-123", timeout=5)
    mock_response.raise_for_status.assert_called_once()
    assert record == mock_response.json.return_value


@patch("webhook_service.client.requests.post")
def test_mark_event_processed_posts_to_endpoint(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "abc-123", "processed": True}
    mock_post.return_value = mock_response

    record = client.mark_event_processed("abc-123")

    mock_post.assert_called_once_with(f"{client.BASE_URL}/events/abc-123/mark_processed", timeout=5)
    mock_response.raise_for_status.assert_called_once()
    assert record == mock_response.json.return_value
