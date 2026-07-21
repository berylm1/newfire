"""Parses the Final Action Dates tables out of a real Visa Bulletin PDF
(travel.state.gov's monthly publication) into a plain dict. Pure parsing —
no network calls here; see main.py for fetching the PDF and caching the
result.

Why the PDF and not the HTML page: the HTML page is behind a Cloudflare
bot-check that a plain `requests` call can't pass (no JS execution — a real
browser is the only thing that gets through it). The PDF asset path
(`/content/dam/visas/Bulletins/...`) is served unprotected — confirmed by a
direct `requests.get()`, no scraping workaround or headless browser
involved. Prefer this over "Dates for Filing" — Final Action Dates are what
actually determines when a green card can be issued; Dates for Filing is
only sometimes usable, at USCIS's monthly discretion.

Text layout, not a real HTML/PDF table structure — PyMuPDF extracts each
page's text in reading order, so a table's cells come out as a flat
sequence of lines: category label, then its five country values, repeated.
The family-sponsored table's labels are always one line each (F1, F2A, ...)
so they can be matched by exact text. The employment-based table's labels
wrap across multiple lines (e.g. "5th Unreserved (including C5, T5, I5, R5,
NU, RU)"), so those are parsed by accumulating lines until five
consecutive value-shaped tokens appear — whatever came before those five
lines is the label, however many lines it took.
"""

import re
from datetime import date, datetime
from io import BytesIO

import fitz

FAMILY_CATEGORIES = ["F1", "F2A", "F2B", "F3", "F4"]
COUNTRIES = ["All Chargeability Areas Except Those Listed", "CHINA-mainland born", "INDIA", "MEXICO", "PHILIPPINES"]

VALUE_RE = re.compile(r"^(?:\d{2}[A-Z]{3}\d{2}|C|U)$")

# Repeats on every PDF page (department header, page number, "<Month>
# <year>" footer) -- a table spanning a page break otherwise leaks this
# text into whatever label or row happens to be accumulating at that
# point.
_PAGE_BOILERPLATE_RE = re.compile(r"^(U\.S\. DEPARTMENT of\s+STATE|\d{1,2}|[A-Za-z]+ \d{4})$")

EB_LABEL_TO_CODE = [
    (re.compile(r"^1st\b"), "EB-1"),
    (re.compile(r"^2nd\b"), "EB-2"),
    (re.compile(r"^3rd\b"), "EB-3"),
    (re.compile(r"^Other Workers\b", re.IGNORECASE), "EB-3-other-workers"),
    (re.compile(r"^4th\b"), "EB-4"),
    (re.compile(r"^Certain Religious Workers\b", re.IGNORECASE), "EB-4-religious-workers"),
    (re.compile(r"^5th Unreserved\b", re.IGNORECASE), "EB-5-unreserved"),
    (re.compile(r"^5th Set Aside:\s*Rural\b", re.IGNORECASE), "EB-5-rural"),
    (re.compile(r"^5th Set Aside:\s*High Unemployment\b", re.IGNORECASE), "EB-5-high-unemployment"),
    (re.compile(r"^5th Set Aside:\s*Infrastructure\b", re.IGNORECASE), "EB-5-infrastructure"),
]

FAMILY_SECTION_START = "A. Final Action Dates for Family-Sponsored Preference Class"
FAMILY_SECTION_END = "B. Dates for Filing Family-Sponsored Visa Applications"
EMPLOYMENT_SECTION_START = "A. Final Action Dates for Employment-Based Preference Cases"
EMPLOYMENT_SECTION_END = "B. Dates for Filing of Employment-Based Visa Applications"


class BulletinParseError(ValueError):
    pass


def _strip_page_boilerplate(lines: list[str]) -> list[str]:
    return [ln for ln in lines if not _PAGE_BOILERPLATE_RE.match(ln)]


def _section(text: str, start_marker: str, end_marker: str) -> str:
    try:
        start = text.index(start_marker) + len(start_marker)
        end = text.index(end_marker, start)
    except ValueError as exc:
        raise BulletinParseError(f"expected section markers not found: {start_marker!r} / {end_marker!r}") from exc
    return text[start:end]


def _parse_value(token: str) -> str:
    if token in ("C", "U"):
        return token
    parsed = datetime.strptime(token, "%d%b%y").date()
    # A category like F2A can legitimately list a cutoff within a day or
    # two of today, so this can't require "strictly in the past" -- it's
    # only here to catch a wild 2-digit-year misparse (Python's %y pivot
    # maps 00-68 to 2000-2068, 69-99 to 1969-1999; a real cutoff should
    # never land far outside that plausible window).
    if parsed > date.today().replace(year=date.today().year + 2):
        raise BulletinParseError(f"parsed date {parsed} for token {token!r} is implausibly far in the future")
    return parsed.isoformat()


def _parse_fixed_label_table(section_text: str, categories: list[str]) -> dict:
    lines = _strip_page_boilerplate([ln.strip() for ln in section_text.splitlines() if ln.strip()])
    result = {}
    i = 0
    for category in categories:
        while i < len(lines) and lines[i] != category:
            i += 1
        if i >= len(lines):
            raise BulletinParseError(f"could not find category {category!r} in table")
        i += 1
        values = lines[i : i + len(COUNTRIES)]
        i += len(COUNTRIES)
        if len(values) < len(COUNTRIES):
            raise BulletinParseError(f"ran out of lines reading values for category {category!r}")
        result[category] = {country: _parse_value(v) for country, v in zip(COUNTRIES, values)}
    return result


def _parse_variable_label_table(section_text: str) -> dict:
    # "PHILIPPINES" is the last, unique column header -- everything before
    # it is the descriptive paragraph and column headers, not row data.
    header_end = section_text.rindex("PHILIPPINES") + len("PHILIPPINES")
    lines = _strip_page_boilerplate([ln.strip() for ln in section_text[header_end:].splitlines() if ln.strip()])

    result = {}
    label_parts: list[str] = []
    i = 0
    while i < len(lines):
        window = lines[i : i + len(COUNTRIES)]
        if len(window) == len(COUNTRIES) and all(VALUE_RE.match(v) for v in window):
            label = " ".join(label_parts).strip()
            if label:
                result[label] = {country: _parse_value(v) for country, v in zip(COUNTRIES, window)}
            label_parts = []
            i += len(COUNTRIES)
        else:
            label_parts.append(lines[i])
            i += 1
    return result


def _normalize_eb_label(raw_label: str) -> str:
    for pattern, code in EB_LABEL_TO_CODE:
        if pattern.match(raw_label):
            return code
    raise BulletinParseError(f"unrecognized employment-based category label: {raw_label!r}")


def parse_bulletin(pdf_bytes: bytes) -> dict:
    """Returns {"bulletin_month": "August 2026", "family_sponsored": {...},
    "employment_based": {...}} — each leaf value is either an ISO date
    string (the Final Action cutoff) or the literal "C" (current, no wait)
    or "U" (unavailable, no visas issued in that category/country this
    month)."""
    doc = fitz.open(stream=BytesIO(pdf_bytes), filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)

    month_match = re.search(r"Visa Bulletin\s*\n?\s*Number \d+, Volume [IVXLC]+\s*\|.*?\n\s*([A-Za-z]+ \d{4})", text)
    bulletin_month = month_match.group(1) if month_match else None

    family_section = _section(text, FAMILY_SECTION_START, FAMILY_SECTION_END)
    family_dates = _parse_fixed_label_table(family_section, FAMILY_CATEGORIES)

    eb_section = _section(text, EMPLOYMENT_SECTION_START, EMPLOYMENT_SECTION_END)
    eb_raw = _parse_variable_label_table(eb_section)
    employment_dates = {_normalize_eb_label(label): values for label, values in eb_raw.items()}

    return {
        "bulletin_month": bulletin_month,
        "family_sponsored": family_dates,
        "employment_based": employment_dates,
    }
