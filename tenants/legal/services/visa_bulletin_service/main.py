"""Visa Bulletin service — requirement #10 from Mr. Patrick's product-
direction meeting: track a client's priority date against the State
Department's monthly Visa Bulletin and flag when it becomes current.
Nothing else in this tenant tracks this; it's a real, distinct
immigration-specific pain point (see the research addendum in the
immigration-tenant-pivot notes).

Fetches and caches the real bulletin PDF from travel.state.gov (see
parser.py's docstring for why the PDF, not the HTML page) — no synthetic
stand-in, same principle as citation_checker's real CourtListener calls.
The bulletin only changes once a month, so this only re-fetches when the
cache isn't already for a plausible current month; a live-fetch failure
falls back to whatever's cached rather than hard-failing.
"""

import calendar
import json
import os
from datetime import date

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from visa_bulletin_service.parser import parse_bulletin

PDF_URL_TEMPLATE = "https://travel.state.gov/content/dam/visas/Bulletins/visabulletin_{month_name}{year}.pdf"
CACHE_PATH = os.path.join(os.path.dirname(__file__), "bulletin_cache.json")

COUNTRY_ALIASES = {
    "china": "CHINA-mainland born",
    "india": "INDIA",
    "mexico": "MEXICO",
    "philippines": "PHILIPPINES",
}
DEFAULT_COUNTRY_COLUMN = "All Chargeability Areas Except Those Listed"

app = FastAPI(title="Visa Bulletin Service")


class PriorityDateCheck(BaseModel):
    category: str
    country: str | None = None
    priority_date: str


def _candidate_months(today: date) -> list[tuple[str, int]]:
    # Next month first: by the second half of a given month, State
    # Department has usually already published next month's bulletin,
    # which is the one that matters for forward planning. Falls through to
    # the current month (always published by definition) and then the
    # previous month as a last-resort fallback.
    candidates = []
    for offset in (1, 0, -1):
        total = today.month - 1 + offset
        year = today.year + total // 12
        month = total % 12 + 1
        candidates.append((calendar.month_name[month], year))
    return candidates


def _load_cache() -> dict | None:
    if not os.path.exists(CACHE_PATH):
        return None
    with open(CACHE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_cache(data: dict) -> None:
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _fetch_and_parse(month_name: str, year: int) -> dict | None:
    url = PDF_URL_TEMPLATE.format(month_name=month_name, year=year)
    try:
        response = requests.get(url, timeout=15)
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    return parse_bulletin(response.content)


def get_current_bulletin() -> dict:
    candidates = _candidate_months(date.today())
    candidate_labels = {f"{name} {year}" for name, year in candidates}

    cached = _load_cache()
    if cached and cached.get("bulletin_month") in candidate_labels:
        return cached

    for month_name, year in candidates:
        parsed = _fetch_and_parse(month_name, year)
        if parsed is not None:
            _save_cache(parsed)
            return parsed

    if cached is not None:
        # Nothing current could be fetched live -- better to serve a
        # known-stale bulletin (flagged as such) than to fail outright,
        # since most categories don't move every month anyway.
        return {**cached, "stale": True}

    raise HTTPException(
        status_code=503,
        detail="Visa Bulletin unavailable: no live fetch succeeded and nothing cached yet",
    )


def _normalize_country(country: str | None) -> str:
    if not country:
        return DEFAULT_COUNTRY_COLUMN
    return COUNTRY_ALIASES.get(country.strip().lower(), DEFAULT_COUNTRY_COLUMN)


def _is_current(cutoff: str, priority_date: str) -> bool:
    if cutoff == "C":
        return True
    if cutoff == "U":
        return False
    return date.fromisoformat(priority_date) <= date.fromisoformat(cutoff)


@app.get("/bulletin/current")
def bulletin_current() -> dict:
    return get_current_bulletin()


@app.post("/check")
def check_priority_date(check: PriorityDateCheck) -> dict:
    bulletin = get_current_bulletin()
    country = _normalize_country(check.country)

    if check.category in bulletin["family_sponsored"]:
        table = bulletin["family_sponsored"]
    elif check.category in bulletin["employment_based"]:
        table = bulletin["employment_based"]
    else:
        raise HTTPException(status_code=422, detail=f"unknown visa category: {check.category}")

    cutoff = table[check.category][country]
    return {
        "current": _is_current(cutoff, check.priority_date),
        "cutoff": cutoff,
        "category": check.category,
        "country": country,
        "bulletin_month": bulletin.get("bulletin_month"),
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
