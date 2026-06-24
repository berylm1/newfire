# Grant Prospect Scout

Nonprofit tenant's first agent (Sprint 2, Week 6). Searches open funding
opportunities against the org's mission keywords, scores them for fit and
deadline urgency, and drafts a digest for the Executive Director — who
reviews before anything goes further. The agent never contacts funders
directly.

## Real data, no synthetic stand-in needed

Unlike the legal intake agent, this one queries a real, open API:
[Grants.gov search2](https://api.grants.gov/v1/api/search2) — no API key
required. `grants_gov.py` is the client; `fit_scoring.py` is pure
deterministic scoring logic (no LLM), so the ranking stays auditable.

Score = number of matched mission keywords + a deadline-urgency bonus
(closer deadlines score higher; forecasted opportunities with no close date
yet still surface, just lower).

## Running it

```
pip install -r requirements.txt
python run.py --keywords "housing,food access,homelessness"
```

## Not yet wired up

- **Weekly cron**: this runs on demand right now, not on a Monday schedule.
  Scheduling is an infra/ops task, not a workflow-logic one — same graph,
  just needs a cron trigger.
- **Candid**: Grants.gov covers federal opportunities; Candid (foundation/private
  grants) needs a paid API key, so it isn't wired in yet.
