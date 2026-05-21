"""
SIE client used for startup dimension fingerprint check only.
Superlinked handles production embeddings internally via the same SIE.
Never fall back to nomic (768-dim vs bge-m3 1024-dim corrupts the index).
"""

import os

import httpx
import redis as redis_mod

EMBED_URL = os.environ.get("EMBED_URL", "http://sie:8089/embed")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")
EMBED_DIM = int(os.environ.get("EMBED_DIM", "1024"))
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-rag")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

_FINGERPRINT_KEY = "rag:embed:fingerprint"


def _redis() -> redis_mod.Redis:
    return redis_mod.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def _parse_vectors(data: dict) -> list[list[float]]:
    if "data" in data:
        return [item["embedding"] for item in data["data"]]
    if "embeddings" in data:
        return data["embeddings"]
    raise ValueError(f"Unrecognised SIE response shape: {list(data.keys())}")


def embed(texts: list[str]) -> list[list[float]]:
    resp = httpx.post(
        EMBED_URL,
        json={"model": EMBED_MODEL, "input": texts},
        timeout=30.0,
    )
    resp.raise_for_status()
    return _parse_vectors(resp.json())


def startup_check() -> None:
    """
    Pitfall 1 mitigation, fail-closed at boot:
    1. Verify SIE is reachable and returns vectors of the expected dimension.
    2. Persist a model:dim fingerprint to Redis; abort if it conflicts with a
       previously stored fingerprint (means someone repointed EMBED_URL to a
       different model without dropping the index first).
    """
    try:
        vecs = embed(["startup-health-probe"])
    except Exception as exc:
        raise RuntimeError(
            f"SIE unreachable at {EMBED_URL}: {exc}. "
            "Service cannot start without the embedding backend."
        ) from exc

    actual_dim = len(vecs[0])
    if actual_dim != EMBED_DIM:
        raise RuntimeError(
            f"SIE returned dim={actual_dim}, expected {EMBED_DIM} "
            f"(EMBED_MODEL={EMBED_MODEL}). Wrong model loaded? "
            "NEVER fall back to nomic-embed: 768-dim vectors corrupt the 1024-dim index."
        )

    fingerprint = f"{EMBED_MODEL}:{EMBED_DIM}"
    r = _redis()
    stored = r.get(_FINGERPRINT_KEY)
    if stored is None:
        r.set(_FINGERPRINT_KEY, fingerprint)
    elif stored != fingerprint:
        raise RuntimeError(
            f"Embed fingerprint mismatch: Redis has '{stored}', "
            f"current config is '{fingerprint}'. "
            "Run FT.DROPINDEX on all legal_* indices before switching models, "
            "then delete the Redis key rag:embed:fingerprint."
        )
