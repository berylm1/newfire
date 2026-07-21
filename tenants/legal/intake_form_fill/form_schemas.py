"""Per-case-type intake question schemas — requirement #4 from Mr.
Patrick's product-direction meeting: "the intake bot should provide them
with the form but in a conversational manner. like walk them through it in
a flow."

Each schema is an ordered list of (field_path, question) pairs. field_path
tells handler.py exactly where the answer lands in a real `case_service`
record — "key_dates.us_entry_date" becomes {"key_dates": {"us_entry_date":
...}}, so a completed conversation produces a case record with no
translation step in between.

Deliberately minimal, not every field a case could ever have — this
collects only what's needed to create a real case record plus the one or
two case-type-specific dates that actually feed something downstream (the
90-day rule in case_jeopardy_check reads key_dates.us_entry_date for
change_of_status; a priority date would come from visa_bulletin_tracking,
set later once USCIS assigns one, not something a client knows to give at
intake). Fee status, documents-on-file, and financial snapshots stay staff-
entered, not something to ask a prospective client to self-report through
a chat.

Same five case types as case_jeopardy_check's PLAYBOOKS, for the same
reason: these are the case types Hawthorn & Pell actually handles. The two
modules aren't merged into one shared file — each is small, and one asks
"what do we already have," the other asks "what do we still need" — but
they're kept in sync on case_type naming deliberately.
"""

FORM_SCHEMAS = {
    "change_of_status": [
        ("client_name", "What's your full legal name?"),
        ("contact.email", "What's the best email address to reach you at?"),
        ("key_dates.us_entry_date", "What date did you enter the U.S.? (YYYY-MM-DD)"),
        ("key_dates.visa_expiration", "When does your current visa or I-94 expire? (YYYY-MM-DD)"),
    ],
    "marriage_based_green_card": [
        ("client_name", "What's your full legal name?"),
        ("contact.email", "What's the best email address to reach you at?"),
        ("key_dates.marriage_date", "What date did you get married? (YYYY-MM-DD)"),
    ],
    "asylum": [
        ("client_name", "What's your full legal name?"),
        ("contact.email", "What's the best email address to reach you at?"),
        ("key_dates.us_entry_date", "What date did you enter the U.S.? (YYYY-MM-DD)"),
    ],
    "h1b": [
        ("client_name", "What's your full legal name?"),
        ("contact.email", "What's the best email address to reach you at?"),
        ("key_dates.visa_expiration", "When does your current visa expire? (YYYY-MM-DD)"),
    ],
    "naturalization": [
        ("client_name", "What's your full legal name?"),
        ("contact.email", "What's the best email address to reach you at?"),
        ("key_dates.green_card_date", "What date did you receive your green card? (YYYY-MM-DD)"),
    ],
}
