"""Case-type playbooks — requirement #5 from Mr. Patrick's product-direction
meeting, turned from "flag anything that could hurt the application" into a
real per-case-type rules engine instead of one generic check for every
matter. Deliberately plain Python data and functions, no LLM involved — a
missing document or a blown deadline is a fact, not something that benefits
from a model's judgment. The LLM's job (see graph.py) is turning the facts
this file produces into a readable report for the attorney, not deciding
whether a fact is true.

These checklists and thresholds are a researched starting baseline (see the
2026-07-14 addendum to the immigration-tenant-pivot notes this was built
from, itself cross-checked against a proposed COS workflow), not settled
legal fact — an attorney should treat this as a first draft to refine, not
something to file against unreviewed.
"""

from datetime import date, datetime

PLAYBOOKS = {
    "change_of_status": {
        "required_documents": [
            "passport_copy",
            "current_visa_copy",
            "i94_record",
            "i20_for_cos",
            "sevis_fee_receipt",
            "financial_proof",
            "personal_statement",
            "academic_transcripts",
        ],
    },
    "marriage_based_green_card": {
        "required_documents": [
            "marriage_certificate",
            "passport_copy",
            "i94_record",
            "joint_financial_records",
            "affidavit_of_support",
            "passport_photos",
        ],
    },
    "asylum": {
        "required_documents": [
            "passport_copy",
            "i94_record",
            "personal_statement",
            "country_conditions_evidence",
            "identity_documents",
        ],
    },
    "h1b": {
        "required_documents": [
            "passport_copy",
            "current_visa_copy",
            "labor_condition_application",
            "employer_support_letter",
            "academic_transcripts",
            "resume",
        ],
    },
    "naturalization": {
        "required_documents": [
            "green_card_copy",
            "passport_copy",
            "tax_returns",
            "travel_history",
            "identity_documents",
        ],
    },
}

# How many days must separate a B-1/B-2 entry from filing a change-of-status
# application before USCIS is less likely to read it as preconceived intent
# to stay and study rather than a genuine visit. A rough marker, not a hard
# legal bar — the check exists to flag it for attorney judgment, not to
# reject a filing outright.
NINETY_DAY_RULE_THRESHOLD = 90


def _parse_date(value) -> date | None:
    try:
        return datetime.fromisoformat(value).date()
    except (TypeError, ValueError):
        return None


def _missing_documents(case: dict, required: list[str]) -> dict | None:
    documents = case.get("documents") or {}
    missing = [doc for doc in required if not documents.get(doc)]
    if not missing:
        return None
    return {
        "rule": "missing_documents",
        "urgency": "medium",
        "detail": f"Still missing: {', '.join(missing)}.",
    }


def _ninety_day_rule_check(case: dict) -> dict | None:
    key_dates = case.get("key_dates") or {}
    entry_date = _parse_date(key_dates.get("us_entry_date"))
    if entry_date is None:
        return None

    # No filing_date on file yet means "if we filed today" -- the check
    # should warn before the window closes, not only after a filing date is
    # already recorded.
    filing_date = _parse_date(key_dates.get("filing_date")) or date.today()
    gap_days = (filing_date - entry_date).days
    if 0 <= gap_days < NINETY_DAY_RULE_THRESHOLD:
        return {
            "rule": "ninety_day_rule",
            "urgency": "high",
            "detail": (
                f"Only {gap_days} days between U.S. entry ({entry_date.isoformat()}) and filing "
                f"({filing_date.isoformat()}) — under the {NINETY_DAY_RULE_THRESHOLD}-day guideline "
                "USCIS uses as a rough marker of preconceived intent."
            ),
        }
    return None


def _financial_sufficiency_check(case: dict) -> dict | None:
    snapshot = case.get("financial_snapshot") or {}
    funds_available = snapshot.get("funds_available")
    program_cost = snapshot.get("program_cost")
    if funds_available is None or program_cost is None:
        return None
    if funds_available < program_cost:
        shortfall = program_cost - funds_available
        return {
            "rule": "financial_sufficiency",
            "urgency": "high",
            "detail": (
                f"Documented funds (${funds_available:,.0f}) fall short of the stated program "
                f"cost (${program_cost:,.0f}) by ${shortfall:,.0f}."
            ),
        }
    return None


# Checks beyond the document checklist, keyed by case_type. Every case type
# gets the document-checklist check for free (below); this is for rules
# specific to one case type, like the 90-day rule only applying to a
# change of status.
CASE_TYPE_CHECKS = {
    "change_of_status": [_ninety_day_rule_check, _financial_sufficiency_check],
}


def run_checks(case: dict) -> list[dict]:
    """Runs every applicable check for case['case_type'] and returns the raw
    flags found — each a {"rule", "urgency", "detail"} dict. Empty list if
    the case type isn't in PLAYBOOKS yet, or if nothing is wrong. See
    graph.py for how these get a citation attached and turned into a report
    for the attorney.
    """
    case_type = case.get("case_type")
    playbook = PLAYBOOKS.get(case_type)
    if playbook is None:
        return []

    flags = []

    missing_flag = _missing_documents(case, playbook["required_documents"])
    if missing_flag is not None:
        flags.append(missing_flag)

    for check in CASE_TYPE_CHECKS.get(case_type, []):
        result = check(case)
        if result is not None:
            flags.append(result)

    return flags
