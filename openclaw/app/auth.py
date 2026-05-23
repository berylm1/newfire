"""
Cloudflare Access JWT verification.

Reads the Cf-Access-Jwt-Assertion header, validates against the team's JWKS,
extracts the email claim, and uses it as the canonical developer identity.

A dev bypass is available: if settings.openclaw_dev_email is set, JWT is
skipped entirely and that email is used. The service refuses to start in
"production posture" (no dev email AND no AUD) so the bypass cannot be left
on by accident.
"""
import time
import logging
import httpx
import jwt
from fastapi import Header, HTTPException, status
from .config import settings

log = logging.getLogger("openclaw.auth")

_JWKS_CACHE: dict = {"keys": [], "fetched_at": 0.0}


async def _get_jwks() -> list:
    now = time.time()
    if _JWKS_CACHE["keys"] and (now - _JWKS_CACHE["fetched_at"]) < settings.cf_jwks_ttl_seconds:
        return _JWKS_CACHE["keys"]
    url = f"https://{settings.cf_team_domain}/cdn-cgi/access/certs"
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
    _JWKS_CACHE["keys"] = data.get("keys", [])
    _JWKS_CACHE["fetched_at"] = now
    log.info("refreshed JWKS, %d keys cached", len(_JWKS_CACHE["keys"]))
    return _JWKS_CACHE["keys"]


async def authenticate(
    cf_access_jwt_assertion: str | None = Header(default=None, alias="Cf-Access-Jwt-Assertion"),
) -> str:
    """FastAPI dependency: returns the authenticated developer email."""
    # Dev bypass for local curl testing. Container fails startup if both
    # bypass and AUD are unset (see main.py startup check).
    if settings.openclaw_dev_email:
        return settings.openclaw_dev_email

    if not cf_access_jwt_assertion:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing Cf-Access-Jwt-Assertion header",
        )

    try:
        unverified = jwt.get_unverified_header(cf_access_jwt_assertion)
        kid = unverified.get("kid")
        if not kid:
            raise HTTPException(401, "JWT missing kid")

        keys = await _get_jwks()
        matched = next((k for k in keys if k.get("kid") == kid), None)
        if not matched:
            # try a refresh in case the key rotated
            _JWKS_CACHE["fetched_at"] = 0.0
            keys = await _get_jwks()
            matched = next((k for k in keys if k.get("kid") == kid), None)
        if not matched:
            raise HTTPException(401, f"no JWKS key matches kid={kid}")

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(matched)
        payload = jwt.decode(
            cf_access_jwt_assertion,
            key=public_key,
            algorithms=["RS256"],
            audience=settings.cf_access_aud if settings.cf_access_aud else None,
            options={"verify_aud": bool(settings.cf_access_aud)},
        )
        email = payload.get("email")
        if not email:
            raise HTTPException(401, "JWT has no email claim")
        return email
    except HTTPException:
        raise
    except jwt.PyJWTError as e:
        log.warning("JWT verification failed: %s", e)
        raise HTTPException(401, f"invalid JWT: {e}")
