# Intake & Conflict-Check Agent

First agent for the legal tenant (Sprint 2, Week 5). Receives a prospective-client
intake email, extracts party names and matter type, checks them against a
conflicts database, and drafts an intake memo for partner review. Nothing goes
back to the prospective client without explicit partner approval.

## Why this is generic, not firm-specific

Built so it works for any small-to-mid firm, not hardcoded to one customer:

- Conflict checking is now its own service (`../services/conflicts_service/`),
  not a module this agent imports directly — `check_conflicts(party_names)`
  is called over HTTP via `conflicts_service.client`. Swap in a real backend
  (SQL table, CRM export, whatever a given firm already uses) by changing the
  service's storage, not this agent's code. Same logged event also flows
  through `../services/activity_log_service/` so the daily briefing agent
  picks up anything this agent flags, automatically.
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
pip install -r ../services/requirements.txt
uvicorn activity_log_service.main:app --port 8001 --app-dir ../services &
uvicorn conflicts_service.main:app --port 8002 --app-dir ../services &
python run.py --email sample_emails/conflict_intake.txt
```

`sample_emails/clean_intake.txt` has no conflicts. `sample_emails/conflict_intake.txt`
should trigger two conflict hits (the synthetic DB has matching entries for
both named parties).

## Photo/scan intake (`--image`)

```
python run.py --image sample_emails/intake_scan.png
```

Runs the image through `../shared/document_vision.py` first (a self-hosted
vision model on the DGX, `qwen2.5vl:7b`), then feeds the extracted text into
the same pipeline as `--email`. This is the actual mechanism behind "a lawyer
can handle intake without being in the office" — a photo of a paper form
becomes the same kind of input a typed email already was. Tested against a
synthetic scanned intake form with two real conflict hits; extraction was
exact and the conflict-check result matched the `--email` path.
