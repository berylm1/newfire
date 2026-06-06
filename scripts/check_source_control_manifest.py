#!/usr/bin/env python3
"""Validate the NewFire source-control manifest.

Default behavior is strict because this script is intended as an agent preflight:
load-bearing production services must be GitHub-governed before implementation.
Use --report-only when generating a CEO status report that should list blockers
without failing the shell command.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ALLOWED_STATUSES = {
    "github_tracked",
    "vendored_baseline_approved",
    "blocked_untracked",
    "deferred_scaffold",
}
GOVERNED_STATUSES = {"github_tracked", "vendored_baseline_approved"}
REQUIRED_FIELDS = {
    "id",
    "name",
    "owner",
    "risk_level",
    "load_bearing",
    "production_surface",
    "governance_status",
    "local_source_path",
}


def load_manifest(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"manifest not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit("manifest root must be an object")
    if not isinstance(data.get("services"), list):
        raise SystemExit("manifest must contain a services array")
    return data


def validate(data: dict, repo_root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    blockers: list[str] = []
    seen_ids: set[str] = set()

    for idx, service in enumerate(data["services"], start=1):
        label = service.get("id") or f"service[{idx}]"
        missing = sorted(REQUIRED_FIELDS - set(service))
        if missing:
            errors.append(f"{label}: missing required fields: {', '.join(missing)}")
            continue

        if label in seen_ids:
            errors.append(f"{label}: duplicate service id")
        seen_ids.add(label)

        status = service["governance_status"]
        if status not in ALLOWED_STATUSES:
            errors.append(f"{label}: invalid governance_status={status!r}")
            continue

        load_bearing = bool(service["load_bearing"])
        production = bool(service["production_surface"])
        governed = status in GOVERNED_STATUSES

        if governed:
            github_repo = service.get("github_repo")
            if not github_repo:
                errors.append(f"{label}: governed service must name github_repo")
            repo_relative_path = service.get("repo_relative_path")
            if repo_relative_path:
                rel = Path(repo_relative_path)
                if rel.is_absolute() or ".." in rel.parts:
                    errors.append(f"{label}: repo_relative_path must stay inside repo")
                elif not (repo_root / rel).exists():
                    errors.append(f"{label}: repo_relative_path does not exist: {repo_relative_path}")

        if load_bearing and production and not governed:
            blockers.append(
                f"{label}: production/load-bearing service is not GitHub-governed "
                f"(status={status}, source={service.get('local_source_path')})"
            )

        if not production and status == "github_tracked" and not service.get("repo_relative_path"):
            errors.append(f"{label}: github_tracked scaffold must name repo_relative_path if promoted")

    return errors, blockers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default="docs/ceo-agent/source-control-manifest.json",
        help="Path to source-control manifest JSON",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Print blockers but exit 0 if the manifest schema is valid",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path

    data = load_manifest(manifest_path)
    errors, blockers = validate(data, repo_root)

    print(f"manifest: {manifest_path.relative_to(repo_root)}")
    print(f"services: {len(data['services'])}")
    governed = [s for s in data["services"] if s.get("governance_status") in GOVERNED_STATUSES]
    print(f"governed: {len(governed)}")
    print(f"blockers: {len(blockers)}")

    if errors:
        print("\nSchema/path errors:")
        for err in errors:
            print(f"- {err}")

    if blockers:
        print("\nSource-control blockers:")
        for blocker in blockers:
            print(f"- {blocker}")

    if errors:
        return 1
    if blockers and not args.report_only:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
