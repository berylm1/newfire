"""Unit coverage for case_jeopardy_check's graph nodes. Exercising the full
compiled graph needs live case_service/activity_log_service/rag_service and
an LLM, so these tests call the node functions directly instead — the same
functions the compiled graph runs, just without the LangGraph plumbing
around them (same approach as intake_conflict_check's
tests/test_graph_recall.py).
"""

import importlib.util
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # for graph.py's own `import playbooks`

# Loaded by explicit file path under a distinguishing name, not a bare
# `import graph` -- this tenant has several same-named graph.py files
# (intake_conflict_check, citation_checker, daily_briefing), and a plain
# `import graph` collides with whichever one Python already cached under
# `sys.modules["graph"]` from an earlier test file in the same pytest run.
_spec = importlib.util.spec_from_file_location(
    "case_jeopardy_graph", os.path.join(os.path.dirname(__file__), "..", "graph.py")
)
jeopardy_graph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jeopardy_graph)


def test_load_case_node_fetches_and_stores_case(monkeypatch):
    case = {"id": "case-1", "client_name": "Priya Raman"}
    seen = {}

    def fake_get_case(tenant_id, case_id):
        seen["tenant_id"] = tenant_id
        seen["case_id"] = case_id
        return case

    monkeypatch.setattr(jeopardy_graph, "get_case", fake_get_case)

    result = jeopardy_graph.load_case_node({"tenant_id": "hawthorn-pell", "case_id": "case-1"})

    assert seen == {"tenant_id": "hawthorn-pell", "case_id": "case-1"}
    assert result == {"case": case}


def test_check_playbook_node_runs_playbook_for_the_loaded_case():
    case = {"case_type": "change_of_status", "documents": {}}

    result = jeopardy_graph.check_playbook_node({"case": case})

    assert any(f["rule"] == "missing_documents" for f in result["flags"])


def test_rag_lookup_node_attaches_citation_above_relevance_threshold(monkeypatch):
    monkeypatch.setattr(
        jeopardy_graph,
        "rag_search",
        lambda query, top_k=1: [{"score": 0.9, "text": "some matched text", "metadata": {"citation": "8 CFR 214.2"}}],
    )

    result = jeopardy_graph.rag_lookup_node({"flags": [{"rule": "ninety_day_rule", "detail": "..."}]})

    assert result["flags"][0]["citation"] == "8 CFR 214.2"


def test_rag_lookup_node_falls_back_to_text_snippet_without_citation_metadata(monkeypatch):
    monkeypatch.setattr(
        jeopardy_graph,
        "rag_search",
        lambda query, top_k=1: [{"score": 0.9, "text": "relevant policy text here", "metadata": {}}],
    )

    result = jeopardy_graph.rag_lookup_node({"flags": [{"rule": "ninety_day_rule", "detail": "..."}]})

    assert result["flags"][0]["citation"] == "relevant policy text here"


def test_rag_lookup_node_ignores_matches_below_relevance_threshold(monkeypatch):
    monkeypatch.setattr(
        jeopardy_graph,
        "rag_search",
        lambda query, top_k=1: [{"score": 0.4, "text": "unrelated text", "metadata": {}}],
    )

    result = jeopardy_graph.rag_lookup_node({"flags": [{"rule": "ninety_day_rule", "detail": "..."}]})

    assert result["flags"][0]["citation"] is None


def test_rag_lookup_node_treats_empty_results_as_no_citation(monkeypatch):
    monkeypatch.setattr(jeopardy_graph, "rag_search", lambda query, top_k=1: [])

    result = jeopardy_graph.rag_lookup_node({"flags": [{"rule": "ninety_day_rule", "detail": "..."}]})

    assert result["flags"][0]["citation"] is None


def test_rag_lookup_node_survives_rag_service_being_unreachable(monkeypatch):
    # rag_service is an enhancement, same "best effort" precedent as
    # intake_conflict_check's recall_node -- a connection error shouldn't
    # fail the whole jeopardy check, just skip the citation.
    def raise_connection_error(query, top_k=1):
        raise ConnectionError("rag_service unreachable")

    monkeypatch.setattr(jeopardy_graph, "rag_search", raise_connection_error)

    result = jeopardy_graph.rag_lookup_node({"flags": [{"rule": "ninety_day_rule", "detail": "..."}]})

    assert result["flags"][0]["citation"] is None


def test_draft_report_node_skips_llm_when_no_flags(monkeypatch):
    llm_called = []
    monkeypatch.setattr(jeopardy_graph, "_llm", lambda: llm_called.append(True))

    result = jeopardy_graph.draft_report_node({"case": {"client_name": "David Chen"}, "flags": []})

    assert llm_called == []
    assert result["draft"] == "No jeopardy flags found for David Chen."


def test_draft_report_node_includes_citation_in_prompt_when_present(monkeypatch):
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "drafted report"
    mock_response.usage_metadata = {"input_tokens": 1, "output_tokens": 1}
    mock_llm.invoke.return_value = mock_response
    monkeypatch.setattr(jeopardy_graph, "_llm", lambda: mock_llm)

    state = {
        "case": {"client_name": "Amara Okafor"},
        "flags": [
            {
                "rule": "ninety_day_rule",
                "urgency": "high",
                "detail": "Only 30 days between entry and filing.",
                "citation": "8 CFR 214.2",
            }
        ],
    }

    jeopardy_graph.draft_report_node(state)

    prompt_sent = mock_llm.invoke.call_args[0][0]
    assert "Amara Okafor" in prompt_sent
    assert "(see 8 CFR 214.2)" in prompt_sent


def test_draft_report_node_omits_citation_parenthetical_when_absent(monkeypatch):
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "drafted report"
    mock_response.usage_metadata = {"input_tokens": 1, "output_tokens": 1}
    mock_llm.invoke.return_value = mock_response
    monkeypatch.setattr(jeopardy_graph, "_llm", lambda: mock_llm)

    state = {
        "case": {"client_name": "Amara Okafor"},
        "flags": [{"rule": "missing_documents", "urgency": "medium", "detail": "Still missing: passport_copy.", "citation": None}],
    }

    jeopardy_graph.draft_report_node(state)

    prompt_sent = mock_llm.invoke.call_args[0][0]
    assert "(see" not in prompt_sent


def test_log_flags_node_logs_one_event_per_flag(monkeypatch):
    logged = []
    monkeypatch.setattr(
        jeopardy_graph, "log_event", lambda event_type, urgency, summary: logged.append((event_type, urgency, summary))
    )

    state = {
        "case": {"client_name": "Amara Okafor"},
        "flags": [
            {"rule": "ninety_day_rule", "urgency": "high", "detail": "flag one"},
            {"rule": "missing_documents", "urgency": "medium", "detail": "flag two"},
        ],
        "draft": "the drafted report",
    }

    result = jeopardy_graph.log_flags_node(state)

    assert len(logged) == 2
    assert logged[0] == ("case_jeopardy_flag", "high", "Amara Okafor: flag one")
    assert logged[1] == ("case_jeopardy_flag", "medium", "Amara Okafor: flag two")
    assert result == {"output": "the drafted report"}


def test_log_flags_node_logs_nothing_when_no_flags(monkeypatch):
    logged = []
    monkeypatch.setattr(jeopardy_graph, "log_event", lambda **kwargs: logged.append(kwargs))

    result = jeopardy_graph.log_flags_node({"case": {"client_name": "David Chen"}, "flags": [], "draft": "clean"})

    assert logged == []
    assert result == {"output": "clean"}
