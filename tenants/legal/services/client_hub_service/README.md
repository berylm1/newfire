# Client Hub Service

The centralized client-facing surface this tenant didn't have. This is
requirement #3 from Mr. Patrick's live product-direction meeting: "a
centralized location that shows them their clients, who has paid their fees
and who hasn't, and they should be able to send emails out to clients from
here."

`case_service` already owns the roster and fee data, `notify_service`
already owns delivery — this service is the composition layer that turns
those two primitives into a hub view and a send-email action, the same way
`daily_briefing` composes `case_service` and `notify_service` for the
attorney-facing briefing. This one is a plain HTTP service rather than a
LangGraph agent because there's no drafting or judgment involved: listing a
roster and sending a caller-supplied email is direct composition, not
something an LLM needs to be in the loop for.

## Endpoints

`GET /hub/{tenant_id}` — a tenant's cases from `case_service`, each with an
added `outstanding_balance` field (`total_fee - amount_paid`, or `null` if
either isn't set yet). This is the "who's paid and who hasn't" view. Optional
`?case_type=` filter, passed straight through to `case_service`.

`POST /hub/{tenant_id}/{case_id}/email` — body `{"subject": str, "body":
str}`. Looks up the case, reads `contact.email`, and sends it via
`notify_service` (`channel="email"`). Every send is also logged to
`activity_log_service` (`client_email_sent`) so it shows up in the tenant's
shared feed. 404 if the case doesn't exist or belongs to a different tenant;
422 if the case has no email address on file.

`GET /health` — liveness check.

## What this deliberately doesn't do yet

No template library for common client emails (fee reminders, document
requests) — this round is "send whatever text the caller provides," not
drafting. No WhatsApp send from the hub — `notify_service` already supports
that channel, but the meeting's ask was specifically about email from the
hub; wiring `channel="whatsapp"` in here is a small follow-up, not a
redesign.

## Running locally

```
pip install -r requirements.txt
uvicorn client_hub_service.main:app --port 8009
```

Requires `activity_log_service`, `case_service`, and `notify_service`
running too (see the tenant's `services/README.md`). Agents or a future UI
pick this up via `CLIENT_HUB_SERVICE_URL` (defaults to
`http://localhost:8009`). Import `client.py` for `get_hub` and
`send_client_email`.

In production this would run as `legal-client-hub.service` on port 8109,
same pattern as the other services — not deployed this round.
