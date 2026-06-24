import argparse
import json
import uuid

from langgraph.types import Command

from graph import graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--keywords",
        required=True,
        help="Comma-separated mission keywords, e.g. 'housing,food access,homelessness'",
    )
    args = parser.parse_args()
    mission_keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke({"tenant_id": "nonprofit", "mission_keywords": mission_keywords}, config=config)

    print(f"Found {len(result.get('top_opportunities', []))} top-scoring opportunities.\n")
    print("--- Draft digest ---\n")
    print(result["draft"])

    approved = input("\nApprove digest for ED review? [y/N]: ").strip().lower() == "y"
    if approved:
        result = graph.invoke(Command(resume=True), config=config)
    else:
        result = graph.invoke(Command(resume=False), config=config)

    print(
        json.dumps(
            {
                "tenant_id": "nonprofit",
                "model": result["model"],
                "mission_keywords": mission_keywords,
                "top_opportunities": result.get("top_opportunities"),
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
