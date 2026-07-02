import argparse
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from graph import graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", required=True, help="Path to a text file containing the draft brief")
    args = parser.parse_args()

    with open(args.brief, encoding="utf-8") as f:
        brief_text = f.read()

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"tenant_id": "legal", "thread_id": thread_id, "prompt": brief_text}, config=config)

    print(f"Citations found: {result.get('citations_found')}\n")
    print("--- Verification results ---")
    for r in result.get("verification_results", []):
        print(r)
    print("\n--- Draft report ---\n")
    print(result["draft"])

    # The graph is now paused on human_approval_interrupt with a durable
    # approval_service record backing it — nothing left to do here but wait
    # for a decision. resume_approvals.py picks this up from any process,
    # any time, instead of blocking this one on a synchronous input().
    print(f"\nSubmitted for approval (id={result['approval_id']}).")
    print("Run resume_approvals.py once a decision is made.")


if __name__ == "__main__":
    main()
