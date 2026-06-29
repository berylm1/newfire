# Daily Briefing

The agent Mr. Patrick described directly: the attorney should be able to wake
up to one place that says what they actually need to know today, instead of
checking email, a calendar, and two other agents' output separately.

## Why this one has no approval gate

Every other agent in this tenant (intake, citation checker) drafts something
that could leave the firm, so a human has to approve it first. This one
doesn't leave the firm at all — it's read by the attorney and nobody else.
There's nothing to approve; the attorney still makes every actual decision
about what to do with each item. The control principle holds, there's just no
separate "approve to send" step because nothing gets sent anywhere.

## Why it pulls in the other agents' findings

`docket_feed.py` deliberately includes the kind of thing the conflict-checker
and citation-checker already surface (a flagged conflict awaiting a waiver
decision, an unverifiable citation). Without this, an attorney would still
have to go check three separate places. The point of a daily briefing is that
they don't have to.

## Swappable, same pattern as the rest of this tenant

`docket_feed.py` returns synthetic data for now. A real deployment swaps
`get_todays_docket()` for an actual calendar/case-management API call —
same interface, nothing else changes.

## Running it

```
pip install -r requirements.txt
python run.py
```
