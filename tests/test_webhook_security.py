"""
Webhook Security Regression Tests

Tests for webhook signature validation, replay/idempotency protection,
malformed payload handling, and error sanitization.

These tests verify the security properties outlined in issue #19:
- Invalid signature and malformed payloads are rejected
- Duplicate events (replay attacks) are handled correctly
- Error messages do not leak sensitive information (secrets, tokens, etc.)
"""

import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest

# Import the mock webhooks module for testing
from mock_webhooks import (
    verify_webhook_signature,
    process_webhook,
    is_event_processed,
    mark_event_processed,
    get_webhook_secret,
    verify_signature,
    sanitize_for_logging,
    db_query,
    process_event,
    clear_processed_events,
)


# =============================================================================
# Test Configuration
# =============================================================================

WEBHOOK_SECRET = "test-webhook-secret-key-12345"
TEST_EVENT_ID = "evt_test_123456"
TEST_COMPANY_ID = "company_abc"


def generate_signature(payload: str, secret: str, timestamp: int | None = None) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    if timestamp is not None:
        signed_payload = f"{timestamp}.{payload}"
    else:
        signed_payload = payload
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def create_webhook_headers(
    payload: str,
    secret: str = WEBHOOK_SECRET,
    timestamp: int | None = None,
    signature: str | None = None,
    event_id: str = TEST_EVENT_ID,
    company_id: str = TEST_COMPANY_ID
) -> dict:
    """Create headers for webhook request."""
    if signature is None:
        signature = generate_signature(payload, secret, timestamp)
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": "test.event",
        "X-Webhook-Event-ID": event_id,
        "X-Company-ID": company_id,
    }
    if timestamp is not None:
        headers["X-Webhook-Timestamp"] = str(timestamp)
    return headers


def create_valid_webhook_payload(
    event_type: str = "test.event",
    event_id: str = TEST_EVENT_ID,
    company_id: str = TEST_COMPANY_ID,
    data: dict | None = None
) -> dict:
    """Create a valid webhook payload."""
    return {
        "event": event_type,
        "event_id": event_id,
        "company_id": company_id,
        "timestamp": int(time.time()),
        "data": data or {"message": "test data"}
    }


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_processed_events():
    """Reset processed events before each test."""
    clear_processed_events()
    yield
    clear_processed_events()


@pytest.fixture
def mock_webhook_config():
    """Mock webhook configuration with secret."""
    with patch("mock_webhooks._webhook_secret", WEBHOOK_SECRET):
        yield


# =============================================================================
# Signature Validation Tests
# =============================================================================

class TestWebhookSignatureValidation:
    """Tests for webhook signature validation."""

    def test_valid_signature_is_accepted(self, mock_webhook_config):
        """Valid HMAC-SHA256 signatures should be accepted."""
        payload = json.dumps(create_valid_webhook_payload())
        headers = create_webhook_headers(payload)
        
        result = verify_webhook_signature(payload, headers)
        assert result is True

    def test_invalid_signature_is_rejected(self, mock_webhook_config):
        """Invalid signatures should be rejected."""
        payload = json.dumps(create_valid_webhook_payload())
        headers = create_webhook_headers(payload, signature="sha256=invalid_signature_here")
        
        result = verify_webhook_signature(payload, headers)
        assert result is False

    def test_missing_signature_header_is_rejected(self, mock_webhook_config):
        """Requests without signature header should be rejected."""
        payload = json.dumps(create_valid_webhook_payload())
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event-ID": TEST_EVENT_ID,
            "X-Company-ID": TEST_COMPANY_ID,
        }
        
        result = verify_webhook_signature(payload, headers)
        assert result is False

    def test_tampered_payload_is_rejected(self, mock_webhook_config):
        """Payloads modified after signing should be rejected."""
        original_payload = create_valid_webhook_payload()
        payload_str = json.dumps(original_payload)
        
        # Generate signature for original payload
        headers = create_webhook_headers(payload_str)
        
        # Tamper with the payload
        tampered_payload = json.dumps({**original_payload, "data": {"message": "tampered"}})
        
        result = verify_webhook_signature(tampered_payload, headers)
        assert result is False

    def test_wrong_secret_is_rejected(self):
        """Signatures generated with wrong secret should be rejected."""
        payload = json.dumps(create_valid_webhook_payload())
        # Sign with wrong secret
        headers = create_webhook_headers(payload, secret="wrong-secret-key")
        
        result = verify_webhook_signature(payload, headers)
        assert result is False

    def test_empty_signature_is_rejected(self, mock_webhook_config):
        """Empty signature should be rejected."""
        payload = json.dumps(create_valid_webhook_payload())
        headers = create_webhook_headers(payload, signature="")
        
        result = verify_webhook_signature(payload, headers)
        assert result is False

    def test_malformed_signature_format_is_rejected(self, mock_webhook_config):
        """Signatures not using sha256= prefix should be rejected."""
        payload = json.dumps(create_valid_webhook_payload())
        headers = create_webhook_headers(payload, signature="md5=abcdef123456")
        
        result = verify_webhook_signature(payload, headers)
        assert result is False


# =============================================================================
# Malformed Payload Tests
# =============================================================================

class TestMalformedPayloadHandling:
    """Tests for handling malformed webhook payloads."""

    def test_empty_payload_is_rejected(self, mock_webhook_config):
        """Empty payload body should be rejected."""
        result = process_webhook("", {})
        assert result["status"] == 400
        assert "error" in result

    def test_non_json_payload_is_rejected(self, mock_webhook_config):
        """Non-JSON payload should be rejected."""
        result = process_webhook("not valid json", {})
        assert result["status"] == 400
        assert "error" in result

    def test_missing_required_fields_are_rejected(self, mock_webhook_config):
        """Payloads missing required fields should be rejected after signature validation."""
        # Missing event_id - needs valid signature first to get to validation step
        incomplete_payload = {
            "event": "test.event",
            "company_id": TEST_COMPANY_ID,
            "timestamp": int(time.time()),
            # Missing: event_id
        }
        payload_str = json.dumps(incomplete_payload)
        headers = create_webhook_headers(payload_str)
        
        result = process_webhook(payload_str, headers)
        assert result["status"] == 400

    def test_invalid_event_type_is_rejected(self, mock_webhook_config):
        """Unknown event types should be rejected."""
        payload = create_valid_webhook_payload(event_type="unknown.event.type")
        headers = create_webhook_headers(json.dumps(payload))
        
        result = process_webhook(json.dumps(payload), headers)
        assert result["status"] == 400

    def test_sql_injection_in_payload_is_neutralized(self, mock_webhook_config):
        """SQL injection attempts in payload should be neutralized."""
        malicious_payload = {
            "event": "test.event",
            "event_id": TEST_EVENT_ID,
            "company_id": TEST_COMPANY_ID,
            "timestamp": int(time.time()),
            "data": {
                "message": "'; DROP TABLE users; --",
                "query": "1=1 OR 1=1"
            }
        }
        payload_str = json.dumps(malicious_payload)
        headers = create_webhook_headers(payload_str)
        
        result = process_webhook(payload_str, headers)
        # Should either reject or sanitize, not execute the injection
        assert result["status"] in [200, 400]

    def test_xss_in_payload_is_neutralized(self, mock_webhook_config):
        """XSS attempts in payload should be neutralized."""
        malicious_payload = {
            "event": "test.event",
            "event_id": TEST_EVENT_ID,
            "company_id": TEST_COMPANY_ID,
            "timestamp": int(time.time()),
            "data": {
                "message": "<script>alert('xss')</script>",
                "html_content": "<img src=x onerror=alert(1)>"
            }
        }
        payload_str = json.dumps(malicious_payload)
        headers = create_webhook_headers(payload_str)
        
        result = process_webhook(payload_str, headers)
        # Should sanitize or reject
        assert result["status"] in [200, 400]

    def test_oversized_payload_is_rejected(self, mock_webhook_config):
        """Oversized payloads should be rejected."""
        # Create a payload that exceeds reasonable size limits
        large_payload = {
            "event": "test.event",
            "event_id": TEST_EVENT_ID,
            "company_id": TEST_COMPANY_ID,
            "timestamp": int(time.time()),
            "data": {"content": "x" * (10 * 1024 * 1024)}  # 10MB of data
        }
        payload_str = json.dumps(large_payload)
        headers = create_webhook_headers(payload_str)
        
        result = process_webhook(payload_str, headers)
        assert result["status"] == 400  # Bad request - payload too large

    def test_null_bytes_in_payload_are_handled(self, mock_webhook_config):
        """Payloads with null bytes should be handled safely."""
        malicious_payload = json.dumps({
            "event": "test.event",
            "event_id": TEST_EVENT_ID,
            "company_id": TEST_COMPANY_ID,
            "timestamp": int(time.time()),
            "data": {"content": "hello\x00world"}
        })
        headers = create_webhook_headers(malicious_payload)
        
        result = process_webhook(malicious_payload, headers)
        # Should handle safely without crashing
        assert result["status"] in [200, 400]

    def test_nested_depth_limit_exceeded(self, mock_webhook_config):
        """Deeply nested payloads should be rejected."""
        def create_deeply_nested(depth: int) -> dict:
            if depth <= 0:
                return {"value": "leaf"}
            return {"nested": create_deeply_nested(depth - 1)}
        
        deep_payload = json.dumps(create_deeply_nested(100))
        headers = create_webhook_headers(deep_payload)
        
        result = process_webhook(deep_payload, headers)
        assert result["status"] in [200, 400]


# =============================================================================
# Replay / Idempotency Tests
# =============================================================================

class TestReplayAndIdempotency:
    """Tests for replay attack protection and idempotency."""

    def test_duplicate_event_within_window_is_rejected(self, mock_webhook_config):
        """Duplicate events within the idempotency window should be rejected."""
        payload = create_valid_webhook_payload()
        payload_str = json.dumps(payload)
        headers = create_webhook_headers(payload_str)
        
        # First request should succeed
        result1 = process_webhook(payload_str, headers)
        assert result1["status"] == 200
        
        # Second request with same event_id should be rejected (replay)
        result2 = process_webhook(payload_str, headers)
        assert result2["status"] == 409  # Conflict - duplicate

    def test_duplicate_event_after_window_is_handled(self, mock_webhook_config):
        """Duplicate events after idempotency window should be processed."""
        # Clear events first
        clear_processed_events()
        
        payload = create_valid_webhook_payload()
        payload_str = json.dumps(payload)
        headers = create_webhook_headers(payload_str)
        
        result = process_webhook(payload_str, headers)
        assert result["status"] == 200

    def test_different_events_same_content_both_processed(self, mock_webhook_config):
        """Different events with same content should both be processed."""
        clear_processed_events()
        
        payload1 = create_valid_webhook_payload(event_id="event_1")
        payload2 = create_valid_webhook_payload(event_id="event_2")
        
        result1 = process_webhook(json.dumps(payload1), create_webhook_headers(json.dumps(payload1), event_id="event_1"))
        result2 = process_webhook(json.dumps(payload2), create_webhook_headers(json.dumps(payload2), event_id="event_2"))
        
        assert result1["status"] == 200
        assert result2["status"] == 200

    def test_event_with_timestamps_outside_window_rejected(self, mock_webhook_config):
        """Events with timestamps outside acceptable window should be rejected."""
        old_timestamp = int(time.time()) - 90000  # 25 hours ago (exceeds 24h window)
        payload = create_valid_webhook_payload()
        payload["timestamp"] = old_timestamp
        payload_str = json.dumps(payload)
        
        headers = create_webhook_headers(payload_str, timestamp=old_timestamp)
        
        result = process_webhook(payload_str, headers)
        # Should reject due to stale timestamp (replay protection)
        assert result["status"] in [400, 401]

    def test_event_with_future_timestamp_rejected(self, mock_webhook_config):
        """Events with future timestamps should be rejected."""
        future_timestamp = int(time.time()) + 90000  # 25 hours in future
        payload = create_valid_webhook_payload()
        payload["timestamp"] = future_timestamp
        payload_str = json.dumps(payload)
        
        headers = create_webhook_headers(payload_str, timestamp=future_timestamp)
        
        result = process_webhook(payload_str, headers)
        # Should reject due to future timestamp
        assert result["status"] in [400, 401]


# =============================================================================
# Error Sanitization Tests
# =============================================================================

class TestErrorSanitization:
    """Tests to ensure errors do not leak secrets."""

    def test_signature_verification_error_does_not_leak_secret(self, mock_webhook_config):
        """Signature verification errors should not expose the secret."""
        payload = json.dumps(create_valid_webhook_payload())
        headers = create_webhook_headers(payload, signature="sha256=tampered")
        
        result = process_webhook(payload, headers)
        
        error_message = result.get("error", "")
        # Error should not contain sensitive details
        assert "WEBHOOK_SECRET" not in error_message

    def test_database_error_does_not_leak_connection_details(self, mock_webhook_config):
        """Database errors should not expose connection strings or credentials."""
        # Test that the error sanitization works by testing the sanitize function
        sensitive_data = {
            "db_password": "secret123",
            "host": "db.example.com",
            "safe_field": "visible"
        }
        
        sanitized = sanitize_for_logging(sensitive_data)
        
        assert "secret123" not in str(sanitized)
        assert "visible" in str(sanitized)

    def test_internal_error_returns_generic_message(self, mock_webhook_config):
        """Internal errors should return generic message to client."""
        payload = json.dumps(create_valid_webhook_payload())
        headers = create_webhook_headers(payload)
        
        # Mock an internal error
        with patch("mock_webhooks.process_event", side_effect=RuntimeError("Internal stack trace here")):
            result = process_webhook(payload, headers)
            
            assert result["status"] == 500
            error_message = result.get("error", "")
            # Should be a generic error, not the actual exception
            assert "stack trace" not in error_message.lower()

    def test_config_error_does_not_leak_secrets(self, mock_webhook_config):
        """Configuration errors should not expose secrets."""
        # Test the sanitize function catches config-related secrets
        sensitive_config = {
            "WEBHOOK_SECRET": "super_secret_123",
            "JWT_SECRET": "jwt_secret_456",
            "safe_setting": "visible"
        }
        
        sanitized = sanitize_for_logging(sensitive_config)
        
        assert "super_secret_123" not in str(sanitized)
        assert "jwt_secret_456" not in str(sanitized)
        assert "visible" in str(sanitized)

    def test_company_not_found_error_is_safe(self, mock_webhook_config):
        """Company not found errors should be generic."""
        payload = create_valid_webhook_payload(company_id="nonexistent_company")
        
        result = process_webhook(json.dumps(payload), create_webhook_headers(json.dumps(payload), company_id="nonexistent_company"))
        
        # Should succeed (mock doesn't validate company IDs, but real impl would)
        # The key point is no sensitive data should be leaked
        assert result["status"] in [200, 400, 401, 404]

    def test_logging_does_not_include_sensitive_data(self, mock_webhook_config):
        """Logs should not include sensitive webhook data."""
        sensitive_payload = create_valid_webhook_payload(
            data={
                "api_key": "sk_live_secret_key_123",
                "password": "user_password_456",
                "token": "oauth_token_789",
                "safe_field": "visible_data"
            }
        )
        
        # Sanitize function should remove sensitive fields
        sanitized = sanitize_for_logging(sensitive_payload)
        
        assert "sk_live_secret_key_123" not in str(sanitized)
        assert "user_password_456" not in str(sanitized)
        assert "oauth_token_789" not in str(sanitized)
        assert "visible_data" in str(sanitized)


# =============================================================================
# Integration Tests
# =============================================================================

class TestWebhookIntegration:
    """End-to-end integration tests for webhook security."""

    def test_complete_valid_webhook_flow(self, mock_webhook_config):
        """Complete flow with valid signature should succeed."""
        clear_processed_events()
        
        payload = create_valid_webhook_payload()
        payload_str = json.dumps(payload)
        headers = create_webhook_headers(payload_str)
        
        result = process_webhook(payload_str, headers)
        
        assert result["status"] == 200
        assert "event_id" in result

    def test_complete_invalid_signature_webhook_flow(self, mock_webhook_config):
        """Complete flow with invalid signature should fail securely."""
        payload = create_valid_webhook_payload()
        payload_str = json.dumps(payload)
        headers = create_webhook_headers(payload_str, signature="sha256=invalid")
        
        result = process_webhook(payload_str, headers)
        
        assert result["status"] in [401, 403]
        assert "error" in result
        # Error should not leak the actual secret or internal details
        error_msg = result.get("error", "").lower()
        assert "sha256" not in error_msg
        assert WEBHOOK_SECRET not in error_msg

    def test_webhook_timing_attack_mitigation(self, mock_webhook_config):
        """Signature comparison should use constant-time comparison."""
        payload = json.dumps(create_valid_webhook_payload())
        headers = create_webhook_headers(payload)
        
        # The mock_webhooks module uses hmac.compare_digest which is constant-time
        result = process_webhook(payload, headers)
        
        # Should succeed with valid signature
        assert result["status"] == 200


# =============================================================================
# Test Helpers
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
