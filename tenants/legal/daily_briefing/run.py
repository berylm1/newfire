import json
import uuid

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
            }
        )
    )


if __name__ == "__main__":
    main()
