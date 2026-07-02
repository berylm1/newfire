import argparse
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

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

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"tenant_id": "legal", "thread_id": thread_id, "prompt": email_text}, config=config)

    print(f"Matter type: {result.get('matter_type')}")
    print(f"Parties: {result.get('party_names')}")
    print(f"Conflicts: {result.get('conflicts')}")
    print("\n--- Draft memo ---\n")
    print(result["draft"])

    # The graph is now paused on human_approval_interrupt — it hasn't returned
    # normally, so "approval_id" isn't in result yet. It's on the interrupt
    # payload instead, which is what's available at pause time.
    approval_id = result["__interrupt__"][0].value["approval_id"]

    # A durable approval_service record now backs this pause — nothing left
    # to do here but wait for a decision. resume_approvals.py picks this up
    # from any process, any time, instead of blocking this one on input().
    print(f"\nSubmitted for approval (id={approval_id}).")
    print("Run resume_approvals.py once a decision is made.")


if __name__ == "__main__":
    main()
