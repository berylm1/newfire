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

1. **First message from a new number** — `detect_case_type_and_language`
   (`translation.py`, one combined LLM call, same "single JSON extraction"
   pattern as `intake_conflict_check`'s matter-type extraction) figures out
   both which of the five case types (`form_schemas.py`) the message is
   about *and* what language it's written in. If the case type can't be
   determined, it asks a clarifying question (translated into whatever
   language was detected) and doesn't save any state — the next message
   tries classification again cold.
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

## Multi-language intake (requirement #7)

Layered on top of the flow above via `translation.py`, not a rewrite of
it. Every outgoing message — questions, reprompts, the confirmation — gets
translated into the language detected on the client's first message.
Coming back the other way, only **dates** get translated to English before
validation; the parser only recognizes English month names, so a client
writing "15 de marzo de 2024" needs that translated before
`_parse_date_answer` can read it. Names and email addresses are never
translated in either direction — neither is natural-language content, and
running a name through an LLM risks it being "corrected" into something
that isn't what the client actually goes by. The client's `client_name` is
also never handed to the LLM as part of a sentence being translated (see
`_complete_intake`): the confirmation template has no name in it at all,
and the name is prepended in its original form after translation.

Self-hosted only (same DGX/Ollama endpoint every other agent here uses —
no external translation API, per the self-hosted mandate). Outgoing
translations are cached (`translation_cache.json`, keyed by language +
source text) since the same handful of questions repeat across every
conversation in a given language; incoming answers aren't cached, since
they're per-client and rarely repeat. English conversations make zero
translation-related LLM calls — both `translate_to_language` and
`translate_to_english` return their input unchanged before touching the
LLM at all.

The detected language is stored on the case record too
(`contact.preferred_language`), so it's available to whatever eventually
handles ongoing client communication in this case, not just the intake
conversation itself.

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
