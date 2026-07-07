"""Tests for the rewrite guard (part of the LLM layer, but offline itself)."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from skill_refine.lint.parser import parse_skill
from skill_refine.lint.profiles import STRICT
from skill_refine.llm.guard import check_rewrite


@pytest.fixture
def skill_with_sections(tmp_path: Path):
    content = dedent("""\
        ---
        name: Test
        description: A test
        tags: [test]
        ---

        ## Description

        This skill does something useful and well-defined for testing purposes.

        ## When to apply

        When testing.

        ## Warnings

        Be careful.
    """)
    p = tmp_path / "test.md"
    p.write_text(content)
    return parse_skill(p)


def test_guard_passes_valid_rewrite(skill_with_sections) -> None:
    rewritten = dedent("""\
        ---
        name: Test
        description: A test
        tags: [test]
        ---

        ## Description

        This skill does something useful and well-defined for testing in practice.

        ## When to apply

        When running unit tests.

        ## Warnings

        Handle edge cases carefully.
    """)
    result = check_rewrite(skill_with_sections, rewritten, STRICT)
    assert result.passed
    assert not result.blocked


def test_guard_blocks_empty_content(skill_with_sections) -> None:
    result = check_rewrite(skill_with_sections, "", STRICT)
    assert not result.passed
    assert result.blocked


def test_guard_blocks_whitespace_only(skill_with_sections) -> None:
    result = check_rewrite(skill_with_sections, "   \n\n  ", STRICT)
    assert not result.passed
    assert result.blocked


def test_guard_warns_frontmatter_lost(skill_with_sections) -> None:
    result = check_rewrite(
        skill_with_sections, "## Description\n\nJust text without frontmatter.", STRICT
    )
    assert "frontmatter-lost" in [w.code for w in result.warnings]


def test_guard_warns_section_removed(skill_with_sections) -> None:
    rewritten = dedent("""\
        ---
        name: Test
        description: A test
        tags: [test]
        ---

        ## Description

        This skill does something useful and well-defined for testing purposes.

        ## When to apply

        When testing.
    """)
    result = check_rewrite(skill_with_sections, rewritten, STRICT)
    assert "section-removed" in [w.code for w in result.warnings]


def test_guard_warns_token_shrink(skill_with_sections) -> None:
    result = check_rewrite(
        skill_with_sections, "---\nname: Test\n---\n\nShort.\n", STRICT
    )
    assert "token-shrink" in [w.code for w in result.warnings]
