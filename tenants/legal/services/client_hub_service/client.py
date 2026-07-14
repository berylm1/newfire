"""Client for the Client Hub service — thin HTTP wrapper so agents (or a
future UI) don't need to know this is a service call instead of a local
function.
"""

import os

import requests

BASE_URL = os.environ.get("CLIENT_HUB_SERVICE_URL", "http://localhost:8009")


def get_hub(tenant_id: str, case_type: str | None = None) -> list[dict]:
    params = {}
    if case_type is not None:
        params["case_type"] = case_type
    response = requests.get(f"{BASE_URL}/hub/{tenant_id}", params=params, timeout=5)
    response.raise_for_status()
    return response.json()


def send_client_email(tenant_id: str, case_id: str, subject: str, body: str) -> dict:
    response = requests.post(
        f"{BASE_URL}/hub/{tenant_id}/{case_id}/email",
        json={"subject": subject, "body": body},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()
