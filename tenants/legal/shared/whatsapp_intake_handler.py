#!/usr/bin/env python3
"""Non-interactive entry point for gateway-triggered WhatsApp document intake.

Called by the legal-intake-handler agent's exec tool after OpenClaw's own
image tool has already turned an inbound photo into text. This script never
sends the conflict-check result anywhere external — it only logs a triage
flag for the attorney's daily briefing, and returns a short, generic
acknowledgment for the agent to reply with. The attorney still makes every
real decision; this just makes sure nothing sits unseen until someone happens
to check three different places.

Party extraction uses the same LLM call the full intake agent uses, not a
cheap regex heuristic — a missed conflict because the auto-triage step took
a shortcut is a real liability problem, not an acceptable speed tradeoff.

Usage: python3 whatsapp_intake_handler.py "<extracted document text>"
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from activity_log_service.client import log_event
from conflicts_service.client import check_conflicts

DEFAULT_MODEL = "glm4:9b"
DEFAULT_BASE_URL = "http://100.88.112.5:11434/v1"


def extract_party_names(document_text: str) -> list[str]:
    from langchain_openai import ChatOpenAI

    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.environ.get("LLM_API_KEY", "ollama")
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    llm = ChatOpenAI(api_key=api_key, base_url=base_url, model=model)

    prompt = (
        "Extract every person or company named anywhere in this document — "
        "in labeled fields and in free-text descriptions. Respond with ONLY "
        'a JSON object, no other text: {"party_names": ["..."]}\n\n'
        f"Document:\n{document_text}"
    )
    response = llm.invoke(prompt)
    match = re.search(r"\{.*\}", str(response.content), re.DOTALL)
    try:
        parsed = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        parsed = {}
    return parsed.get("party_names", [])


def main() -> None:
    if len(sys.argv) < 2:
        print("Sorry, I couldn't read that — could you try sending it again?")
        return

    document_text = sys.argv[1]
    party_names = extract_party_names(document_text)
    conflicts = check_conflicts(party_names) if party_names else []

    if conflicts:
        names = ", ".join(c["name"] for c in conflicts)
        log_event(
            "conflict_flag",
            "high",
            f"Auto-triaged WhatsApp intake flagged a possible conflict: {names}. "
            f"Needs attorney review — not yet a final conflict determination.",
        )
    else:
        log_event(
            "internal",
            "low",
            "A new document came in over WhatsApp and has been queued for intake review.",
        )

    print(
        "Thanks for sending this over — we've received it and someone from "
        "the firm will follow up with you shortly."
    )


if __name__ == "__main__":
    main()
