"""Notify service — the generic outbound delivery door this tenant didn't
have. Every agent that draws a conclusion worth telling someone (the daily
briefing reaching the attorney, eventually a reminder reaching a client) had
nowhere to actually send it — the existing services store and queue data,
none of them deliver anything. This is the mirror image of `webhook_service`
(the generic inbound trigger): it doesn't know or care about tenant-specific
content, it just delivers a message via a named channel and records what
happened.

No firm has a real SMTP account or WhatsApp Business API credential wired up
yet, so delivery goes through `backends.send`, a local stub — see
`backends.py`. Swapping in a real provider later is a contained change
there, not a rewrite of this file.

Read-aloud/TTS delivery is a deferred follow-up, not in scope here.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from notify_service import backends

SUPPORTED_CHANNELS = ("email", "whatsapp")

app = FastAPI(title="Notify Service")


class NotifyIn(BaseModel):
    tenant_id: str
    channel: str
    to: str
    subject: str | None = None
    body: str


@app.post("/notify")
def send_notification(notification: NotifyIn) -> dict:
    if notification.channel not in SUPPORTED_CHANNELS:
        raise HTTPException(status_code=422, detail=f"unsupported channel: {notification.channel}")

    return backends.send(
        tenant_id=notification.tenant_id,
        channel=notification.channel,
        to=notification.to,
        subject=notification.subject,
        body=notification.body,
    )


@app.get("/notify/log")
def get_notify_log(tenant_id: str | None = None) -> list[dict]:
    entries = backends.get_log()
    if tenant_id is not None:
        entries = [e for e in entries if e["tenant_id"] == tenant_id]
    return entries


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
