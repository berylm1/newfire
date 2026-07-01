"""
Mock webhooks module for testing webhook security tests.

This module provides mock implementations that mirror the expected
interface of the actual webhooks module in newfire-backend.

The actual implementation should be in the backend repository.
"""

import hashlib
import hmac
import json
import time
from typing import Any

# Simulated in-memory store for idempotency testing
_processed_events: set = set()
_webhook_secret = "test-webhook-secret-key-12345"


def get_webhook_secret() -> str:
    """Get the configured webhook secret."""
    return _webhook_secret


def verify_signature(payload: str, signature: str, secret: str, timestamp: int | None = None) -> bool:
    """
    Verify HMAC-SHA256 signature of webhook payload.
    
    Uses constant-time comparison to prevent timing attacks.
    """
    if timestamp is not None:
        signed_payload = f"{timestamp}.{payload}"
    else:
        signed_payload = payload
    
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    expected_sig = f"sha256={expected}"
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, expected_sig)


def verify_webhook_signature(payload: str, headers: dict) -> bool:
    """
    Verify the signature of an incoming webhook request.
    
    Args:
        payload: Raw request body
        headers: Request headers
        
    Returns:
        True if signature is valid, False otherwise
    """
    signature = headers.get("X-Webhook-Signature", "")
    
    if not signature:
        return False
    
    # Verify signature format
    if not signature.startswith("sha256="):
        return False
    
    secret = get_webhook_secret()
    timestamp = headers.get("X-Webhook-Timestamp")
    
    try:
        timestamp_int = int(timestamp) if timestamp else None
    except (ValueError, TypeError):
        timestamp_int = None
    
    return verify_signature(payload, signature, secret, timestamp_int)


def is_event_processed(event_id: str) -> bool:
    """Check if an event has already been processed (idempotency check)."""
    return event_id in _processed_events


def mark_event_processed(event_id: str) -> None:
    """Mark an event as processed (idempotency tracking)."""
    _processed_events.add(event_id)


# Valid event types for this webhook
VALID_EVENT_TYPES = {"test.event", "message.received", "user.created", "user.updated"}


def validate_payload_structure(payload: dict) -> tuple[bool, str | None]:
    """
    Validate the structure of a webhook payload.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["event", "event_id", "company_id", "timestamp"]
    
    for field in required_fields:
        if field not in payload:
            return False, f"Missing required field: {field}"
    
    # Check event type is known
    event_type = payload.get("event")
    if event_type not in VALID_EVENT_TYPES:
        return False, f"Unknown event type"
    
    # Check payload size (max 1MB)
    try:
        payload_str = json.dumps(payload)
        if len(payload_str) > 1024 * 1024:
            return False, "Payload too large"
    except Exception:
        return False, "Invalid JSON"
    
    # Check timestamp is reasonable (within 24 hours)
    try:
        ts = payload.get("timestamp", 0)
        now = int(time.time())
        if abs(now - ts) > 86400:
            return False, "Timestamp out of range"
    except (ValueError, TypeError):
        return False, "Invalid timestamp"
    
    return True, None


def sanitize_for_logging(data: dict) -> dict:
    """
    Sanitize webhook data for logging by removing sensitive fields.
    This should be used before any logging operations.
    """
    sensitive_fields = {
        "api_key", "apikey", "api-key", "secret", "password", "passwd",
        "token", "authorization", "auth", "credential", "private_key",
        "access_token", "refresh_token", "session_token", "session_key",
        "jwt_secret", "webhook_secret", "db_password", "db_password",
        "connection_string", "connection", "secret_key", "private_key",
        # Environment variable style names
        "webhook_secret", "jwt_secret", "secret_key", "api_secret",
        "access_key", "access_secret"
    }
    
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower().replace("-", "_")
        if key_lower in sensitive_fields:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_for_logging(value)
        else:
            sanitized[key] = value
    
    return sanitized


def process_event(payload: dict) -> dict:
    """
    Process a validated webhook event.
    Override this in tests to simulate processing.
    """
    return {"event_id": payload.get("event_id")}


def db_query(query: str, params: tuple = ()) -> Any:
    """
    Mock database query function.
    Override in tests.
    """
    return None


def process_webhook(payload_str: str, headers: dict) -> dict:
    """
    Main webhook processing function.
    
    Args:
        payload_str: Raw request body
        headers: Request headers
        
    Returns:
        Response dict with status and optional error
    """
    try:
        # Parse payload
        if not payload_str or not payload_str.strip():
            return {"status": 400, "error": "Empty payload"}
        
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            return {"status": 400, "error": "Invalid JSON"}
        
        # Verify signature
        if not verify_webhook_signature(payload_str, headers):
            return {"status": 401, "error": "Invalid signature"}
        
        # Validate payload structure
        is_valid, error = validate_payload_structure(payload)
        if not is_valid:
            return {"status": 400, "error": error}
        
        # Check idempotency
        event_id = payload.get("event_id")
        if is_event_processed(event_id):
            return {"status": 409, "error": "Duplicate event", "event_id": event_id}
        
        # Process the event
        result = process_event(payload)
        
        # Mark as processed
        mark_event_processed(event_id)
        
        return {"status": 200, "event_id": event_id, **result}
        
    except Exception as e:
        # Generic error response - don't leak internal details
        return {"status": 500, "error": "Internal server error"}


def clear_processed_events() -> None:
    """Reset the processed events store. Used for testing."""
    global _processed_events
    _processed_events = set()
