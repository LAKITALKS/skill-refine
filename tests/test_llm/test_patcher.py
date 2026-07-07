"""Tests for section patching (requires the LLM extra: httpx)."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

pytest.importorskip("httpx", reason="LLM extra not installed")

from skill_refine.lint.parser import parse_skill
from skill_refine.llm.models import BoundaryConfidence, PatchProposal
from skill_refine.llm.refine.patcher import (
    _find_section_span,
    apply_patch,
    assess_boundary_confidence,
)


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
    p = tmp_path / "flat.md"
    p.write_text("Just text without any structure.\n")
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
    assert assess_boundary_confidence(structured_skill, "description") == (
        BoundaryConfidence.HIGH
    )


def test_confidence_low_for_missing_section(structured_skill) -> None:
    assert assess_boundary_confidence(structured_skill, "nonexistent") == (
        BoundaryConfidence.LOW
    )


def test_confidence_low_for_flat_skill(flat_skill) -> None:
    assert assess_boundary_confidence(flat_skill, "description") == (
        BoundaryConfidence.LOW
    )


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
    assert "## When to apply" in result
    assert "## Warnings" in result


def test_apply_patch_missing_section(structured_skill) -> None:
    proposal = PatchProposal(
        section_name="nonexistent",
        original="",
        proposed="New content",
        confidence=BoundaryConfidence.LOW,
    )
    assert apply_patch(structured_skill, proposal) == structured_skill.raw_content


def test_apply_patch_duplicate_headings_unchanged(duplicate_headings_skill) -> None:
    proposal = PatchProposal(
        section_name="notes",
        original="First notes section.",
        proposed="Rewritten notes.",
        confidence=BoundaryConfidence.MEDIUM,
    )
    result = apply_patch(duplicate_headings_skill, proposal)
    assert result == duplicate_headings_skill.raw_content


def test_find_section_span_unique() -> None:
    body = "## Foo\n\nContent of foo.\n\n## Bar\n\nContent of bar."
    span = _find_section_span(body, "foo")
    assert span is not None
    start, end = span
    assert "Content of foo." in body[start:end]


def test_find_section_span_ambiguous() -> None:
    assert _find_section_span("## Notes\n\nA.\n\n## Notes\n\nB.", "notes") is None


def test_find_section_span_not_found() -> None:
    assert _find_section_span("## Foo\n\nContent.", "nonexistent") is None


def test_apply_patch_preserves_frontmatter(structured_skill) -> None:
    proposal = PatchProposal(
        section_name="warnings",
        original="Be careful with Y.",
        proposed="Handle edge cases and validate input.",
        confidence=BoundaryConfidence.HIGH,
    )
    result = apply_patch(structured_skill, proposal)
    assert "name: Structured" in result
    assert "Handle edge cases and validate input." in result
