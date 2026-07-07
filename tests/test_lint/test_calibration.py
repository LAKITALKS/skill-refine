"""Calibration gate for the standard profile.

Reference-style folder Agent Skills that a well-written SKILL.md should look
like MUST score highly and carry no errors under the default ``standard``
profile. This pins the new (v0.2) measuring stick: if a future change regresses
scoring so that a genuinely good skill drops below 8/10 or sprouts an ERROR,
this test fails.

The fixtures are synthetic but realistic (not vendored third-party files).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_refine.lint import Severity, lint_path
from skill_refine.lint.profiles import STANDARD

_REFERENCE_DIR = Path(__file__).resolve().parents[2] / "examples" / "reference"

_REFERENCE_SKILLS = sorted(p.parent.name for p in _REFERENCE_DIR.rglob("SKILL.md"))


def test_reference_dir_has_fixtures() -> None:
    assert _REFERENCE_SKILLS, f"no reference SKILL.md fixtures under {_REFERENCE_DIR}"


@pytest.mark.parametrize("skill_name", _REFERENCE_SKILLS)
def test_reference_skill_meets_standard_calibration(skill_name: str) -> None:
    skill_md = _REFERENCE_DIR / skill_name / "SKILL.md"
    reports = lint_path(skill_md, STANDARD)
    assert len(reports) == 1
    report = reports[0]

    errors = [f for f in report.findings if f.severity == Severity.ERROR]
    assert errors == [], f"{skill_name} has ERROR findings: {[f.id for f in errors]}"

    assert report.score.total >= 8.0, (
        f"{skill_name} scored {report.score.total}/10 under standard (expected >= 8.0)"
    )


def test_lint_path_accepts_profile_by_name() -> None:
    """lint_path is the promised public entry point and takes a profile string."""
    reports = lint_path(_REFERENCE_DIR, "standard")
    assert {r.name for r in reports} == set(_REFERENCE_SKILLS)
    assert all(r.skill_format == "folder" for r in reports)
