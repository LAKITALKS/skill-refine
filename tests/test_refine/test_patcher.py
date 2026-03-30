"""Tests for patcher functionality."""

from pathlib import Path
from textwrap import dedent

import pytest

from skill_refine.core.models import BoundaryConfidence, PatchProposal
from skill_refine.core.parser import parse_skill
from skill_refine.refine.patcher import apply_patch, assess_boundary_confidence, _find_section_span
from skill_refine.core.sections import extract_sections


@pytest.fixture
def structured_skill(tmp_path: Path):
    content = dedent("""\
        ---
        name: Structured
        description: Has clear sections
        tags: [test]
        ---

        ## Description

        This is a well-structured skill with clear boundaries.

        ## When to apply

        When you need to do X.

        ## Warnings

        Be careful with Y.
    """)
    p = tmp_path / "structured.md"
    p.write_text(content)
    return parse_skill(p)


@pytest.fixture
def flat_skill(tmp_path: Path):
    content = "Just text without any structure.\n"
    p = tmp_path / "flat.md"
    p.write_text(content)
    return parse_skill(p)


@pytest.fixture
def duplicate_headings_skill(tmp_path: Path):
    content = dedent("""\
        ---
        name: Dupes
        ---

        ## Notes

        First notes section.

        ## Notes

        Second notes section.
    """)
    p = tmp_path / "dupes.md"
    p.write_text(content)
    return parse_skill(p)


def test_confidence_high_for_clear_structure(structured_skill) -> None:
    confidence = assess_boundary_confidence(structured_skill, "description")
    assert confidence == BoundaryConfidence.HIGH


def test_confidence_low_for_missing_section(structured_skill) -> None:
    confidence = assess_boundary_confidence(structured_skill, "nonexistent")
    assert confidence == BoundaryConfidence.LOW


def test_confidence_low_for_flat_skill(flat_skill) -> None:
    confidence = assess_boundary_confidence(flat_skill, "description")
    assert confidence == BoundaryConfidence.LOW


def test_apply_patch(structured_skill) -> None:
    proposal = PatchProposal(
        section_name="description",
        original="This is a well-structured skill with clear boundaries.",
        proposed="This is an improved description with more detail.",
        confidence=BoundaryConfidence.HIGH,
    )

    result = apply_patch(structured_skill, proposal)

    assert "This is an improved description with more detail." in result
    assert "## Description" in result
    assert "## When to apply" in result  # Other sections preserved
    assert "## Warnings" in result


def test_apply_patch_missing_section(structured_skill) -> None:
    proposal = PatchProposal(
        section_name="nonexistent",
        original="",
        proposed="New content",
        confidence=BoundaryConfidence.LOW,
    )

    result = apply_patch(structured_skill, proposal)
    assert result == structured_skill.raw_content  # Unchanged


def test_apply_patch_duplicate_headings_returns_unchanged(duplicate_headings_skill) -> None:
    """When a section name appears multiple times, apply_patch should not patch (ambiguous)."""
    proposal = PatchProposal(
        section_name="notes",
        original="First notes section.",
        proposed="Rewritten notes.",
        confidence=BoundaryConfidence.MEDIUM,
    )

    result = apply_patch(duplicate_headings_skill, proposal)
    assert result == duplicate_headings_skill.raw_content  # Unchanged due to ambiguity


def test_find_section_span_unique() -> None:
    body = "## Foo\n\nContent of foo.\n\n## Bar\n\nContent of bar."
    span = _find_section_span(body, "foo")
    assert span is not None
    start, end = span
    assert "Content of foo." in body[start:end]


def test_find_section_span_ambiguous() -> None:
    body = "## Notes\n\nFirst.\n\n## Notes\n\nSecond."
    span = _find_section_span(body, "notes")
    assert span is None  # Ambiguous


def test_find_section_span_not_found() -> None:
    body = "## Foo\n\nContent."
    span = _find_section_span(body, "nonexistent")
    assert span is None


def test_apply_patch_preserves_frontmatter(structured_skill) -> None:
    proposal = PatchProposal(
        section_name="warnings",
        original="Be careful with Y.",
        proposed="Handle edge cases and validate input.",
        confidence=BoundaryConfidence.HIGH,
    )

    result = apply_patch(structured_skill, proposal)

    assert "---" in result
    assert "name: Structured" in result
    assert "Handle edge cases and validate input." in result
