"""Client for the Conflicts service — drop-in replacement for the old direct
import of tenants/legal/intake_conflict_check/conflicts_db.py.

Same function name and signature (check_conflicts) so agents only need to
change their import line, not their calling code.
"""

import os

import requests

BASE_URL = os.environ.get("CONFLICTS_SERVICE_URL", "http://localhost:8002")


def check_conflicts(party_names: list[str]) -> list[dict]:
    response = requests.post(f"{BASE_URL}/check", json={"party_names": party_names}, timeout=5)
    response.raise_for_status()
    return response.json()
