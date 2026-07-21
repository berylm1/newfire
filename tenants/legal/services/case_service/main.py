"""Case service — owns the client/case record for the legal tenant.

This is the foundation that didn't exist before: `daily_briefing` had no real
client data to work from (`docket_feed.py` returned hardcoded sample items),
and `memory_service` is an append-only note log, not a structured record with
fields like fee status or key dates. Crisis/deadline detection, a client hub,
priority-date tracking — none of the direction that came out of the pilot
firm's product meeting is buildable without a real case record to hang it on.
This service is that record: one JSON object per client matter, scoped to
`tenant_id` so this works for any small-to-mid immigration practice, not one
firm's data model.

`case_type` is deliberately a free-text label, not an enum or a rules engine —
case-type-specific playbooks (what to flag for a marriage-based green card
vs. an asylum case) are a later phase. `key_dates` is deliberately a flexible
dict, not fixed columns — different case types care about different dates
(visa expiration, filing deadline, priority date, ...) and a rigid schema
would need a migration every time a new case type showed up with a date type
nobody anticipated.

Swappable like the rest of this tenant: point STORE_PATH at a real database
and nothing calling this service needs to change.
"""

import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

STORE_PATH = os.path.join(os.path.dirname(__file__), "cases.json")

# Case record fields that hold a dict of sub-fields rather than a single
# scalar value. A PATCH touching one of these merges into the existing dict
# instead of replacing it outright — see update_case.
DICT_FIELDS = ("contact", "key_dates", "fee_status", "documents", "financial_snapshot", "visa_bulletin_tracking")

DEFAULT_FEE_STATUS = {"total_fee": None, "amount_paid": None, "status": "unpaid", "notes": ""}

app = FastAPI(title="Case Service")


class CaseIn(BaseModel):
    tenant_id: str
    client_name: str
    contact: dict = Field(default_factory=dict)
    case_type: str = ""
    key_dates: dict = Field(default_factory=dict)
    fee_status: dict = Field(default_factory=lambda: dict(DEFAULT_FEE_STATUS))
    # Which of case_type's required documents are on file yet, e.g.
    # {"passport_copy": True, "i94_record": False}. Same free-form-dict
    # philosophy as key_dates: case_jeopardy_check's playbooks.py owns what's
    # "required" per case_type, this just tracks what's actually in hand.
    documents: dict = Field(default_factory=dict)
    # Case-type-specific financial facts (e.g. {"funds_available": 15000,
    # "program_cost": 12000} for a change-of-status financial-sufficiency
    # check). Not every case type needs this, so it's fine empty.
    financial_snapshot: dict = Field(default_factory=dict)
    # {"category": "F2A", "country": "Mexico", "priority_date": "2023-05-01"}
    # for a case that has a priority date at all (family-sponsored or
    # employment-based green card matters) -- visa_bulletin_check checks
    # this against the current Visa Bulletin. Empty for case types with no
    # priority date (asylum, naturalization, non-immigrant H-1B, ...).
    visa_bulletin_tracking: dict = Field(default_factory=dict)
    assigned_attorney: str = ""
    notes: str = ""


class CaseUpdate(BaseModel):
    client_name: str | None = None
    contact: dict | None = None
    case_type: str | None = None
    key_dates: dict | None = None
    fee_status: dict | None = None
    documents: dict | None = None
    financial_snapshot: dict | None = None
    visa_bulletin_tracking: dict | None = None
    assigned_attorney: str | None = None
    notes: str | None = None


def _load() -> dict[str, dict]:
    if not os.path.exists(STORE_PATH):
        return {}
    with open(STORE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save(cases: dict[str, dict]) -> None:
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)


@app.post("/cases")
def create_case(case: CaseIn) -> dict:
    cases = _load()
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": str(uuid.uuid4()),
        "tenant_id": case.tenant_id,
        "client_name": case.client_name,
        "contact": case.contact,
        "case_type": case.case_type,
        "key_dates": case.key_dates,
        "fee_status": case.fee_status,
        "documents": case.documents,
        "financial_snapshot": case.financial_snapshot,
        "visa_bulletin_tracking": case.visa_bulletin_tracking,
        "assigned_attorney": case.assigned_attorney,
        "notes": case.notes,
        "created_at": now,
        "updated_at": now,
    }
    cases[record["id"]] = record
    _save(cases)
    return record


@app.get("/cases/{tenant_id}")
def list_cases(tenant_id: str, case_type: str | None = None) -> list[dict]:
    cases = _load()
    results = [c for c in cases.values() if c["tenant_id"] == tenant_id]
    if case_type is not None:
        results = [c for c in results if c["case_type"] == case_type]
    return results


@app.get("/cases/{tenant_id}/{case_id}")
def get_case(tenant_id: str, case_id: str) -> dict:
    cases = _load()
    record = cases.get(case_id)
    if record is None or record["tenant_id"] != tenant_id:
        raise HTTPException(status_code=404, detail="case not found")
    return record


@app.patch("/cases/{tenant_id}/{case_id}")
def update_case(tenant_id: str, case_id: str, update: CaseUpdate) -> dict:
    cases = _load()
    record = cases.get(case_id)
    if record is None or record["tenant_id"] != tenant_id:
        raise HTTPException(status_code=404, detail="case not found")

    updates = update.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field in DICT_FIELDS and isinstance(record.get(field), dict) and isinstance(value, dict):
            # Merge, don't replace — a PATCH updating one key date or one
            # fee-status field shouldn't erase the rest of that dict.
            record[field].update(value)
        else:
            record[field] = value
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    cases[case_id] = record
    _save(cases)
    return record


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
