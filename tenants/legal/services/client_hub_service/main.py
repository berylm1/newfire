"""Client Hub service — the centralized client-facing surface this tenant
didn't have. This is requirement #3 from Mr. Patrick's live product-direction
meeting: "a centralized location that shows them their clients, who has paid
their fees and who hasn't, and they should be able to send emails out to
clients from here."

`case_service` already stores the roster and fee data, `notify_service`
already delivers messages — this is the composition layer that turns those
two primitives into a hub view and a send-email action, the same way
`daily_briefing` composes `case_service` and `notify_service` for the
attorney-facing briefing. This one is a plain HTTP service rather than a
LangGraph agent because there's no drafting or judgment involved — listing a
roster and sending a caller-supplied email is direct composition, not
something that benefits from an LLM in the loop.

Every send is logged to `activity_log_service` so an outbound client email
shows up in the tenant's shared feed alongside everything else that
happened that day.
"""

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from activity_log_service.client import log_event
from case_service.client import get_case, list_cases
from notify_service.client import send_notification

app = FastAPI(title="Client Hub Service")

# This is the one service in the tenant meant to be called directly from a
# browser rather than only from another backend process — nothing built so
# far has a front end. Wide open because this service isn't deployed or
# reachable from outside localhost yet (see README); narrow this to a real
# origin once a front end actually ships.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ClientEmailIn(BaseModel):
    subject: str
    body: str


def _outstanding_balance(fee_status: dict) -> float | None:
    total_fee = fee_status.get("total_fee")
    amount_paid = fee_status.get("amount_paid")
    if total_fee is None or amount_paid is None:
        return None
    return total_fee - amount_paid


@app.get("/hub/{tenant_id}")
def get_hub(tenant_id: str, case_type: str | None = None) -> list[dict]:
    cases = list_cases(tenant_id, case_type=case_type)
    for case in cases:
        case["outstanding_balance"] = _outstanding_balance(case.get("fee_status") or {})
    return cases


@app.post("/hub/{tenant_id}/{case_id}/email")
def send_client_email(tenant_id: str, case_id: str, email: ClientEmailIn) -> dict:
    try:
        case = get_case(tenant_id, case_id)
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="case not found") from exc
        raise

    address = (case.get("contact") or {}).get("email")
    if not address:
        raise HTTPException(status_code=422, detail="client has no email on file")

    result = send_notification(
        tenant_id=tenant_id,
        channel="email",
        to=address,
        subject=email.subject,
        body=email.body,
    )
    log_event(
        event_type="client_email_sent",
        urgency="low",
        summary=f"Emailed {case['client_name']}: {email.subject}",
    )
    return result


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
