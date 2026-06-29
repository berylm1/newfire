"""Conflicts service — owns the conflicts-of-interest lookup for the legal tenant.

Pulled out of tenants/legal/intake_conflict_check/conflicts_db.py. Same
swappable-backend idea as before (a real firm plugs in their own database
behind this endpoint), now reachable over HTTP so intake, the WhatsApp
handler, and anything else that needs a conflict check don't need to import
this module directly or share its filesystem layout.
"""

from fastapi import FastAPI
from pydantic import BaseModel

SYNTHETIC_CONFLICTS_DB = [
    {"name": "Marcus Whitfield", "role": "former_client", "matter": "Whitfield Properties LLC formation"},
    {"name": "Greenline Logistics", "role": "current_client", "matter": "Ongoing commercial lease dispute"},
    {"name": "Dana Okafor", "role": "adverse_party", "matter": "Okafor v. Whitfield Properties LLC"},
]

app = FastAPI(title="Conflicts Service")


class CheckRequest(BaseModel):
    party_names: list[str]


@app.post("/check")
def check_conflicts(request: CheckRequest) -> list[dict]:
    matches = []
    for name in request.party_names:
        name_lower = name.strip().lower()
        if not name_lower:
            continue
        for entry in SYNTHETIC_CONFLICTS_DB:
            if name_lower in entry["name"].lower() or entry["name"].lower() in name_lower:
                matches.append({"queried_name": name, **entry})
    return matches


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
