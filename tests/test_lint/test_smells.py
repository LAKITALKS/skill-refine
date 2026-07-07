"""Tests for profile-driven smell detection."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from skill_refine.lint.models import SmellType
from skill_refine.lint.parser import parse_skill
from skill_refine.lint.profiles import STANDARD, STRICT
from skill_refine.lint.smells import detect_smells


@pytest.fixture
def vague_skill(tmp_path: Path) -> Path:
    p = tmp_path / "vague.md"
    p.write_text(
        dedent("""\
            ---
            name: Vague
            description: vague thing that applies
            tags: [x]
            ---

            ## When to apply

            Use this when needed, as appropriate, whenever it seems right.
        """)
    )
    return p


def test_strict_vague_trigger_detected(vague_skill: Path) -> None:
    smells = detect_smells(parse_skill(vague_skill), STRICT)
    assert SmellType.VAGUE_TRIGGER in smells


def test_strict_no_frontmatter_smells(no_frontmatter_skill: Path) -> None:
    smells = detect_smells(parse_skill(no_frontmatter_skill), STRICT)
    assert SmellType.EMPTY_FRONTMATTER in smells
    assert SmellType.NO_BOUNDARIES in smells
    assert SmellType.NO_WARNINGS in smells


def test_strict_full_skill_no_smells(strict_full_skill: Path) -> None:
    assert detect_smells(parse_skill(strict_full_skill), STRICT) == []


def test_standard_suppresses_section_schema_smells(no_frontmatter_skill: Path) -> None:
    smells = detect_smells(parse_skill(no_frontmatter_skill), STANDARD)
    assert SmellType.EMPTY_FRONTMATTER not in smells
    assert SmellType.NO_BOUNDARIES not in smells
    assert SmellType.NO_WARNINGS not in smells


def test_standard_still_flags_wall_of_text(tmp_path: Path) -> None:
    p = tmp_path / "wall.md"
    body = " ".join(["word"] * 200)
    p.write_text(f"---\nname: x\ndescription: a long enough description here\n---\n\n{body}\n")
    smells = detect_smells(parse_skill(p), STANDARD)
    assert SmellType.WALL_OF_TEXT in smells


def test_standard_clean_skill_no_smells(standard_skill: Path) -> None:
    assert detect_smells(parse_skill(standard_skill), STANDARD) == []
