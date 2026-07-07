"""Tests for the profile-driven deterministic scorer."""

from __future__ import annotations

from pathlib import Path

from skill_refine.lint.parser import parse_skill
from skill_refine.lint.profiles import STANDARD, STRICT
from skill_refine.lint.scorer import compute_score

# --- strict profile: regression against legacy v0.1 behavior ---


def test_strict_full_skill_high_score(strict_full_skill: Path) -> None:
    score = compute_score(parse_skill(strict_full_skill), STRICT)
    assert score.total >= 7.0
    assert score.completeness >= 8.0
    assert score.metadata >= 8.0


def test_strict_empty_skill_low_score(empty_skill: Path) -> None:
    score = compute_score(parse_skill(empty_skill), STRICT)
    assert score.total <= 2.5
    assert score.completeness == 0.0
    assert score.structure == 0.0
    assert score.metadata == 0.0


def test_strict_no_frontmatter_zero_metadata(no_frontmatter_skill: Path) -> None:
    score = compute_score(parse_skill(no_frontmatter_skill), STRICT)
    assert score.metadata == 0.0
    assert score.completeness == 0.0


def test_score_bounds(strict_full_skill: Path) -> None:
    score = compute_score(parse_skill(strict_full_skill), STRICT)
    for val in (
        score.completeness,
        score.structure,
        score.metadata,
        score.conciseness,
        score.total,
    ):
        assert 0.0 <= val <= 10.0


# --- standard profile ---


def test_standard_good_skill_high_score(standard_skill: Path) -> None:
    score = compute_score(parse_skill(standard_skill), STANDARD)
    assert score.total >= 7.0
    # name + description present -> full metadata under standard
    assert score.metadata == 10.0


def test_standard_empty_skill_low_score(empty_skill: Path) -> None:
    score = compute_score(parse_skill(empty_skill), STANDARD)
    assert score.total <= 3.0
    assert score.metadata == 0.0


def test_standard_and_strict_differ(standard_skill: Path) -> None:
    """The same skill scores differently under the two profiles."""
    skill = parse_skill(standard_skill)
    standard = compute_score(skill, STANDARD)
    strict = compute_score(skill, STRICT)
    # It lacks the 8 legacy sections, so strict completeness is low...
    assert strict.completeness < standard.completeness
    # ...and the overall totals are not identical.
    assert standard.total != strict.total
