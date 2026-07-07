"""Tests for the skill parser."""

from pathlib import Path
from textwrap import dedent

import pytest

from skill_refine.lint.parser import parse_skill


@pytest.fixture
def tmp_skill(tmp_path: Path) -> Path:
    content = dedent("""\
        ---
        name: Test Skill
        description: A test skill for unit testing
        tags:
          - test
          - unit
        ---

        ## Description

        This is a test skill that does something useful for testing purposes.

        ## Steps

        1. Do step one
        2. Do step two
    """)
    p = tmp_path / "test-skill.md"
    p.write_text(content)
    return p


def test_parse_skill_metadata(tmp_skill: Path) -> None:
    skill = parse_skill(tmp_skill)
    assert skill.metadata.name == "Test Skill"
    assert skill.metadata.description == "A test skill for unit testing"
    assert skill.metadata.tags == ["test", "unit"]


def test_parse_skill_sections(tmp_skill: Path) -> None:
    skill = parse_skill(tmp_skill)
    headings = [s.heading for s in skill.sections]
    assert "Description" in headings
    assert "Steps" in headings


def test_parse_skill_word_count(tmp_skill: Path) -> None:
    skill = parse_skill(tmp_skill)
    assert skill.word_count > 0
    assert skill.estimated_tokens > 0


def test_parse_no_frontmatter(no_frontmatter_skill: Path) -> None:
    skill = parse_skill(no_frontmatter_skill)
    assert skill.metadata.name == ""
    assert skill.metadata.tags == []
    assert not skill.metadata.raw


def test_parse_empty_file(empty_skill: Path) -> None:
    skill = parse_skill(empty_skill)
    assert skill.metadata.name == ""
    assert skill.body == ""
    assert skill.sections == []
    assert skill.word_count == 0
    assert skill.estimated_tokens == 0


def test_parse_whitespace_only(tmp_path: Path) -> None:
    p = tmp_path / "whitespace.md"
    p.write_text("   \n\n  \n")
    skill = parse_skill(p)
    assert skill.word_count == 0
    assert skill.sections == []


def test_parse_partial_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "partial.md"
    p.write_text("---\nname: Partial\n---\n\nSome body text.\n")
    skill = parse_skill(p)
    assert skill.metadata.name == "Partial"
    assert skill.metadata.description == ""
    assert skill.metadata.tags == []
    assert "name" in skill.metadata.raw


def test_parse_comma_separated_tags(tmp_path: Path) -> None:
    p = tmp_path / "comma.md"
    p.write_text('---\nname: Comma Tags\ntags: "foo, bar, baz"\n---\n\nBody.\n')
    skill = parse_skill(p)
    assert skill.metadata.tags == ["foo", "bar", "baz"]
