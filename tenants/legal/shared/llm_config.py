"""Centralized LLM configuration for legal tenant services.

All graph-based services should import from this module instead of defining
their own DEFAULT_BASE_URL / DEFAULT_MODEL constants. The environment
variables listed below override the defaults.

Enforced env vars (no silent fallback to hardcoded IPs):
  LLM_BASE_URL   — OpenAI-compatible API base URL (default: LiteLLM on localhost)
  LLM_API_KEY    — API key for the LLM provider (required)
  LLM_MODEL      — Model name (default: gemma4-26b-64k)
  OLLAMA_EMBEDDING_BASE_URL — Embedding service URL (default: localhost)
  OLLAMA_VISION_BASE_URL    — Vision service URL (default: localhost)
"""

import os

# Primary LLM endpoint (OpenAI-compatible interface — LiteLLM or Ollama)
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:4000/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma4-26b-64k")

# Embedding service endpoint
EMBEDDING_BASE_URL = os.environ.get(
    "OLLAMA_EMBEDDING_BASE_URL",
    "http://localhost:11434",
)
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")

# Vision service endpoint
VISION_BASE_URL = os.environ.get(
    "OLLAMA_VISION_BASE_URL",
    "http://localhost:11434",
)
VISION_MODEL = os.environ.get("OLLAMA_VISION_MODEL", "llava")


def require_api_key() -> str:
    """Return the configured LLM API key or raise if missing."""
    if not LLM_API_KEY:
        raise RuntimeError(
            "LLM_API_KEY environment variable is required but not set. "
            "See .env.example for guidance."
        )
    return LLM_API_KEY
