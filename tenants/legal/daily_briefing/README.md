# Daily Briefing

The agent Mr. Patrick described directly: the attorney should be able to wake
up to one place that says what they actually need to know today, instead of
checking email, a calendar, and two other agents' output separately.

## Why this one has no approval gate

Every other agent in this tenant (intake, citation checker) drafts something
that could leave the firm, so a human has to approve it first. This one
doesn't leave the firm at all — it's read by the attorney and nobody else,
even though it now gets delivered (see below) instead of only printed. There's
nothing to approve; the attorney still makes every actual decision about what
to do with each item. The control principle holds, there's just no separate
"approve to send" step because nothing leaves the firm to a third party.

## Where the docket comes from

Two sources feed the docket, merged in `fetch_docket_node`:

- `activity_log_service` — what the intake agent, the citation checker, and
  the WhatsApp intake handler logged today (a flagged conflict, an
  unverifiable citation, a new document that came in).
- `case_service` — every case on file for the tenant, scanned for
  `key_dates` within the next `KEY_DATE_WINDOW_DAYS` (14, chosen as a
  reasonable near-term window; not tuned to any specific case type yet).
  Each date within that window becomes a docket item with a computed
  urgency (`high` inside 3 days, `medium` inside 7, `low` otherwise) and a
  plain-language summary, e.g. "Visa expiration for Jane Doe is in 5 days."

This replaces the old `docket_feed.py`, which returned four hardcoded sample
items and nothing else — there was no real client data anywhere to draw a
docket from. That file has been removed; nothing else imported it. Real
urgency-tiering per case type (a filing deadline behaves differently than a
priority date) is a later phase — this just needs to surface the date-driven
items instead of only working from a static file.

## Delivery

After drafting the briefing, `send_briefing_node` calls `notify_service` to
deliver it. The recipient is the attorney, not a client, and `assigned_attorney`
on a case record is just a free-text name — not a place to hang the
attorney's own email or phone, since the same attorney is assigned to many
cases. `tenant_config.py` adds the missing piece: a minimal, tenant-scoped
`get_attorney_contact(tenant_id)` backed by a hand-edited JSON file, not a
whole settings service — one tenant, one delivery target is enough for now.
An unconfigured tenant gets an obviously-fake placeholder address rather than
a crash.

`notify_service`'s backend is a local stub this round — see
`../services/notify_service/README.md`. Nothing is actually emailed or
WhatsApp'd out yet; `GET /notify/log` on that service is how you confirm an
attempt happened.

## Swappable, same pattern as the rest of this tenant

`case_service`, `notify_service`, and `tenant_config.py` are all swappable the
same way: point the storage at a real database (or `backends.py` at a real
provider) and nothing calling them needs to change.

## Running it

```
pip install -r requirements.txt
pip install -r ../services/requirements.txt
uvicorn activity_log_service.main:app --port 8001 --app-dir ../services &
uvicorn case_service.main:app --port 8007 --app-dir ../services &
uvicorn notify_service.main:app --port 8008 --app-dir ../services &
python run.py
```
