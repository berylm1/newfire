# Intake & Conflict-Check Agent

First agent for the legal tenant (Sprint 2, Week 5). Receives a prospective-client
intake email, extracts party names and matter type, checks them against a
conflicts database, and drafts an intake memo for partner review. Nothing goes
back to the prospective client without explicit partner approval.

## Why this is generic, not firm-specific

Built so it works for any small-to-mid firm, not hardcoded to one customer:

- `conflicts_db.py` defines a `check_conflicts(party_names)` interface backed by
  synthetic data. Swap in a real backend (SQL table, CRM export, whatever a
  given firm already uses) without touching the graph.
- Model, base URL, and API key are all environment-driven (`LLM_MODEL`,
  `LLM_BASE_URL`, `LLM_API_KEY`) — same pattern as `workflows/skeleton/`.
- No client data is hardcoded anywhere. `sample_emails/` contains synthetic
  test cases only.

## Why synthetic data, not real client data

This does not connect to the existing `funmi-legal` agent or its (currently
undeployed) RAG setup. That's separate, real client work from a different
engagement; this agent is intentionally self-contained until a specific firm's
conflicts data is ready to wire in.

## Running it

```
pip install -r requirements.txt
python run.py --email sample_emails/conflict_intake.txt
```

`sample_emails/clean_intake.txt` has no conflicts. `sample_emails/conflict_intake.txt`
should trigger two conflict hits (the synthetic DB has matching entries for
both named parties).
