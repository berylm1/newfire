import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from conflicts_service import client


@patch("conflicts_service.client.requests.post")
def test_check_conflicts_posts_party_names_and_returns_matches(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "queried_name": "Marcus Whitfield",
            "name": "Marcus Whitfield",
            "role": "former_client",
            "matter": "Whitfield Properties LLC formation",
        }
    ]
    mock_post.return_value = mock_response

    matches = client.check_conflicts(["Marcus Whitfield"])

    mock_post.assert_called_once_with(
        f"{client.BASE_URL}/check",
        json={"party_names": ["Marcus Whitfield"]},
        timeout=5,
    )
    mock_response.raise_for_status.assert_called_once()
    assert matches == mock_response.json.return_value
