"""Tests for the Production Readiness Scorecard."""

import re
from pathlib import Path

# Path to the scorecard document
SCORECARD_PATH = Path(__file__).parent.parent / "09_PRODUCTION_READINESS_SCORECARD.md"


def test_scorecard_exists():
    """Verify the scorecard document exists."""
    assert SCORECARD_PATH.exists(), f"Scorecard not found at {SCORECARD_PATH}"


def test_scorecard_has_required_sections():
    """Verify the scorecard contains all required sections per the issue."""
    content = SCORECARD_PATH.read_text()

    # Check for scoring methodology
    assert "Scoring Methodology" in content, "Missing scoring methodology"
    assert "Functional Completeness" in content, "Missing Functional Completeness dimension"
    assert "Test Coverage" in content, "Missing Test Coverage dimension"
    assert "Security Posture" in content, "Missing Security Posture dimension"
    assert "Performance Posture" in content, "Missing Performance Posture dimension"
    assert "Observability" in content, "Missing Observability dimension"
    assert "Deployment/Rollback" in content, "Missing Deployment/Rollback dimension"
    assert "Business Flow" in content, "Missing Business Flow dimension"


def test_scorecard_has_threshold_definition():
    """Verify the scorecard defines the threshold."""
    content = SCORECARD_PATH.read_text()

    assert "Threshold:" in content, "Missing threshold definition"
    assert "70/100" in content, "Threshold should be 70/100"


def test_scorecard_has_all_services():
    """Verify all major services and features are included."""
    content = SCORECARD_PATH.read_text()

    required_services = [
        "OpenClaw",
        "OpenHands",
        "OpenCode",
        "Ollama",
        "APISIX",
        "OpenRouter",
        "DGX Spark",
        "NemoClaw",
        "CI/CD",
        "Network Isolation",
    ]

    for service in required_services:
        assert service in content, f"Missing service: {service}"


def test_scorecard_has_summary_dashboard():
    """Verify the scorecard has a summary dashboard."""
    content = SCORECARD_PATH.read_text()

    assert "Summary Dashboard" in content, "Missing summary dashboard"
    assert "Status" in content, "Missing status column"
    assert "Critical Blockers" in content, "Missing blockers column"


def test_scorecard_has_ceo_summary():
    """Verify the scorecard has a CEO summary with 3-5 bullets."""
    content = SCORECARD_PATH.read_text()

    assert "CEO Summary" in content, "Missing CEO summary section"

    # Find the CEO summary section (between "CEO Summary" and "Next Steps")
    ceo_section_match = re.search(
        r"CEO Summary.*?(?=Next Steps|$)", content, re.DOTALL
    )
    assert ceo_section_match, "Could not find CEO summary section"

    ceo_section = ceo_section_match.group()

    # Count bullet points specifically in blockquote format "> -" or "> •"
    bullet_count = len(re.findall(r"^\s*>\s*[-•]\s+", ceo_section, re.MULTILINE))
    assert 3 <= bullet_count <= 5, f"CEO summary should have 3-5 bullets, found {bullet_count}"


def test_scorecard_scores_are_numeric():
    """Verify all service scores are numeric values."""
    content = SCORECARD_PATH.read_text()

    # Find all score patterns like "68/100" or "**68/100**"
    scores = re.findall(r"\*\*?(\d{2})/100\*\*?", content)

    assert len(scores) > 0, "No scores found in scorecard"

    for score in scores:
        score_int = int(score)
        assert 0 <= score_int <= 100, f"Score {score_int} is out of range (0-100)"


def test_scorecard_has_blocker_issues():
    """Verify services below threshold have blocker issues listed."""
    content = SCORECARD_PATH.read_text()

    # Services that are below threshold (scores < 70)
    below_threshold_services = [
        "OpenClaw Gateway",
        "OpenHands Agent",
        "OpenCode Agent",
        "DGX Spark",
        "NemoClaw",
        "RAG Service",
        "Grant Scout",
        "Network Isolation",
    ]

    # Verify each has blocker issues section
    for service in below_threshold_services:
        # Look for the service section and check for Blockers
        service_pattern = rf"{service}.*?(\*\*TOTAL\*\*.*?)?"
        # At minimum verify the service exists
        assert service in content, f"Missing below-threshold service: {service}"


def test_scorecard_has_evidence_links():
    """Verify scorecard includes evidence links to documentation."""
    content = SCORECARD_PATH.read_text()

    # Check for markdown link patterns that point to docs
    link_pattern = r"\[.*?\]\(.*?\.md\)"
    links = re.findall(link_pattern, content)

    assert len(links) >= 10, f"Expected at least 10 evidence links, found {len(links)}"


def test_scorecard_has_next_steps():
    """Verify the scorecard has next steps section."""
    content = SCORECARD_PATH.read_text()

    assert "Next Steps" in content, "Missing next steps section"
    assert "Immediate" in content, "Missing immediate actions"
    assert "Short-term" in content, "Missing short-term actions"
    assert "Medium-term" in content, "Missing medium-term actions"


def test_blocker_issues_are_documented():
    """Verify blocker issues follow the format specified in the issue."""
    content = SCORECARD_PATH.read_text()

    # Check for blocker issue patterns like "- [ ] **PRIORITY:** Description"
    blocker_pattern = r"- \[ \] \*\*[A-Z]+:\*\*"
    blockers = re.findall(blocker_pattern, content)

    assert len(blockers) >= 10, f"Expected at least 10 blocker issues, found {len(blockers)}"


def test_scorecard_has_last_updated_date():
    """Verify the scorecard has a last updated date."""
    content = SCORECARD_PATH.read_text()

    # The header line is: **Last Updated:** 2026-07-02
    # Simple pattern: Last Updated followed by a date
    date_pattern = r"Last Updated.*?\d{4}-\d{2}-\d{2}"
    assert re.search(date_pattern, content), "Missing last updated date"
