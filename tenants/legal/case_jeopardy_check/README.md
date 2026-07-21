# Case Jeopardy Check

Requirement #5 from Mr. Patrick's live product-direction meeting: "all
things that could create issues with their immigration application should
be flagged." Before this, that was one generic idea with no real
implementation. This turns it into an actual per-case-type rules engine —
"case-type-specific playbooks (what to flag for a marriage-based green card
vs. an asylum case), not one generic check."

## Where the rules live

`playbooks.py` is the rules engine itself — plain Python, no LLM. For each
`case_type` it defines:

- a **required-document checklist** (checked against the case's `documents`
  field on `case_service`)

and, where applicable, case-type-specific checks. Today that's two, both
specific to `change_of_status`:

- **The 90-day rule** — flags a change-of-status filing (or an
  as-of-today check before one's filed) inside 90 days of the client's
  U.S. entry date, the rough marker USCIS uses for preconceived intent.
- **Financial sufficiency** — flags when a case's `financial_snapshot`
  shows documented funds below the stated program cost.

These checklists and thresholds are a researched starting baseline (cross-
checked against a proposed agentic COS workflow), not settled legal fact —
an attorney should treat this as a first draft to refine per case type, not
something to file against unreviewed. Five case types have a starter
playbook today: `change_of_status`, `marriage_based_green_card`, `asylum`,
`h1b`, `naturalization`. A case whose `case_type` isn't in `PLAYBOOKS` yet
produces zero flags rather than an error — silently skipped, not silently
wrong.

## What the graph does with those flags

1. `load_case` — fetches the case from `case_service`.
2. `check_playbook` — runs `playbooks.run_checks` against it.
3. `rag_lookup` — best-effort, for each flag: searches `rag_service` for a
   supporting citation. Below `RAG_RELEVANCE_THRESHOLD` (0.75 cosine
   similarity) or on any error, the flag just gets no citation rather than
   an irrelevant one — an unrelated top-1 match from a sparse corpus is
   worse than nothing in a legal context.
4. `draft_report` — an LLM turns the raw flags into a short, plain-language
   report for the attorney.
5. `log_flags` — every flag is logged to `activity_log_service`
   (`event_type="case_jeopardy_flag"`), the same shared feed
   `daily_briefing` already reads from. No new delivery plumbing — a
   jeopardy flag shows up in tomorrow's morning briefing automatically.

## Not gated behind human approval — on purpose

Unlike `citation_checker` and `intake_conflict_check`, this graph has no
`human_approval_interrupt`. It never leaves the firm — it's advisory
information reaching the attorney about their own case, the same category
as `daily_briefing`, not a client-facing draft. See the autonomy-tiering
direction from the same product-direction meeting.

## The `rag_lookup` citation is wired, not populated

`rag_service`'s corpus (`legal_documents` in Qdrant) has real case-law
citations working already via the citation checker, but nobody has loaded
the USCIS Policy Manual into it yet — that's real content-sourcing work,
not something to fabricate. Until it's populated, every flag's `citation`
will legitimately come back `None`, which is correct behavior (see the
relevance threshold above), not a bug. Loading real Policy Manual sections
into `rag_service` is the natural next step to make citations actually
show up.

## Running it

```
pip install -r requirements.txt
python run.py --tenant hawthorn-pell
```

Checks every case on file for that tenant. Add `--case-id` to check just
one. Requires `case_service`, `activity_log_service`, and `rag_service`
running (`rag_service` degrades gracefully if it isn't — see above).
