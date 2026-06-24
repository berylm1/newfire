import argparse
import json
import uuid

from langgraph.types import Command

from graph import graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", required=True, help="Path to a text file containing the draft brief")
    args = parser.parse_args()

    with open(args.brief, encoding="utf-8") as f:
        brief_text = f.read()

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke({"tenant_id": "legal", "prompt": brief_text}, config=config)

    print(f"Citations found: {result.get('citations_found')}\n")
    print("--- Verification results ---")
    for r in result.get("verification_results", []):
        print(r)
    print("\n--- Draft report ---\n")
    print(result["draft"])

    approved = input("\nApprove report? [y/N]: ").strip().lower() == "y"
    if approved:
        result = graph.invoke(Command(resume=True), config=config)
    else:
        result = graph.invoke(Command(resume=False), config=config)

    print(
        json.dumps(
            {
                "tenant_id": "legal",
                "model": result["model"],
                "citations_found": result.get("citations_found"),
                "verification_results": result.get("verification_results"),
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
