"""Today's docket — deadlines, follow-ups, and pending items.

Swappable interface, same pattern as conflicts_db.py and grants_gov.py: a real
firm plugs in their actual calendar/case-management system here. The synthetic
data below also deliberately surfaces what the other legal-tenant agents
already found, so the briefing is one place to look instead of three.
"""

SYNTHETIC_DOCKET = [
    {
        "type": "court_deadline",
        "urgency": "high",
        "summary": "Response to motion to dismiss is due today in Okafor v. Whitfield Properties LLC.",
    },
    {
        "type": "conflict_flag",
        "urgency": "high",
        "summary": (
            "Yesterday's intake for Dana Okafor flagged a conflict: Marcus Whitfield is a "
            "former client. Still needs a conflict-waiver decision before the matter proceeds."
        ),
    },
    {
        "type": "citation_review",
        "urgency": "medium",
        "summary": (
            "The citation checker flagged one unverifiable case (\"Smithson v. General Fabricated "
            "Holdings Corp.\") in the draft brief. Needs a manual check before filing."
        ),
    },
    {
        "type": "client_followup",
        "urgency": "medium",
        "summary": "Priya Raman (Sunrise Bakeshop) has been waiting 3 days for a reply on her lease review.",
    },
    {
        "type": "pending_signature",
        "urgency": "low",
        "summary": "The engagement letter sent to a new client 2 days ago still hasn't been signed.",
    },
    {
        "type": "internal",
        "urgency": "low",
        "summary": "Two intake memos from this week are still sitting in the partner review queue.",
    },
]


def get_todays_docket() -> list[dict]:
    """Return today's docket items. Static for now — swap in a real calendar/
    case-management API call here."""
    return SYNTHETIC_DOCKET
