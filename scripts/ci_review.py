#!/usr/bin/env python3
"""Local code review helper. Diffs the current branch against origin/main
and asks the homelab's own model for a second pair of eyes before you push.

Usage:
    python scripts/ci_review.py
"""
import json
import subprocess
import sys
import urllib.request

OLLAMA_URL = "http://100.88.112.5:11434/api/chat"
MODEL = "qwen3-coder-30b-32k:latest"

PROMPT_TEMPLATE = """Review this git diff for bugs, security issues, and anything that looks unfinished. Be specific and point to the actual lines. Keep it short if there's nothing wrong.

{diff}
"""


def get_diff():
    subprocess.run(["git", "fetch", "origin", "main"], check=True)
    result = subprocess.run(
        ["git", "diff", "origin/main...HEAD"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def review(diff):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(diff=diff)}],
        "stream": False,
        "options": {"num_ctx": 8192},
        "keep_alive": 0,
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())
    return body["message"]["content"]


def main():
    diff = get_diff()
    if not diff.strip():
        print("no diff against origin/main, nothing to review")
        return

    try:
        print(review(diff))
    except Exception as e:
        print(f"couldn't reach the review model ({e}) — is the DGX up and on the tailnet?", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
