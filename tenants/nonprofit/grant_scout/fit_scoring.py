"""Fit-scoring rubric for grant opportunities.

Score = how many of the org's mission keywords matched, weighted by deadline
urgency. Pure scoring logic, no LLM involved — keeps the ranking deterministic
and auditable.
"""

from datetime import datetime, timezone


def _urgency_score(close_date: str) -> float:
    """Higher score for sooner deadlines. No close date (forecasted) gets a low,
    non-zero default so forecasted opportunities still surface, just not urgently."""
    if not close_date:
        return 0.2
    try:
        deadline = datetime.strptime(close_date, "%m/%d/%Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.2
    days_out = (deadline - datetime.now(timezone.utc)).days
    if days_out < 0:
        return 0.0  # already closed
    if days_out <= 14:
        return 1.0
    if days_out <= 30:
        return 0.7
    if days_out <= 60:
        return 0.4
    return 0.2


def score_opportunities(hits_by_keyword: dict[str, list[dict]]) -> list[dict]:
    """Merge opportunities found across mission keywords, dedupe by id, and score.

    hits_by_keyword: {mission_keyword: [opportunity dicts from grants_gov]}
    """
    merged: dict[str, dict] = {}
    for keyword, hits in hits_by_keyword.items():
        for hit in hits:
            opp_id = hit["id"]
            if opp_id not in merged:
                merged[opp_id] = {**hit, "matched_keywords": []}
            merged[opp_id]["matched_keywords"].append(keyword)

    scored = []
    for opp in merged.values():
        keyword_score = len(opp["matched_keywords"])
        urgency = _urgency_score(opp.get("closeDate", ""))
        opp["fit_score"] = round(keyword_score + urgency, 2)
        scored.append(opp)

    return sorted(scored, key=lambda o: o["fit_score"], reverse=True)
