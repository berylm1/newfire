"""Unit coverage for recall_node and draft_memo_node's prior-history handling.

No existing test suite covered this graph before this change, and exercising
the full compiled graph (checkpointer + human_approval_interrupt) needs a
live approval_service and an LLM, so these tests call the node functions
directly instead — the same functions the compiled graph runs, just without
the LangGraph plumbing around them. See the module docstring in
`shared/resume_approvals.py`'s companion end-to-end check (run manually, not
part of this suite) for the full graph-plus-memory_service verification.
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services"))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import graph as intake_graph


def _mock_llm_response(text):
    response = MagicMock()
    response.content = text
    response.usage_metadata = {"input_tokens": 1, "output_tokens": 1}
    return response


@patch("graph.get_client_memory")
def test_recall_node_collects_only_parties_with_history(mock_get_client_memory):
    def fake_memory(tenant_id, client_key):
        if client_key == "Marcus Whitfield":
            return {"client_key": client_key, "notes": [{"note": "Prior matter, no conflict."}]}
        return {"client_key": client_key, "notes": []}

    mock_get_client_memory.side_effect = fake_memory

    result = intake_graph.recall_node(
        {"tenant_id": "acme-legal", "party_names": ["Marcus Whitfield", "Someone New"]}
    )

    assert result["prior_history"] == [
        {"party": "Marcus Whitfield", "notes": [{"note": "Prior matter, no conflict."}]}
    ]


@patch("graph.get_client_memory")
def test_recall_node_returns_empty_list_when_no_party_has_history(mock_get_client_memory):
    mock_get_client_memory.return_value = {"client_key": "anyone", "notes": []}

    result = intake_graph.recall_node({"tenant_id": "acme-legal", "party_names": ["Someone New"]})

    assert result["prior_history"] == []


@patch("graph.ChatOpenAI")
def test_draft_memo_prompt_includes_prior_history_when_present(mock_chat_openai):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _mock_llm_response("draft text")
    mock_chat_openai.return_value = mock_llm

    state = {
        "prompt": "raw intake email",
        "matter_type": "llc_formation",
        "party_names": ["Marcus Whitfield"],
        "conflicts": [],
        "prior_history": [
            {
                "party": "Marcus Whitfield",
                "notes": [{"note": "Intake matter (llc_formation): approved on 2026-01-01."}],
            }
        ],
    }

    intake_graph.draft_memo_node(state)

    prompt_sent = mock_llm.invoke.call_args[0][0]
    assert "Prior history with these parties:" in prompt_sent
    assert "Marcus Whitfield: Intake matter (llc_formation): approved on 2026-01-01." in prompt_sent


@patch("graph.ChatOpenAI")
def test_draft_memo_prompt_unchanged_when_no_prior_history(mock_chat_openai):
    # Regression check: a first-time party (the common case) must produce the
    # exact same prompt shape as before recall_node existed, no "Prior
    # history" section at all.
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _mock_llm_response("draft text")
    mock_chat_openai.return_value = mock_llm

    state = {
        "prompt": "raw intake email",
        "matter_type": "llc_formation",
        "party_names": ["Someone New"],
        "conflicts": [],
        "prior_history": [],
    }

    intake_graph.draft_memo_node(state)

    prompt_sent = mock_llm.invoke.call_args[0][0]
    assert "Prior history" not in prompt_sent
    assert prompt_sent == (
        "Draft a short intake memo for a partner to review, based on this "
        "prospective-client matter. Include: matter type, parties involved, "
        "conflict-check results, and a recommendation on whether to proceed "
        "to engagement or escalate the conflict for partner review.\n\n"
        "Matter type: llc_formation\n"
        "Parties: Someone New\n"
        "Conflict check results:\nNo conflicts found.\n\n"
        "Original intake email:\nraw intake email"
    )
