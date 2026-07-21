"""Unit coverage for visa_bulletin_check's graph nodes. Exercising the full
compiled graph needs live case_service/activity_log_service/
visa_bulletin_service and an LLM, so these tests call the node functions
directly instead (same approach as case_jeopardy_check's and
intake_conflict_check's tests).
"""

import importlib.util
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services"))

# Loaded by explicit file path under a distinguishing name, not a bare
# `import graph` -- this tenant has several same-named graph.py files
# (intake_conflict_check, citation_checker, daily_briefing,
# case_jeopardy_check), and a plain `import graph` collides with whichever
# one Python already cached under `sys.modules["graph"]` from an earlier
# test file in the same pytest run.
_spec = importlib.util.spec_from_file_location(
    "visa_bulletin_check_graph", os.path.join(os.path.dirname(__file__), "..", "graph.py")
)
bulletin_graph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bulletin_graph)


def test_load_case_node_fetches_and_stores_case(monkeypatch):
    case = {"id": "case-1", "client_name": "Miguel Torres"}
    seen = {}

    def fake_get_case(tenant_id, case_id):
        seen["tenant_id"] = tenant_id
        seen["case_id"] = case_id
        return case

    monkeypatch.setattr(bulletin_graph, "get_case", fake_get_case)

    result = bulletin_graph.load_case_node({"tenant_id": "hawthorn-pell", "case_id": "case-1"})

    assert seen == {"tenant_id": "hawthorn-pell", "case_id": "case-1"}
    assert result == {"case": case}


def test_check_bulletin_node_skips_case_with_no_tracking_data():
    result = bulletin_graph.check_bulletin_node({"case": {"visa_bulletin_tracking": {}}})

    assert result == {"tracked": False}


def test_check_bulletin_node_skips_case_with_partial_tracking_data():
    # category present but no priority_date -- not enough to check.
    result = bulletin_graph.check_bulletin_node({"case": {"visa_bulletin_tracking": {"category": "F2A"}}})

    assert result == {"tracked": False}


def test_check_bulletin_node_calls_service_with_tracking_fields(monkeypatch):
    seen = {}

    def fake_check(category, priority_date, country=None):
        seen.update(category=category, priority_date=priority_date, country=country)
        return {"current": True, "cutoff": "2025-07-22", "category": category, "country": "MEXICO", "bulletin_month": "August 2026"}

    monkeypatch.setattr(bulletin_graph, "check_priority_date", fake_check)

    result = bulletin_graph.check_bulletin_node(
        {"case": {"visa_bulletin_tracking": {"category": "F2A", "country": "Mexico", "priority_date": "2024-01-01"}}}
    )

    assert seen == {"category": "F2A", "priority_date": "2024-01-01", "country": "Mexico"}
    assert result["tracked"] is True
    assert result["check_result"]["current"] is True


def test_draft_report_node_skips_llm_when_not_tracked(monkeypatch):
    llm_called = []
    monkeypatch.setattr(bulletin_graph, "_llm", lambda: llm_called.append(True))

    result = bulletin_graph.draft_report_node({"case": {"client_name": "David Chen"}, "tracked": False})

    assert llm_called == []
    assert result["draft"] == "No priority date on file to track for David Chen."


def test_draft_report_node_skips_llm_when_not_yet_current(monkeypatch):
    llm_called = []
    monkeypatch.setattr(bulletin_graph, "_llm", lambda: llm_called.append(True))

    state = {
        "case": {"client_name": "Miguel Torres"},
        "tracked": True,
        "check_result": {
            "current": False,
            "cutoff": "2025-07-22",
            "category": "F2A",
            "country": "MEXICO",
            "bulletin_month": "August 2026",
        },
    }

    result = bulletin_graph.draft_report_node(state)

    assert llm_called == []
    assert "Miguel Torres" in result["draft"]
    assert "not yet current" in result["draft"]
    assert "2025-07-22" in result["draft"]


def test_draft_report_node_calls_llm_when_current(monkeypatch):
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Miguel's priority date is current -- worth a call this week."
    mock_response.usage_metadata = {"input_tokens": 1, "output_tokens": 1}
    mock_llm.invoke.return_value = mock_response
    monkeypatch.setattr(bulletin_graph, "_llm", lambda: mock_llm)

    state = {
        "case": {"client_name": "Miguel Torres"},
        "tracked": True,
        "check_result": {
            "current": True,
            "cutoff": "2025-07-22",
            "category": "F2A",
            "country": "MEXICO",
            "bulletin_month": "August 2026",
        },
    }

    result = bulletin_graph.draft_report_node(state)

    prompt_sent = mock_llm.invoke.call_args[0][0]
    assert "Miguel Torres" in prompt_sent
    assert "F2A" in prompt_sent
    assert result["draft"] == "Miguel's priority date is current -- worth a call this week."


def test_log_flag_node_logs_when_current(monkeypatch):
    logged = []
    monkeypatch.setattr(
        bulletin_graph, "log_event", lambda event_type, urgency, summary: logged.append((event_type, urgency, summary))
    )

    state = {
        "case": {"client_name": "Miguel Torres"},
        "tracked": True,
        "check_result": {"current": True},
        "draft": "now current",
    }

    result = bulletin_graph.log_flag_node(state)

    assert len(logged) == 1
    assert logged[0][0] == "priority_date_current"
    assert logged[0][1] == "high"
    assert "Miguel Torres" in logged[0][2]
    assert result == {"output": "now current"}


def test_log_flag_node_does_not_log_when_not_current(monkeypatch):
    logged = []
    monkeypatch.setattr(bulletin_graph, "log_event", lambda **kwargs: logged.append(kwargs))

    state = {
        "case": {"client_name": "Miguel Torres"},
        "tracked": True,
        "check_result": {"current": False},
        "draft": "not yet current",
    }

    result = bulletin_graph.log_flag_node(state)

    assert logged == []
    assert result == {"output": "not yet current"}


def test_log_flag_node_does_not_log_when_not_tracked(monkeypatch):
    logged = []
    monkeypatch.setattr(bulletin_graph, "log_event", lambda **kwargs: logged.append(kwargs))

    state = {"case": {"client_name": "David Chen"}, "tracked": False, "draft": "no priority date"}

    result = bulletin_graph.log_flag_node(state)

    assert logged == []
    assert result == {"output": "no priority date"}
