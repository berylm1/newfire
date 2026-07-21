"""Client for the Case service — thin HTTP wrapper so agents don't need to
know this is a service call instead of a local function.

Mirrors the other services' client style: one function per endpoint, same
BASE_URL-from-env pattern. `case_id` is a server-generated uuid, so it's fine
in the URL path — unlike a free-text client_key (see memory_service), it
never contains characters that would break routing.
"""

import os

import requests

BASE_URL = os.environ.get("CASE_SERVICE_URL", "http://localhost:8007")


def create_case(
    tenant_id: str,
    client_name: str,
    contact: dict | None = None,
    case_type: str = "",
    key_dates: dict | None = None,
    fee_status: dict | None = None,
    documents: dict | None = None,
    financial_snapshot: dict | None = None,
    assigned_attorney: str = "",
    notes: str = "",
) -> dict:
    payload = {
        "tenant_id": tenant_id,
        "client_name": client_name,
        "case_type": case_type,
        "assigned_attorney": assigned_attorney,
        "notes": notes,
    }
    # Left out entirely (rather than sent as None) when not provided, so the
    # server's own defaults (empty dict / default fee_status) apply.
    if contact is not None:
        payload["contact"] = contact
    if key_dates is not None:
        payload["key_dates"] = key_dates
    if fee_status is not None:
        payload["fee_status"] = fee_status
    if documents is not None:
        payload["documents"] = documents
    if financial_snapshot is not None:
        payload["financial_snapshot"] = financial_snapshot

    response = requests.post(f"{BASE_URL}/cases", json=payload, timeout=5)
    response.raise_for_status()
    return response.json()


def list_cases(tenant_id: str, case_type: str | None = None) -> list[dict]:
    params = {}
    if case_type is not None:
        params["case_type"] = case_type
    response = requests.get(f"{BASE_URL}/cases/{tenant_id}", params=params, timeout=5)
    response.raise_for_status()
    return response.json()


def get_case(tenant_id: str, case_id: str) -> dict:
    response = requests.get(f"{BASE_URL}/cases/{tenant_id}/{case_id}", timeout=5)
    response.raise_for_status()
    return response.json()


def update_case(
    tenant_id: str,
    case_id: str,
    client_name: str | None = None,
    contact: dict | None = None,
    case_type: str | None = None,
    key_dates: dict | None = None,
    fee_status: dict | None = None,
    documents: dict | None = None,
    financial_snapshot: dict | None = None,
    assigned_attorney: str | None = None,
    notes: str | None = None,
) -> dict:
    fields = {
        "client_name": client_name,
        "contact": contact,
        "case_type": case_type,
        "key_dates": key_dates,
        "fee_status": fee_status,
        "documents": documents,
        "financial_snapshot": financial_snapshot,
        "assigned_attorney": assigned_attorney,
        "notes": notes,
    }
    payload = {k: v for k, v in fields.items() if v is not None}
    response = requests.patch(f"{BASE_URL}/cases/{tenant_id}/{case_id}", json=payload, timeout=5)
    response.raise_for_status()
    return response.json()
