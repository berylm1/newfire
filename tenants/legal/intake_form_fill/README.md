# Intake Form Fill

Requirement #4 from Mr. Patrick's live product-direction meeting: "the
intake bot should provide them with the form but in a conversational
manner. like walk them through it in a flow." Before this, intake was
one-shot — `intake_conflict_check` reads a whole email at once and drafts
an internal memo. Nothing walked a client through anything themselves.

## Why this isn't a LangGraph graph

Every other agent in this tenant that pauses mid-run does it with
`interrupt()` + `approval_service`, because it's waiting on a *human
decision* that might come at any point in the future (see
`resume_approvals.py`). A conversation with a client is a different shape:
each message from them already arrives as its own separate invocation —
OpenClaw calls `handle_message(phone, message)` once per inbound WhatsApp
message, gets a reply string back synchronously, and sends it. There's
nothing to pause; there's just a small amount of state (which question are
we on, what's been answered so far) to read, advance by one step, and
write back. `conversation_state.json`, keyed by phone number, is that
state — same simplicity level as every other JSON-file store in this
tenant.

## How a conversation runs

1. **First message from a new number** — `_classify_case_type` (one LLM
   call, same pattern as `intake_conflict_check`'s matter-type extraction)
   figures out which of the five case types (`form_schemas.py`) the
   message is about. If it can't tell, it asks a clarifying question and
   doesn't save any state — the next message tries classification again
   cold.
2. **Every message after that** — the client's message is validated
   against the *current* question's expected kind (a date, an email, or
   free text) and, if it passes, recorded at the right nested path in the
   answers dict (`key_dates.us_entry_date`, `contact.email`, ...) and the
   conversation advances to the next question. An invalid date or email
   re-prompts on the *same* question instead of advancing — bad data never
   makes it into a case record.
3. **Last question answered** — a real `case_service.create_case` call
   with everything collected, an `activity_log_service` event so the
   attorney sees a new intake came in, the phone number's state is
   deleted, and the client gets a plain confirmation message.

## Why so few questions per case type

This isn't the whole form — just enough to create a real case record plus
whichever one or two dates actually feed something downstream (`key_dates.
us_entry_date` for `change_of_status` is exactly what
`case_jeopardy_check`'s 90-day-rule check reads). Fee status, which
documents are on file, and financial snapshots stay staff-entered later,
not something to ask a prospective client to self-report through a chat
before they've even engaged the firm.

## No human-approval gate — on purpose

Same reasoning as `daily_briefing` and `case_jeopardy_check`: creating a
case record from a client's own stated answers, and telling the attorney
it happened, is the "low-stakes/routine" tier from the autonomy-tiering
direction, not something resembling legal judgment. The attorney still
reviews the new case — this just means they aren't the bottleneck for a
client answering four questions.

## Running it

```
pip install -r requirements.txt
python handler.py  # not meant to be run directly with no args -- see below
```

In practice this is called via `shared/whatsapp_form_fill_handler.py`,
the same calling convention as `shared/whatsapp_intake_handler.py`:

```
python3 ../shared/whatsapp_form_fill_handler.py "<phone number>" "<message text>"
```

`INTAKE_FORM_STATE_PATH` overrides where conversation state is stored
(defaults to `conversation_state.json` alongside `handler.py`). Requires
`case_service` and `activity_log_service` running.
