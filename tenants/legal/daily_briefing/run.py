import json
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from graph import graph


def main() -> None:
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke({"tenant_id": "legal"}, config=config)

    print("--- Morning briefing ---\n")
    print(result["output"])

    print(
        "\n"
        + json.dumps(
            {
                "tenant_id": "legal",
                "model": result["model"],
                "docket_items": len(result.get("docket", [])),
                "latency_ms": result["latency_ms"],
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
                "notify_id": result.get("notify_id"),
            }
        )
    )


if __name__ == "__main__":
    main()
