# Citation & Authority Checker

Legal tenant's second agent (Sprint 2, Week 6, built alongside the Nonprofit
Grant Scout). Reads a draft brief, extracts every cited case, verifies each
one against CourtListener's real case-law database, and produces a report for
attorney review. **Never edits the brief itself** — citation-checking and
brief-drafting are kept strictly separate, per the program's "no auto-edit"
guardrail for this agent.

## Real verification, no synthetic stand-in

`courtlistener.py` calls CourtListener's public search API
(`courtlistener.com/api/rest/v4/search/`). Anonymous requests work
(rate-limited); set `COURTLISTENER_API_TOKEN` for a firm's own account and
higher limits.

## Running it

```
pip install -r requirements.txt
python run.py --brief sample_briefs/mixed_citations.txt
```

`sample_briefs/mixed_citations.txt` cites two real Supreme Court cases
(Marbury v. Madison, Lujan v. Defenders of Wildlife) and one fabricated case
name — the report should verify the first two and flag the third as not
found.

## Known limitation: anonymous rate limiting

Without `COURTLISTENER_API_TOKEN`, anonymous requests get rate-limited fast —
in testing, only the first lookup in a multi-citation brief succeeded before
the rest started timing out. The error handling treats a timeout as "lookup
failed, needs manual check" rather than "not found," so it never confuses
"we couldn't verify this" with "this citation doesn't exist" — but a firm
running this for real, multi-citation briefs needs a CourtListener account
token to get reliable throughput.
