"""Conflicts-of-interest lookup.

This is a swappable interface, not a real conflicts database. Any small-to-mid
firm plugs in their own backend (SQL table, CRM export, whatever) by
implementing `check_conflicts` the same way: take a list of party names, return
a list of matches against existing/former clients or adverse parties.

The synthetic data below exists only so the workflow is testable end-to-end
without real client data.
"""

SYNTHETIC_CONFLICTS_DB = [
    {"name": "Marcus Whitfield", "role": "former_client", "matter": "Whitfield Properties LLC formation"},
    {"name": "Greenline Logistics", "role": "current_client", "matter": "Ongoing commercial lease dispute"},
    {"name": "Dana Okafor", "role": "adverse_party", "matter": "Okafor v. Whitfield Properties LLC"},
]


def check_conflicts(party_names: list[str]) -> list[dict]:
    """Return conflicts-DB entries matching any of the given party names (case-insensitive substring match)."""
    matches = []
    for name in party_names:
        name_lower = name.strip().lower()
        if not name_lower:
            continue
        for entry in SYNTHETIC_CONFLICTS_DB:
            if name_lower in entry["name"].lower() or entry["name"].lower() in name_lower:
                matches.append({"queried_name": name, **entry})
    return matches
