"""Tests for the scorer."""

from pathlib import Path
from textwrap import dedent

import pytest

from skill_refine.analysis.scorer import compute_score
from skill_refine.core.parser import parse_skill


@pytest.fixture
def complete_skill(tmp_path: Path) -> Path:
    content = dedent("""\
        ---
        name: Complete Skill
        description: Fully complete
        tags: [a, b]
        ---

        ## Description

        A thorough description of what this skill does and how it works in practice.

        ## When to apply

        When a specific condition is met.

        ## When not to apply

        When outside scope.

        ## Warnings

        Handle with care.

        ## Inputs

        - Input A

        ## Outputs

        - Output B

        ## Steps

        1. Do X
        2. Do Y

        ## Examples

        Example here.
    """)
    p = tmp_path / "complete.md"
    p.write_text(content)
    return p


@pytest.fixture
def empty_skill(tmp_path: Path) -> Path:
    p = tmp_path / "empty.md"
    p.write_text("")
    return p


@pytest.fixture
def no_frontmatter_skill(tmp_path: Path) -> Path:
    p = tmp_path / "bare.md"
    p.write_text("No structure at all.\n")
    return p


def test_complete_skill_high_score(complete_skill: Path) -> None:
    skill = parse_skill(complete_skill)
    score = compute_score(skill)
    assert score.total >= 7.0
    assert score.completeness >= 8.0
    assert score.metadata >= 8.0


def test_empty_skill_low_score(empty_skill: Path) -> None:
    skill = parse_skill(empty_skill)
    score = compute_score(skill)
    assert score.total <= 2.5
    assert score.completeness == 0.0
    assert score.structure == 0.0
    assert score.metadata == 0.0


def test_no_frontmatter_low_metadata(no_frontmatter_skill: Path) -> None:
    skill = parse_skill(no_frontmatter_skill)
    score = compute_score(skill)
    assert score.metadata == 0.0
    assert score.completeness == 0.0


def test_score_bounds(complete_skill: Path) -> None:
    skill = parse_skill(complete_skill)
    score = compute_score(skill)
    for val in [score.completeness, score.structure, score.metadata, score.conciseness, score.total]:
        assert 0.0 <= val <= 10.0
