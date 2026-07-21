# Visa Bulletin Check

Requirement #10 from Mr. Patrick's live product-direction meeting: track a
client's priority date against the State Department's monthly Visa
Bulletin and flag when it becomes current. `visa_bulletin_service` owns
the real bulletin data (fetched from travel.state.gov, see its README) and
the is-current comparison; this graph is the per-case wiring around it —
same shape as `case_jeopardy_check`, one case in, a short attorney-facing
note out.

## What it does

1. `load_case` — fetches the case from `case_service`.
2. `check_bulletin` — reads `visa_bulletin_tracking` (`category`, `country`,
   `priority_date`) off the case and calls `visa_bulletin_service`. Cases
   with no priority date at all (asylum, naturalization, non-immigrant
   H-1B) skip this cleanly rather than erroring.
3. `draft_report` — a short note for the attorney: nothing tracked, still
   waiting (with the current cutoff and bulletin month for context), or —
   the one that matters — priority date just went current, drafted by the
   LLM.
4. `log_flag` — logs to `activity_log_service` **only when the priority
   date is current**, not every day a case is checked and still waiting. A
   green-card case can sit "not current" for years; a daily "still
   waiting" event for every such case would bury the one thing actually
   worth surfacing. Uses the same shared feed `daily_briefing` already
   reads from — no new delivery plumbing.

No `human_approval_interrupt` — same reasoning as `case_jeopardy_check`,
this is advisory information reaching the attorney about their own case,
not a client-facing draft.

## Running it

```
pip install -r requirements.txt
python run.py --tenant hawthorn-pell
```

Checks every case on file for that tenant. Add `--case-id` to check just
one. Requires `case_service`, `activity_log_service`, and
`visa_bulletin_service` running (the last needs outbound internet access —
see its README).
