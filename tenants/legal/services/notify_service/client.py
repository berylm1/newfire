"""Client for the Notify service — thin HTTP wrapper so agents don't need to
know this is a service call instead of a local function.
"""

import os

import requests

BASE_URL = os.environ.get("NOTIFY_SERVICE_URL", "http://localhost:8008")


def send_notification(tenant_id: str, channel: str, to: str, body: str, subject: str | None = None) -> dict:
    response = requests.post(
        f"{BASE_URL}/notify",
        json={"tenant_id": tenant_id, "channel": channel, "to": to, "subject": subject, "body": body},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def get_notify_log(tenant_id: str | None = None) -> list[dict]:
    params = {}
    if tenant_id is not None:
        params["tenant_id"] = tenant_id
    response = requests.get(f"{BASE_URL}/notify/log", params=params, timeout=5)
    response.raise_for_status()
    return response.json()
