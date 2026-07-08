"""Client for the Memory service — thin HTTP wrapper so agents don't need to
know this is a service call instead of a local function.

Mirrors the other services' client style: one function per endpoint, same
BASE_URL-from-env pattern.
"""

import os

import requests

BASE_URL = os.environ.get("MEMORY_SERVICE_URL", "http://localhost:8006")


def add_note(
    tenant_id: str,
    client_key: str,
    note: str,
    matter_type: str | None = None,
    source: str | None = None,
) -> dict:
    response = requests.post(
        f"{BASE_URL}/memory/{tenant_id}/{client_key}/notes",
        json={"note": note, "matter_type": matter_type, "source": source or ""},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def get_client_memory(tenant_id: str, client_key: str) -> dict:
    response = requests.get(f"{BASE_URL}/memory/{tenant_id}/{client_key}", timeout=5)
    response.raise_for_status()
    return response.json()
