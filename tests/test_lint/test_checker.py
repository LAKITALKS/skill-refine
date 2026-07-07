"""Tests for the profile-driven rule-based checker."""

from __future__ import annotations

from pathlib import Path

from skill_refine.lint.checker import run_checks
from skill_refine.lint.parser import parse_skill
from skill_refine.lint.profiles import STANDARD, STRICT


def _ids(path: Path, profile) -> list[str]:
    return [f.id for f in run_checks(parse_skill(path), profile)]


# --- strict profile (legacy schema) ---


def test_strict_full_skill_clean(strict_full_skill: Path) -> None:
    ids = _ids(strict_full_skill, STRICT)
    assert "missing-frontmatter" not in ids
    assert "missing-section" not in ids


def test_strict_name_only_skill_findings(name_only_skill: Path) -> None:
    ids = _ids(name_only_skill, STRICT)
    assert "missing-frontmatter-description" in ids
    assert "missing-frontmatter-tags" in ids
    assert "missing-section" in ids
    assert "short-description" in ids


def test_strict_empty_file(empty_skill: Path) -> None:
    ids = _ids(empty_skill, STRICT)
    assert "missing-frontmatter" in ids
    assert "missing-section" in ids


def test_strict_no_sections_reports_all_eight(no_frontmatter_skill: Path) -> None:
    findings = run_checks(parse_skill(no_frontmatter_skill), STRICT)
    missing = sum(1 for f in findings if f.id == "missing-section")
    assert missing == 8


# --- standard profile (Agent Skills aligned) ---


def test_standard_requires_description_as_error(name_only_skill: Path) -> None:
    findings = run_checks(parse_skill(name_only_skill), STANDARD)
    desc = [f for f in findings if f.id == "missing-frontmatter-description"]
    assert desc and desc[0].severity.value == "error"


def test_standard_does_not_demand_sections(standard_skill: Path) -> None:
    ids = _ids(standard_skill, STANDARD)
    assert "missing-section" not in ids
    assert "missing-frontmatter-name" not in ids
    assert "missing-frontmatter-description" not in ids


def test_standard_flags_short_description(tmp_path: Path) -> None:
    p = tmp_path / "s.md"
    p.write_text("---\nname: x\ndescription: too short\n---\n\nbody\n")
    ids = _ids(p, STANDARD)
    assert "short-frontmatter-description" in ids


def test_standard_missing_frontmatter_entirely(no_frontmatter_skill: Path) -> None:
    ids = _ids(no_frontmatter_skill, STANDARD)
    assert "missing-frontmatter" in ids


# --- empty-section false-positive regression ---


def test_parent_section_with_subsections_not_empty(tmp_path: Path) -> None:
    """A heading whose content lives in child subsections is not 'empty'."""
    p = tmp_path / "cli.md"
    p.write_text(
        "---\n"
        "name: cli-tools\n"
        "description: a description that is comfortably long enough here\n"
        "---\n\n"
        "## Command-Line Tools\n\n"
        "### Tool A\n\n"
        "```bash\n"
        "example command\n"
        "```\n\n"
        "### Tool B\n\n"
        "Does something else useful.\n"
    )
    findings = run_checks(parse_skill(p), STANDARD)
    empty = [f for f in findings if f.id == "empty-section"]
    assert empty == [], f"unexpected empty-section findings: {[f.section for f in empty]}"


def test_section_with_only_code_block_not_empty(tmp_path: Path) -> None:
    p = tmp_path / "code.md"
    p.write_text(
        "---\nname: x\ndescription: a description long enough to be fine\n---\n\n"
        "## Usage\n\n```bash\nrun --now\n```\n"
    )
    ids = _ids(p, STANDARD)
    assert "empty-section" not in ids


def test_genuinely_empty_section_still_flagged(tmp_path: Path) -> None:
    p = tmp_path / "empty.md"
    p.write_text(
        "---\nname: x\ndescription: a description long enough to be fine\n---\n\n"
        "## Empty Heading\n\n## Next Heading\n\nHas content.\n"
    )
    findings = run_checks(parse_skill(p), STANDARD)
    empty_sections = [f.section for f in findings if f.id == "empty-section"]
    assert "empty heading" in empty_sections
    assert "next heading" not in empty_sections
