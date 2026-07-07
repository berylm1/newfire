# Webhook Service

The generic inbound door for this tenant. Every agent here used to run only
when a human invoked it directly (or, for WhatsApp, through a separate
gateway-level integration). This service is what lets an external event — a
new client email, a website contact-form submission, a CRM webhook — reach an
agent at all: any tool a firm actually uses can be pointed at this service's
endpoint, and a poller (`shared/process_webhook_events.py`) feeds queued
events into the right agent.

This service doesn't know or care which vendor sent an event or what agent
eventually consumes it. `source` is a free-text label the sender chooses
(`"email"`, `"contact_form"`, `"crm"`, ...) — nothing here parses vendor-
specific payload shapes. Examples of things that could point at this once a
firm configures it: Gmail push notifications via a small relay, a Typeform
webhook, a CRM's built-in webhook feature. None of that integration lives in
this codebase; this service only verifies, stores, and queues whatever JSON
body shows up.

## Endpoints

`POST /webhooks/{tenant_id}/{source}` — verifies `X-Webhook-Signature`
(HMAC-SHA256 of the raw request body, keyed by the tenant's secret), stores
the parsed JSON body as a pending event, and returns 202 with the full
record. 401 if the signature is missing, wrong, or the tenant has no secret
on file. Logs a low-urgency note to `activity_log_service` on success —
that call failing doesn't fail the request.

`GET /events/pending?tenant_id=&source=` — list unprocessed events,
optionally filtered by tenant and/or source.

`GET /events/{id}` — fetch one event by id. 404 if it doesn't exist.

`POST /events/{id}/mark_processed` — sets `processed: true`. 404 if the id
doesn't exist, 409 if it's already marked processed.

`GET /health` — liveness check.

## Signature verification

Every inbound request must carry `X-Webhook-Signature`: the hex digest of
HMAC-SHA256 over the exact raw body bytes, keyed by a secret unique to the
tenant. This is the same pattern Stripe and GitHub use for their webhooks,
and it's what makes it safe to expose this endpoint on the public internet
(via Cloudflare/APISIX) — anything without a valid signature for the target
tenant gets a 401 and is never stored. Comparisons use `hmac.compare_digest`,
not `==`, so a wrong guess can't be narrowed down by timing.

`sign_payload(secret, raw_body_bytes)` in `client.py` computes this digest,
for tests and for anything on our side that needs to construct a validly
signed request.

## Secrets

Tenant secrets live in a JSON file (`webhook_secrets.json` next to this
service, path configurable via `WEBHOOK_SECRETS_PATH`) mapping `tenant_id ->
secret`. There's no management API for this on purpose — it's a short list
that changes only when a new firm onboards. To add one, generate a random
secret and add an entry by hand:

```
python3 -c "import secrets; print(secrets.token_hex(32))"
```

```json
{
  "acme-legal": "<the generated secret>"
}
```

Give the firm that secret out of band (not over the webhook itself) so
whatever tool they configure — their email provider's relay, their form
tool, their CRM — can sign requests with it.

## Storage

JSON file (`webhook_events.json`, same simplicity level as the other
services), keyed by event id. Point `STORE_PATH` at a real database if this
tenant's event volume ever outgrows it, and nothing calling this service
needs to change.

## Running locally

```
pip install -r requirements.txt
uvicorn webhook_service.main:app --port 8005
```

The poller picks this up via `WEBHOOK_SERVICE_URL` (defaults to
`http://localhost:8005`). Import `client.py` for `get_pending_events`,
`get_event`, `mark_event_processed`, and `sign_payload`.

In production this runs as `legal-webhook.service` on port 8105, same
pattern as `legal-activity-log` (8101), `legal-conflicts` (8102),
`legal-rag` (8103), and `legal-approval` (8104).

**Production must set `ACTIVITY_LOG_SERVICE_URL=http://127.0.0.1:8101`** in
the unit's `Environment=` — `activity_log_service.client`'s default
(`http://localhost:8001`) is the *dev* port, not the production one. Without
this, the request to `/webhooks/{tenant_id}/{source}` still succeeds (the
activity-log call is best-effort and swallows its own failure), but nothing
ever shows up in the activity feed and there's no error to notice. Found
this exact gap after deploying — every webhook received had been silently
failing to log until the unit picked up the env var.
