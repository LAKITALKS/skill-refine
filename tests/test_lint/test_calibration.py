"""Calibration gate for the standard profile, locked to vendored reference skills.

Real, Apache-2.0-licensed Agent Skills are vendored under
``tests/fixtures/reference_skills/`` (see that directory's NOTICE for provenance
and license verification). They MUST score highly and carry no errors under the
default ``standard`` profile, pinning the v0.2 measuring stick.

``mcp-builder`` additionally locks the empty-section regression fix: several of
its parent headings carry no direct text of their own (their content lives in
child subsections). Without the fix those would be flagged empty and collapse
the structure sub-score; this test fails if that regresses.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_refine.lint import Severity, lint_path
from skill_refine.lint.profiles import STANDARD
from skill_refine.lint.sections import is_empty_section

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "reference_skills"
_VENDORED = sorted(p.parent.name for p in _FIXTURES.rglob("SKILL.md"))


def test_reference_fixtures_present() -> None:
    assert _VENDORED, f"no vendored reference skills under {_FIXTURES}"
    # The two skills chosen in the calibration plan.
    assert "mcp-builder" in _VENDORED
    assert "webapp-testing" in _VENDORED


@pytest.mark.parametrize("skill_name", _VENDORED)
def test_reference_skill_meets_standard_calibration(skill_name: str) -> None:
    reports = lint_path(_FIXTURES / skill_name / "SKILL.md", STANDARD)
    assert len(reports) == 1
    report = reports[0]

    errors = [f for f in report.findings if f.severity == Severity.ERROR]
    assert errors == [], f"{skill_name} has ERROR findings: {[f.id for f in errors]}"

    assert report.score.total >= 8.0, (
        f"{skill_name} scored {report.score.total}/10 under standard (expected >= 8.0)"
    )


def test_mcp_builder_locks_empty_section_and_structure() -> None:
    """Structure regression lock for the empty-section fix (see module docstring)."""
    reports = lint_path(_FIXTURES / "mcp-builder" / "SKILL.md", STANDARD)
    report = reports[0]

    # No empty-section false positives anywhere.
    empty = [f for f in report.findings if f.id == "empty-section"]
    assert empty == [], f"unexpected empty-section findings: {[f.section for f in empty]}"

    # Sanity: the fixture really does contain parent headings with subsections and
    # no direct text of their own (the exact pattern that used to false-positive).
    secs = report.skill.sections
    protected = [
        i
        for i in range(len(secs) - 1)
        if secs[i + 1].level > secs[i].level and not secs[i].content.strip()
    ]
    assert protected, "fixture no longer exercises the parent-with-subsection case"
    for i in protected:
        assert not is_empty_section(secs, i), f"'{secs[i].heading}' wrongly seen as empty"

    # The structure sub-score must stay high; without the fix it would collapse.
    assert report.score.structure >= 8.0, (
        f"mcp-builder structure sub-score is {report.score.structure}/10 (expected >= 8.0)"
    )


def test_lint_path_discovers_vendored_folder_skills() -> None:
    reports = lint_path(_FIXTURES, "standard")
    assert {r.name for r in reports} == set(_VENDORED)
    assert all(r.skill_format == "folder" for r in reports)
