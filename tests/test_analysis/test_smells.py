"""Tests for smell detection."""

from pathlib import Path
from textwrap import dedent

import pytest

from skill_refine.analysis.smells import detect_smells
from skill_refine.core.models import SmellType
from skill_refine.core.parser import parse_skill


@pytest.fixture
def vague_skill(tmp_path: Path) -> Path:
    content = dedent("""\
        ---
        name: Vague
        description: vague
        tags: [x]
        ---

        ## Description

        Does something useful in many contexts.

        ## When to apply

        Use this when needed, as appropriate, whenever it seems right.

        ## Steps

        1. Do things
    """)
    p = tmp_path / "vague.md"
    p.write_text(content)
    return p


@pytest.fixture
def no_frontmatter_skill(tmp_path: Path) -> Path:
    p = tmp_path / "bare.md"
    p.write_text("Just text.\n")
    return p


@pytest.fixture
def empty_skill(tmp_path: Path) -> Path:
    p = tmp_path / "empty.md"
    p.write_text("")
    return p


@pytest.fixture
def clean_skill(tmp_path: Path) -> Path:
    content = dedent("""\
        ---
        name: Clean
        description: A clean skill
        tags: [clean]
        ---

        ## Description

        This does something specific and well-defined.

        ## When to apply

        When the user explicitly requests X for a Y context.

        ## When not to apply

        When Y is not relevant.

        ## Warnings

        Be careful with Z.

        ## Inputs

        - Input A

        ## Outputs

        - Output B

        ## Steps

        1. Do X

        ## Examples

        Example here.
    """)
    p = tmp_path / "clean.md"
    p.write_text(content)
    return p


def test_vague_trigger_detected(vague_skill: Path) -> None:
    skill = parse_skill(vague_skill)
    smells = detect_smells(skill)
    assert SmellType.VAGUE_TRIGGER in smells


def test_no_frontmatter_smell(no_frontmatter_skill: Path) -> None:
    skill = parse_skill(no_frontmatter_skill)
    smells = detect_smells(skill)
    assert SmellType.EMPTY_FRONTMATTER in smells


def test_missing_boundaries(no_frontmatter_skill: Path) -> None:
    skill = parse_skill(no_frontmatter_skill)
    smells = detect_smells(skill)
    assert SmellType.NO_BOUNDARIES in smells
    assert SmellType.NO_WARNINGS in smells


def test_empty_file_smells(empty_skill: Path) -> None:
    skill = parse_skill(empty_skill)
    smells = detect_smells(skill)
    assert SmellType.EMPTY_FRONTMATTER in smells
    assert SmellType.NO_WARNINGS in smells
    assert SmellType.NO_BOUNDARIES in smells


def test_clean_skill_no_smells(clean_skill: Path) -> None:
    skill = parse_skill(clean_skill)
    smells = detect_smells(skill)
    assert smells == []
