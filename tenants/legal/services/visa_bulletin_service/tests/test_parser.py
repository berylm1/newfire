"""Tests the parser against a real Visa Bulletin PDF (August 2026,
committed as a fixture — the actual government publication, not synthetic
data), cross-checked against the live travel.state.gov HTML page at the
time this was written. Same "no synthetic stand-in" principle as
citation_checker's real CourtListener calls.
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from visa_bulletin_service import parser

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "visabulletin_august2026.pdf")


@pytest.fixture(scope="module")
def parsed():
    with open(FIXTURE_PATH, "rb") as f:
        return parser.parse_bulletin(f.read())


def test_bulletin_month_extracted(parsed):
    assert parsed["bulletin_month"] == "August 2026"


def test_all_five_family_sponsored_categories_present(parsed):
    assert set(parsed["family_sponsored"].keys()) == {"F1", "F2A", "F2B", "F3", "F4"}


def test_family_sponsored_values_match_known_bulletin_data(parsed):
    # Cross-checked against the live HTML page for August 2026.
    assert parsed["family_sponsored"]["F1"]["MEXICO"] == "2007-12-01"
    assert parsed["family_sponsored"]["F1"]["PHILIPPINES"] == "2013-05-01"
    assert parsed["family_sponsored"]["F4"]["MEXICO"] == "2001-04-08"


def test_family_sponsored_near_current_date_not_treated_as_misparse(parsed):
    # F2A was genuinely close to fully current this month -- a real value,
    # not a 2-digit-year parsing bug.
    assert parsed["family_sponsored"]["F2A"]["All Chargeability Areas Except Those Listed"] == "2026-07-22"


def test_all_ten_employment_based_categories_present(parsed):
    assert set(parsed["employment_based"].keys()) == {
        "EB-1",
        "EB-2",
        "EB-3",
        "EB-3-other-workers",
        "EB-4",
        "EB-4-religious-workers",
        "EB-5-unreserved",
        "EB-5-rural",
        "EB-5-high-unemployment",
        "EB-5-infrastructure",
    }


def test_employment_based_current_and_unavailable_markers_preserved(parsed):
    assert parsed["employment_based"]["EB-1"]["All Chargeability Areas Except Those Listed"] == "C"
    assert parsed["employment_based"]["EB-2"]["INDIA"] == "U"


def test_employment_based_values_match_known_bulletin_data(parsed):
    assert parsed["employment_based"]["EB-1"]["CHINA-mainland born"] == "2023-07-01"
    assert parsed["employment_based"]["EB-3"]["INDIA"] == "2014-01-01"


def test_multiline_employment_labels_normalized_correctly(parsed):
    # These four categories' raw PDF labels wrap across 2-4 lines each
    # ("5th Set Aside: Rural (20%) (including NR, RR)", etc.) -- confirms
    # the variable-label tokenizer isn't just getting lucky on single-line
    # labels.
    for code in ("EB-5-unreserved", "EB-5-rural", "EB-5-high-unemployment", "EB-5-infrastructure"):
        assert code in parsed["employment_based"]


def test_parse_value_rejects_implausible_future_date():
    # %y pivot maps "50" -> 2050, well past today's +2-year sanity window --
    # exercises the misparse guard directly rather than waiting for a real
    # bulletin to someday produce one.
    with pytest.raises(parser.BulletinParseError):
        parser._parse_value("01DEC50")


def test_parse_value_allows_date_within_two_years_of_today():
    # Confirms the guard's boundary isn't accidentally rejecting legitimate
    # near-term cutoffs (like F2A's) -- only implausibly-distant ones.
    near_term = date.today() + timedelta(days=400)
    token = near_term.strftime("%d%b%y").upper()
    assert parser._parse_value(token) == near_term.isoformat()


def test_section_missing_marker_raises_clear_error():
    with pytest.raises(parser.BulletinParseError):
        parser._section("no markers in here", "START MARKER", "END MARKER")
