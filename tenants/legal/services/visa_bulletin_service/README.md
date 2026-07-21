# Visa Bulletin Service

Requirement #10 from Mr. Patrick's live product-direction meeting: track a
client's priority date against the State Department's monthly Visa
Bulletin and flag when it becomes current. Nothing else in this tenant
tracked this before — a real, distinct immigration-specific pain point,
confirmed by research (see the immigration-tenant-pivot notes), not
something a generic deadline-tracker would ever know to check.

## Real data, no synthetic stand-in

Same principle as `citation_checker`'s real CourtListener calls: this
fetches the actual monthly Visa Bulletin PDF from
`travel.state.gov/content/dam/visas/Bulletins/visabulletin_<Month><Year>.pdf`
and parses the real Final Action Dates tables — Family-Sponsored (F1, F2A,
F2B, F3, F4) and Employment-Based (EB-1 through EB-5, including the
Other-Workers and 5th-preference set-asides). Final Action Dates, not
"Dates for Filing" — Final Action is what actually determines when a green
card can be issued; Dates for Filing is only sometimes usable, at USCIS's
monthly discretion.

## Why the PDF and not the HTML bulletin page

The HTML page is behind a Cloudflare bot-check that returns a JS challenge
("Just a moment...") to any plain HTTP client — confirmed directly, a
`requests.get()` to the HTML page gets a 403, and even this tenant's
browser-automation tooling needed a real render pass to get through it.
The PDF asset path (`/content/dam/visas/Bulletins/...`) is **not** behind
that same challenge — confirmed with a direct `requests.get()`, no
workaround, no headless browser, no bot-detection evasion. Parsing a PDF
programmatically ends up being simpler *and* more honest than scraping the
protected page would have been.

## How the parser works (`parser.py`)

PyMuPDF extracts each page's text in reading order, so a table's cells come
out as a flat sequence of lines, not real rows/columns — category label,
then its five country values, repeated:

- **Family-sponsored** labels are always one line (`F1`, `F2A`, ...), so
  they're matched by exact text.
- **Employment-based** labels wrap across multiple lines (e.g. `5th
  Unreserved (including C5, T5, I5, R5, NU, RU)`), so those are parsed by
  accumulating lines until five consecutive value-shaped tokens (a date
  like `15DEC18`, or `C`, or `U`) appear — whatever came before those five
  lines is the label, however many lines it took. Labels are then
  normalized to short codes (`EB-1` … `EB-5-infrastructure`) via
  `EB_LABEL_TO_CODE`.
- Page headers/footers (department name, page number, "`<Month> <year>`")
  repeat on every PDF page and get stripped before parsing — otherwise a
  table spanning a page break leaks that text into whatever label or row
  happens to be accumulating at that point.
- Every date is a `DDMMMYY` token — parsed with a loose sanity check (must
  land within about 2 years of today) to catch a wild 2-digit-year
  misparse without rejecting legitimate near-term cutoffs (a category like
  F2A can genuinely list a cutoff a day or two from today).

Tested against a real, committed fixture (`tests/fixtures/
visabulletin_august2026.pdf`, the actual August 2026 publication,
cross-checked against the live HTML page) rather than synthetic data —
values are asserted against what that specific bulletin actually says.

## Fetch + cache behavior (`main.py`)

The bulletin only changes once a month, so `get_current_bulletin()` only
re-fetches when the cache isn't already for a plausible current month.
Tries next month's bulletin first (usually already published by the
second half of the current month), then the current month, then the
previous month as a last resort. A live-fetch failure falls back to
whatever's cached (marked `"stale": true`) rather than hard-failing —
most categories don't move every month anyway. A 503 only happens if
nothing has ever been successfully cached and no live fetch succeeds.

## Endpoints

`GET /bulletin/current` — the parsed bulletin: `{"bulletin_month", "family_sponsored", "employment_based"}` (plus `"stale": true` if serving an old cached copy after a failed refresh).

`POST /check` — body `{"category": "F2A" | "EB-2" | ..., "country": "Mexico" | "China" | "India" | "Philippines" | null, "priority_date": "2023-05-01"}`. Country is case-insensitive and defaults to `"All Chargeability Areas Except Those Listed"` for anything unrecognized or omitted — which is the correct real-world behavior, not a fallback of convenience: only those four countries are ever separately listed as oversubscribed. Returns `{"current": bool, "cutoff": "2023-08-01" | "C" | "U", "category", "country", "bulletin_month"}`. 422 if `category` isn't a real category in the current bulletin.

`GET /health` — liveness check.

## Running locally

```
pip install -r requirements.txt
uvicorn visa_bulletin_service.main:app --port 8010
```

Needs outbound internet access to `travel.state.gov` — unlike the other
services in this tenant, this one isn't purely internal. Agents pick this
up via `VISA_BULLETIN_SERVICE_URL` (defaults to `http://localhost:8010`).
Import `client.py` for `get_current_bulletin` and `check_priority_date`.

In production this would run as `legal-visa-bulletin.service` on port
8110, same pattern as the other services — not deployed this round.
