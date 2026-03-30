"""Tests for the rule-based checker."""

from pathlib import Path
from textwrap import dedent

import pytest

from skill_refine.analysis.checker import run_checks
from skill_refine.core.parser import parse_skill


@pytest.fixture
def good_skill(tmp_path: Path) -> Path:
    content = dedent("""\
        ---
        name: Good Skill
        description: A well-structured skill
        tags:
          - example
        ---

        ## Description

        This is a well-structured skill that demonstrates proper formatting and content.

        ## When to apply

        When you need to do a specific, well-defined task.

        ## When not to apply

        When the task is outside the scope of this skill.

        ## Warnings

        Be careful with edge cases.

        ## Inputs

        - A clearly defined input parameter

        ## Outputs

        - A clearly defined output

        ## Steps

        1. First step
        2. Second step

        ## Examples

        Example usage here.
    """)
    p = tmp_path / "good.md"
    p.write_text(content)
    return p


@pytest.fixture
def bad_skill(tmp_path: Path) -> Path:
    content = dedent("""\
        ---
        name: Bad
        ---

        ## Description

        Short.
    """)
    p = tmp_path / "bad.md"
    p.write_text(content)
    return p


@pytest.fixture
def empty_skill(tmp_path: Path) -> Path:
    p = tmp_path / "empty.md"
    p.write_text("")
    return p


@pytest.fixture
def no_sections_skill(tmp_path: Path) -> Path:
    content = dedent("""\
        ---
        name: Flat
        description: No sections at all
        tags: [flat]
        ---

        Just some text without any markdown headings.
    """)
    p = tmp_path / "flat.md"
    p.write_text(content)
    return p


def test_good_skill_few_findings(good_skill: Path) -> None:
    skill = parse_skill(good_skill)
    findings = run_checks(skill)
    rules = [f.rule for f in findings]
    assert "missing-frontmatter" not in rules
    assert "missing-section" not in rules


def test_bad_skill_has_findings(bad_skill: Path) -> None:
    skill = parse_skill(bad_skill)
    findings = run_checks(skill)
    rules = [f.rule for f in findings]
    assert "missing-meta-description" in rules
    assert "missing-tags" in rules
    assert "missing-section" in rules
    assert "short-description" in rules


def test_empty_file_findings(empty_skill: Path) -> None:
    skill = parse_skill(empty_skill)
    findings = run_checks(skill)
    rules = [f.rule for f in findings]
    assert "missing-frontmatter" in rules
    assert "missing-section" in rules


def test_no_sections_findings(no_sections_skill: Path) -> None:
    skill = parse_skill(no_sections_skill)
    findings = run_checks(skill)
    rules = [f.rule for f in findings]
    assert "missing-frontmatter" not in rules
    assert "missing-section" in rules
    # All 8 expected sections should be missing
    missing_count = sum(1 for f in findings if f.rule == "missing-section")
    assert missing_count == 8
