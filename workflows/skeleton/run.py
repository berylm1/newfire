import argparse
import json
import uuid

from langgraph.types import Command

from graph import graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke(
        {"tenant_id": args.tenant, "prompt": args.prompt},
        config=config,
    )
    draft = result["draft"]
    print(draft)
    approved = input("Approve draft? [y/N]: ").strip().lower() == "y"

    if approved:
        result = graph.invoke(Command(resume=True), config=config)

    print(
        json.dumps(
            {
                "tenant_id": args.tenant,
                "model": result["model"],
                "prompt": args.prompt,
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
