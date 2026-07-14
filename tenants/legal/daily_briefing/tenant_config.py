"""Minimal tenant-level config: where does this firm's own briefing go.

`assigned_attorney` on a case record is a free-text name — useful for "who's
handling this file," but not a place to hang the attorney's own contact
info, since the same attorney is assigned to dozens of cases and their
email/phone doesn't belong copied onto every one of them. The briefing is
addressed to the practice itself, not to any client, so it needs its own,
tenant-scoped notion of "where does this firm's briefing go" — a concept
that doesn't exist anywhere else in this tenant yet.

This is deliberately not a settings service: one tenant, one delivery
target, in a JSON file a firm's admin can hand-edit at onboarding. If a firm
ever needs more than one recipient, this is the file that grows, not the
interface callers use.
"""

import json
import os

CONFIG_PATH = os.environ.get(
    "ATTORNEY_CONTACTS_PATH", os.path.join(os.path.dirname(__file__), "attorney_contacts.json")
)

DEFAULT_CHANNEL = "email"


def get_attorney_contact(tenant_id: str) -> dict:
    """Returns {"channel": ..., "to": ...} for delivering tenant_id's daily
    briefing. Falls back to a placeholder address for an unconfigured tenant
    rather than raising — a missing delivery target shouldn't crash the
    whole briefing run, it should just be obviously fake in the log."""
    if not os.path.exists(CONFIG_PATH):
        contacts = {}
    else:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            contacts = json.load(f)

    return contacts.get(tenant_id, {"channel": DEFAULT_CHANNEL, "to": f"attorney+{tenant_id}@example.invalid"})
