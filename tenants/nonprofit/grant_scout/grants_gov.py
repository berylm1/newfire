"""Grants.gov search client.

Real public API, no key required: https://api.grants.gov/v1/api/search2
"""

import urllib.request
import json

SEARCH_URL = "https://api.grants.gov/v1/api/search2"


def search_opportunities(keyword: str, rows: int = 10) -> list[dict]:
    """Search Grants.gov for open opportunities matching a keyword."""
    payload = json.dumps({"keyword": keyword, "rows": rows}).encode("utf-8")
    req = urllib.request.Request(
        SEARCH_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("data", {}).get("oppHits", [])
