"""Client for the Approval service — thin HTTP wrapper so agents and the
resume script don't need to know this is a service call instead of a local
function.

Mirrors the other services' client style: one function per endpoint, same
BASE_URL-from-env pattern.
"""

import os

import requests

BASE_URL = os.environ.get("APPROVAL_SERVICE_URL", "http://localhost:8004")


def create_approval(tenant_id: str, thread_id: str, kind: str, draft: str, context: dict | None = None) -> dict:
    response = requests.post(
        f"{BASE_URL}/approvals",
        json={
            "tenant_id": tenant_id,
            "thread_id": thread_id,
            "kind": kind,
            "draft": draft,
            "context": context or {},
        },
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def get_pending_approvals(tenant_id: str | None = None) -> list[dict]:
    params = {"tenant_id": tenant_id} if tenant_id is not None else {}
    response = requests.get(f"{BASE_URL}/approvals/pending", params=params, timeout=5)
    response.raise_for_status()
    return response.json()


def get_approval(approval_id: str) -> dict:
    response = requests.get(f"{BASE_URL}/approvals/{approval_id}", timeout=5)
    response.raise_for_status()
    return response.json()


def decide_approval(approval_id: str, approved: bool, decided_by: str) -> dict:
    response = requests.post(
        f"{BASE_URL}/approvals/{approval_id}/decide",
        json={"approved": approved, "decided_by": decided_by},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def get_resumable_approvals() -> list[dict]:
    response = requests.get(f"{BASE_URL}/approvals/resumable", timeout=5)
    response.raise_for_status()
    return response.json()


def mark_approval_resumed(approval_id: str) -> dict:
    response = requests.post(f"{BASE_URL}/approvals/{approval_id}/mark_resumed", timeout=5)
    response.raise_for_status()
    return response.json()
