import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import playbooks


def _case(case_type="change_of_status", **fields):
    return {"client_name": "Test Client", "case_type": case_type, **fields}


def test_unknown_case_type_produces_no_flags():
    assert playbooks.run_checks(_case(case_type="unheard_of_matter")) == []


def test_missing_case_type_produces_no_flags():
    assert playbooks.run_checks({"client_name": "A"}) == []


def test_flags_missing_documents_for_known_case_type():
    case = _case(documents={"passport_copy": True})

    flags = playbooks.run_checks(case)

    missing_flags = [f for f in flags if f["rule"] == "missing_documents"]
    assert len(missing_flags) == 1
    assert "current_visa_copy" in missing_flags[0]["detail"]
    assert "passport_copy" not in missing_flags[0]["detail"]
    assert missing_flags[0]["urgency"] == "medium"


def test_no_missing_documents_flag_when_all_required_docs_present():
    all_docs = {doc: True for doc in playbooks.PLAYBOOKS["h1b"]["required_documents"]}
    case = _case(case_type="h1b", documents=all_docs)

    flags = playbooks.run_checks(case)

    assert not any(f["rule"] == "missing_documents" for f in flags)


def test_document_marked_false_still_counts_as_missing():
    all_docs = {doc: True for doc in playbooks.PLAYBOOKS["asylum"]["required_documents"]}
    all_docs["personal_statement"] = False
    case = _case(case_type="asylum", documents=all_docs)

    flags = playbooks.run_checks(case)

    missing_flag = next(f for f in flags if f["rule"] == "missing_documents")
    assert "personal_statement" in missing_flag["detail"]


def test_ninety_day_rule_flags_filing_inside_window():
    entry = date.today() - timedelta(days=30)
    case = _case(key_dates={"us_entry_date": entry.isoformat()})

    flags = playbooks.run_checks(case)

    ninety_day = next(f for f in flags if f["rule"] == "ninety_day_rule")
    assert ninety_day["urgency"] == "high"
    assert "30 days" in ninety_day["detail"]


def test_ninety_day_rule_does_not_flag_filing_outside_window():
    entry = date.today() - timedelta(days=120)
    case = _case(key_dates={"us_entry_date": entry.isoformat()})

    flags = playbooks.run_checks(case)

    assert not any(f["rule"] == "ninety_day_rule" for f in flags)


def test_ninety_day_rule_uses_explicit_filing_date_when_present():
    entry = date.today() - timedelta(days=200)
    filing = entry + timedelta(days=10)  # filed 10 days after entry, well inside the window
    case = _case(key_dates={"us_entry_date": entry.isoformat(), "filing_date": filing.isoformat()})

    flags = playbooks.run_checks(case)

    assert any(f["rule"] == "ninety_day_rule" for f in flags)


def test_ninety_day_rule_skipped_without_entry_date():
    case = _case(key_dates={})

    flags = playbooks.run_checks(case)

    assert not any(f["rule"] == "ninety_day_rule" for f in flags)


def test_ninety_day_rule_not_applicable_to_other_case_types():
    entry = date.today() - timedelta(days=5)
    case = _case(case_type="asylum", key_dates={"us_entry_date": entry.isoformat()})

    flags = playbooks.run_checks(case)

    assert not any(f["rule"] == "ninety_day_rule" for f in flags)


def test_financial_sufficiency_flags_shortfall():
    case = _case(financial_snapshot={"funds_available": 8000, "program_cost": 12000})

    flags = playbooks.run_checks(case)

    financial = next(f for f in flags if f["rule"] == "financial_sufficiency")
    assert financial["urgency"] == "high"
    assert "$4,000" in financial["detail"]


def test_financial_sufficiency_not_flagged_when_funds_cover_cost():
    case = _case(financial_snapshot={"funds_available": 15000, "program_cost": 12000})

    flags = playbooks.run_checks(case)

    assert not any(f["rule"] == "financial_sufficiency" for f in flags)


def test_financial_sufficiency_skipped_when_snapshot_incomplete():
    case = _case(financial_snapshot={"funds_available": 8000})

    flags = playbooks.run_checks(case)

    assert not any(f["rule"] == "financial_sufficiency" for f in flags)


def test_financial_sufficiency_not_applicable_to_other_case_types():
    case = _case(case_type="naturalization", financial_snapshot={"funds_available": 0, "program_cost": 12000})

    flags = playbooks.run_checks(case)

    assert not any(f["rule"] == "financial_sufficiency" for f in flags)
