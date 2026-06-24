"""CourtListener case-law search client.

Real public API: https://www.courtlistener.com/api/rest/v4/search/
Anonymous requests work (rate-limited); set COURTLISTENER_API_TOKEN for
higher limits if a firm has an account.
"""

import os
import urllib.request
import urllib.parse
import json

SEARCH_URL = "https://www.courtlistener.com/api/rest/v4/search/"


def verify_citation(case_name_or_citation: str) -> dict:
    """Look up a case by name or citation. Returns a verification result, not
    raw API output, so the graph doesn't need to know the API shape."""
    query = urllib.parse.urlencode({"q": case_name_or_citation, "type": "o"})
    req = urllib.request.Request(f"{SEARCH_URL}?{query}")

    token = os.environ.get("COURTLISTENER_API_TOKEN")
    if token:
        req.add_header("Authorization", f"Token {token}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {
            "query": case_name_or_citation,
            "verified": False,
            "error": f"lookup failed: {exc}",
        }

    results = body.get("results", [])
    if not results:
        return {
            "query": case_name_or_citation,
            "verified": False,
            "match_count": 0,
        }

    top = results[0]
    return {
        "query": case_name_or_citation,
        "verified": True,
        "match_count": body.get("count", len(results)),
        "matched_case_name": top.get("caseName"),
        "citations": top.get("citation", []),
        "court": top.get("court"),
        "date_filed": top.get("dateFiled"),
        "status": top.get("status"),
    }
