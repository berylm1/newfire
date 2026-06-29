"""Today's docket — deadlines and follow-ups that don't come from another agent.

Swappable interface, same pattern as conflicts_db.py and grants_gov.py: a real
firm plugs in their actual calendar/case-management system here.

Conflict flags and citation reviews aren't listed here anymore — those come
from activity_log.py, logged for real by the intake and citation agents when
they actually find something. This file is just the calendar-style items
nothing else produces yet.
"""

SYNTHETIC_DOCKET = [
    {
        "type": "court_deadline",
        "urgency": "high",
        "summary": "Response to motion to dismiss is due today in Okafor v. Whitfield Properties LLC.",
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
