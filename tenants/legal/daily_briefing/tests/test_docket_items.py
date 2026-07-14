"""Unit coverage for _docket_items_from_cases — the pure date-window logic
that turns each case's key_dates into briefing items. No live services
needed; this only exercises the date math and urgency tiering.
"""

import importlib.util
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # for graph.py's own `import tenant_config`

# Loaded by explicit file path under a distinguishing name, not a bare
# `import graph` — this tenant has several same-named graph.py files
# (intake_conflict_check, citation_checker, daily_briefing), and a plain
# `import graph` collides with whichever one Python already cached under
# `sys.modules["graph"]` from an earlier test file in the same pytest run.
_spec = importlib.util.spec_from_file_location(
    "daily_briefing_graph", os.path.join(os.path.dirname(__file__), "..", "graph.py")
)
briefing_graph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(briefing_graph)


def _iso(days_from_today: int) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


def test_date_within_window_is_included():
    cases = [{"client_name": "Test Client", "key_dates": {"visa_expiration": _iso(5)}}]
    items = briefing_graph._docket_items_from_cases(cases)
    assert len(items) == 1
    assert items[0]["urgency"] == "medium"
    assert "in 5 days" in items[0]["summary"]


def test_date_beyond_window_is_excluded():
    cases = [{"client_name": "Test Client", "key_dates": {"visa_expiration": _iso(49)}}]
    assert briefing_graph._docket_items_from_cases(cases) == []


def test_date_today_is_included_at_high_urgency():
    cases = [{"client_name": "Test Client", "key_dates": {"visa_expiration": _iso(0)}}]
    items = briefing_graph._docket_items_from_cases(cases)
    assert len(items) == 1
    assert items[0]["urgency"] == "high"


def test_overdue_date_is_surfaced_not_dropped():
    # Regression: a date already in the past used to fail the (0 <= days)
    # window check and vanish from the briefing entirely -- exactly the
    # crisis this feature exists to catch (an expired visa nobody noticed),
    # silently hidden instead of flagged.
    cases = [{"client_name": "Test Client", "key_dates": {"visa_expiration": _iso(-3)}}]
    items = briefing_graph._docket_items_from_cases(cases)
    assert len(items) == 1
    assert items[0]["urgency"] == "high"
    assert "3 days ago" in items[0]["summary"]


def test_far_overdue_date_still_surfaced():
    cases = [{"client_name": "Test Client", "key_dates": {"filing_deadline": _iso(-30)}}]
    items = briefing_graph._docket_items_from_cases(cases)
    assert len(items) == 1
    assert items[0]["urgency"] == "high"
    assert "30 days ago" in items[0]["summary"]


def test_unparseable_date_is_skipped_not_raised():
    cases = [{"client_name": "Test Client", "key_dates": {"visa_expiration": "not-a-date"}}]
    assert briefing_graph._docket_items_from_cases(cases) == []


def test_multiple_cases_and_dates_all_considered():
    cases = [
        {"client_name": "Client A", "key_dates": {"visa_expiration": _iso(2), "priority_date": _iso(100)}},
        {"client_name": "Client B", "key_dates": {"filing_deadline": _iso(-1)}},
    ]
    items = briefing_graph._docket_items_from_cases(cases)
    summaries = {i["summary"] for i in items}
    assert len(items) == 2
    assert any("Client A" in s for s in summaries)
    assert any("Client B" in s for s in summaries)
