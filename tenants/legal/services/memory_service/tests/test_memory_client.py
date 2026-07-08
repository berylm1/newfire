import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from memory_service import client


@patch("memory_service.client.requests.post")
def test_add_note_posts_payload_and_returns_record(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "abc-123", "note": "Prior matter, no conflict."}
    mock_post.return_value = mock_response

    record = client.add_note(
        tenant_id="acme-legal",
        client_key="Marcus Whitfield",
        note="Prior matter, no conflict.",
        matter_type="llc_formation",
        source="intake_conflict_check",
    )

    mock_post.assert_called_once_with(
        f"{client.BASE_URL}/memory/acme-legal/Marcus Whitfield/notes",
        json={
            "note": "Prior matter, no conflict.",
            "matter_type": "llc_formation",
            "source": "intake_conflict_check",
        },
        timeout=5,
    )
    mock_response.raise_for_status.assert_called_once()
    assert record == mock_response.json.return_value


@patch("memory_service.client.requests.post")
def test_add_note_defaults_matter_type_and_source(mock_post):
    mock_response = MagicMock()
    mock_post.return_value = mock_response

    client.add_note(tenant_id="acme-legal", client_key="Marcus Whitfield", note="note text")

    assert mock_post.call_args.kwargs["json"]["matter_type"] is None
    assert mock_post.call_args.kwargs["json"]["source"] == ""


@patch("memory_service.client.requests.get")
def test_get_client_memory_returns_parsed_json(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"client_key": "Marcus Whitfield", "notes": [{"id": "abc-123"}]}
    mock_get.return_value = mock_response

    result = client.get_client_memory("acme-legal", "Marcus Whitfield")

    mock_get.assert_called_once_with(f"{client.BASE_URL}/memory/acme-legal/Marcus Whitfield", timeout=5)
    mock_response.raise_for_status.assert_called_once()
    assert result == mock_response.json.return_value
