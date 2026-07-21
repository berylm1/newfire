# Case Service

The client/case record this tenant didn't have. Before this service, there
was no real record of a firm's clients anywhere in the codebase —
`daily_briefing/docket_feed.py` returned hardcoded sample items and
`memory_service` is an append-only note log, not a structured record. Fee
tracking, a client hub, deadline surfacing, priority-date tracking — none of
that is buildable without a real case record to hang it on. This service is
that record.

## Data model

One JSON object per client matter:

- `id` — server-generated uuid.
- `tenant_id` — scopes every record to a firm.
- `client_name`, `assigned_attorney`, `notes` — free text.
- `contact` — `{"email": ..., "phone": ..., "whatsapp": ..., "preferred_language": ...}`,
  all optional. Not every client has all four on file. `preferred_language`
  (an ISO 639-1 code) is set by `intake_form_fill` when a client completes
  a conversational intake in a language other than English.
- `case_type` — free-text label (`"change_of_status"`,
  `"marriage_based_green_card"`, `"asylum"`, ...). Deliberately not an enum
  or a rules engine — case-type-specific playbooks are a later phase, this
  is just a label today.
- `key_dates` — a flexible dict of named date strings (e.g.
  `{"visa_expiration": "2026-08-01", "filing_deadline": "2026-07-20",
  "priority_date": "2023-05-01"}`). Different case types care about
  different dates, so this stays a dict instead of fixed columns.
- `fee_status` — `{"total_fee": number | null, "amount_paid": number |
  null, "status": "paid" | "partial" | "unpaid", "notes": str}`. This is
  the firm's own fee for handling the case, not a government filing fee —
  the two are never the same number and shouldn't be conflated.
- `documents` — a flexible dict of `{document_key: bool}` tracking which of
  a case type's required documents (see `case_jeopardy_check/playbooks.py`)
  are actually on file, e.g. `{"passport_copy": true, "i94_record": false}`.
  This service doesn't know or care what's "required" for a given
  `case_type` — that's the rules engine's job; this just tracks what's in
  hand.
- `financial_snapshot` — a flexible dict for case-type-specific financial
  facts, e.g. `{"funds_available": 15000, "program_cost": 12000}` for a
  change-of-status financial-sufficiency check. Empty for case types that
  don't need one.
- `visa_bulletin_tracking` — `{"category": "F2A" | "EB-2" | ..., "country":
  "Mexico" | ..., "priority_date": "2023-05-01"}` for a case that has a
  priority date at all (family-sponsored or employment-based green card
  matters). `visa_bulletin_check` checks this against the current Visa
  Bulletin (`visa_bulletin_service`). Empty for case types with no
  priority date (asylum, naturalization, non-immigrant H-1B, ...).
- `created_at`, `updated_at`.

## Endpoints

`POST /cases` — body has `tenant_id` and `client_name` required, everything
else optional with sensible defaults (`{}` for `contact`/`key_dates`, an
unpaid `fee_status`). Returns the created record.

`GET /cases/{tenant_id}` — list a tenant's cases. Optional `?case_type=`
filter. Empty list, not a 404, when the tenant has no cases yet.

`GET /cases/{tenant_id}/{case_id}` — fetch one. 404 if missing or if the
case belongs to a different tenant.

`PATCH /cases/{tenant_id}/{case_id}` — partial update. Any field can be
sent; omitted fields are left alone. For the dict-valued fields
(`contact`, `key_dates`, `fee_status`, `documents`, `financial_snapshot`,
`visa_bulletin_tracking`),
the provided dict is **merged** into the existing one rather than
replacing it — `PATCH` with `{"key_dates": {"filing_deadline":
"2026-08-01"}}` updates just that one date without erasing
`visa_expiration` or `priority_date` on the same record, and `PATCH` with
`{"documents": {"passport_copy": true}}` checks off one document without
touching the others. Bumps `updated_at`. 404 if missing or wrong tenant.

`GET /health` — liveness check.

## Why `case_id` is in the URL but `client_name` never would be

`case_id` is a server-generated uuid this service controls, so it's safe as
a path segment. `client_name` is not — `memory_service` already hit this bug
once with `client_key` (party/company names routinely contain `/`, e.g.
`"Jane Doe d/b/a Acme Consulting"`, which breaks path-based routing
outright). This service has no lookup-by-name endpoint yet; if one gets
added, the name belongs in a query param or request body, not the path,
for the same reason.

## Storage

JSON file (`cases.json`, same simplicity level as the other services), keyed
by case id. Point `STORE_PATH` at a real database if a firm's case volume
ever outgrows it, and nothing calling this service needs to change.

## Running locally

```
pip install -r requirements.txt
uvicorn case_service.main:app --port 8007
```

Agents pick this up via `CASE_SERVICE_URL` (defaults to
`http://localhost:8007`). Import `client.py` for `create_case`,
`list_cases`, `get_case`, and `update_case`.

In production this would run as `legal-case.service` on port 8107, same
pattern as the other six services — not deployed this round.
