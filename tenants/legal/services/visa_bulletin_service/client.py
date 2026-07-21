"""Client for the Visa Bulletin service — thin HTTP wrapper so agents don't
need to know this is a service call instead of a local function.
"""

import os

import requests

BASE_URL = os.environ.get("VISA_BULLETIN_SERVICE_URL", "http://localhost:8010")


def get_current_bulletin() -> dict:
    response = requests.get(f"{BASE_URL}/bulletin/current", timeout=20)
    response.raise_for_status()
    return response.json()


def check_priority_date(category: str, priority_date: str, country: str | None = None) -> dict:
    response = requests.post(
        f"{BASE_URL}/check",
        json={"category": category, "country": country, "priority_date": priority_date},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
