"""
Pytest configuration and shared fixtures for webhook security tests.
"""

import pytest


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks between tests to ensure isolation."""
    # This runs automatically before each test
    yield
    # Cleanup after test if needed


@pytest.fixture
def test_secret():
    """Test webhook secret for unit tests."""
    return "test-webhook-secret-key-12345"


@pytest.fixture
def test_company_id():
    """Test company ID."""
    return "company_test_123"


@pytest.fixture
def test_event_id():
    """Test event ID."""
    return "evt_test_abc123"
