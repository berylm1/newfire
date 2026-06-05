import json
from pathlib import Path

import pytest

from app import classifier


@pytest.mark.asyncio
async def test_dispatch_acceptance_cases_use_expected_tool_and_stage(monkeypatch):
    monkeypatch.setattr(classifier, "_call_stage_b_model", _disabled_model)
    cases_path = Path(__file__).with_name("dispatch_cases.json")
    cases = json.loads(cases_path.read_text())["cases"]

    for case in cases:
        tool, reason = await classifier.classify(case["prompt"])
        assert tool == case["expect_tool"]
        assert reason.startswith(f"stage_{case['expect_stage'].lower()}")


@pytest.mark.asyncio
async def test_stage_b_uses_llm_when_it_returns_valid_tool(monkeypatch):
    async def fake_model(prompt: str):
        return ("direct", "stage_b_llm: LiteLLM classifier returned 'direct'")

    monkeypatch.setattr(classifier, "_call_stage_b_model", fake_model)

    tool, reason = await classifier.stage_b("Summarize this repository status.")

    assert tool == "direct"
    assert reason.startswith("stage_b_llm")


@pytest.mark.asyncio
async def test_stage_b_falls_back_when_llm_fails(monkeypatch):
    async def broken_model(prompt: str):
        raise RuntimeError("router unavailable")

    monkeypatch.setattr(classifier, "_call_stage_b_model", broken_model)

    tool, reason = await classifier.stage_b(
        "Add tenant tests and run the suite after that."
    )

    assert tool == "openhands"
    assert reason.startswith("stage_b_rules")


def test_parse_tool_response_rejects_ambiguous_output():
    assert classifier._parse_tool_response("opencode") == "opencode"
    assert classifier._parse_tool_response("Use OpenHands.") == "openhands"
    assert classifier._parse_tool_response("openhands or opencode") is None
    assert classifier._parse_tool_response("unknown") is None


async def _disabled_model(prompt: str):
    return None
