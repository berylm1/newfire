import argparse
import json
import uuid

from langgraph.types import Command

from graph import graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Path to a text file containing the intake email")
    args = parser.parse_args()

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
