import argparse
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from case_service.client import list_cases
from graph import graph


def _run_one(tenant_id: str, case_id: str) -> None:
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"tenant_id": tenant_id, "case_id": case_id}, config=config)

    print(f"\n--- case {case_id} ---")
    print(f"Flags: {len(result.get('flags', []))}")
    print(result["output"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True, help="Tenant id, e.g. hawthorn-pell")
    parser.add_argument("--case-id", help="Check a single case instead of the whole roster")
    args = parser.parse_args()

    if args.case_id:
        _run_one(args.tenant, args.case_id)
        return

    cases = list_cases(args.tenant)
    if not cases:
        print(f"No cases on file for tenant '{args.tenant}'.")
        return
    for case in cases:
        _run_one(args.tenant, case["id"])


if __name__ == "__main__":
    main()
