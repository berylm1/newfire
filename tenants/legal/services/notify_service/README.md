# Notify Service

The generic outbound delivery door this tenant didn't have. Every service
built so far stores or queues data — none of them actually deliver a
message to a person. This is the mirror image of `webhook_service` (the
generic inbound trigger): `POST /notify` with a channel and a recipient, and
this service handles getting it there. It doesn't know or care about
tenant-specific content — same spirit as `webhook_service` not caring which
vendor sent an inbound event.

## Not wired to a real provider yet — on purpose

No firm has a real SMTP account or WhatsApp Business API credential set up
yet, and this round is local-only. `backends.send` is a stub: it durably
records what *would* have been sent to `sent_log.json` instead of calling
any external API. This is intentional, not a placeholder someone forgot to
finish — it makes the service fully testable today, and gives a real,
contained integration point for later. Swapping in a real SMTP client or
WhatsApp-send call means changing `backends.py`; nothing calling this
service needs to change.

Read-aloud/TTS delivery (so an attorney could have a briefing read to them
instead of reading it) is a deferred follow-up, not in scope this round.

## Endpoints

`POST /notify` — body `{"tenant_id": str, "channel": "email" | "whatsapp",
"to": str, "subject": str | None, "body": str}`. 422 if `channel` isn't one
of the supported values. Calls `backends.send` and returns the resulting
record (`id`, `status: "sent"`, `channel`, `to`, `subject`, `body`,
`sent_at`).

`GET /notify/log?tenant_id=` — everything "sent" so far, optionally
filtered by tenant. This is the verification surface for testing — since
there's no real provider yet, this is how a caller confirms an attempt
happened at all.

`GET /health` — liveness check.

## Storage

JSON file (`sent_log.json`, same simplicity level as the other services),
append-only. Point `SENT_LOG_PATH` (in `backends.py`) at a real database if
this ever needs to persist beyond a file.

## Running locally

```
pip install -r requirements.txt
uvicorn notify_service.main:app --port 8008
```

Agents pick this up via `NOTIFY_SERVICE_URL` (defaults to
`http://localhost:8008`). Import `client.py` for `send_notification` and
`get_notify_log`.

In production this would run as `legal-notify.service` on port 8108, same
pattern as the other services — not deployed this round.
