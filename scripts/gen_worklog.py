#!/usr/bin/env python3
"""Regenerate WORKLOG.md from git commit history.

Reads every commit matching "LA {hours}h {date}: {desc}" and rebuilds
WORKLOG.md grouped by day with daily and running totals. Run this after
committing new work:

    python scripts/gen_worklog.py
"""
import re
import subprocess
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r"^LA (\d+(?:\.\d+)?)h (\d{4}-\d{2}-\d{2}): (.+)$")


def load_entries():
    log = subprocess.run(
        ["git", "log", "--format=%s", "--reverse"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()

    entries = []
    for line in log:
        match = PATTERN.match(line.strip())
        if match:
            hours, date, desc = match.groups()
            entries.append((date, float(hours), desc))
    return entries


def render(entries):
    by_date = defaultdict(list)
    for date, hours, desc in entries:
        by_date[date].append((hours, desc))

    total = sum(hours for _, hours, _ in entries)
    lines = [
        "# NewFire Worklog",
        "",
        f"Total hours logged: **{total:g}h** across {len(by_date)} days.",
        "",
        "| Date | Hours | Description |",
        "|---|---|---|",
    ]
    for date in sorted(by_date):
        day_entries = by_date[date]
        day_total = sum(h for h, _ in day_entries)
        for i, (hours, desc) in enumerate(day_entries):
            date_cell = date if i == 0 else ""
            lines.append(f"| {date_cell} | {hours:g}h | {desc} |")
        lines.append(f"| | **{day_total:g}h** | *day total* |")

    lines.append("")
    return "\n".join(lines)


def main():
    entries = load_entries()
    output = render(entries)
    (REPO_ROOT / "WORKLOG.md").write_text(output, encoding="utf-8")
    print(f"wrote WORKLOG.md — {len(entries)} entries")


if __name__ == "__main__":
    main()
