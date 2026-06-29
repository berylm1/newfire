import argparse
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from langgraph.types import Command

from graph import graph


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--email", help="Path to a text file containing the intake email")
    group.add_argument("--image", help="Path to a photo or scan of an intake form")
    args = parser.parse_args()

    if args.image:
        from document_vision import extract_document_text

        email_text = extract_document_text(args.image)
        print("--- Extracted from image ---\n")
        print(email_text)
        print()
    else:
        with open(args.email, encoding="utf-8") as f:
            email_text = f.read()

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke({"tenant_id": "legal", "prompt": email_text}, config=config)

    print(f"Matter type: {result.get('matter_type')}")
    print(f"Parties: {result.get('party_names')}")
    print(f"Conflicts: {result.get('conflicts')}")
    print("\n--- Draft memo ---\n")
    print(result["draft"])

    approved = input("\nApprove draft? [y/N]: ").strip().lower() == "y"
    if approved:
        result = graph.invoke(Command(resume=True), config=config)
    else:
        result = graph.invoke(Command(resume=False), config=config)

    conflicts = result.get("conflicts", [])
    if conflicts:
        from activity_log_service.client import log_event

        names = ", ".join(c["name"] for c in conflicts)
        log_event(
            "conflict_flag",
            "high",
            f"New intake ({result.get('matter_type', 'unspecified matter')}) flagged a conflict: {names}. Needs a decision before this matter proceeds.",
        )

    print(
        json.dumps(
            {
                "tenant_id": "legal",
                "model": result["model"],
                "matter_type": result.get("matter_type"),
                "party_names": result.get("party_names"),
                "conflicts": result.get("conflicts"),
                "output": result.get("output", ""),
                "approved": approved,
                "latency_ms": result["latency_ms"],
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
            }
        )
    )


if __name__ == "__main__":
    main()
