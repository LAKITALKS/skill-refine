"""Tests for guard functionality."""

from pathlib import Path
from textwrap import dedent

import pytest

from skill_refine.core.parser import parse_skill
from skill_refine.safety.guard import check_rewrite


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
    result = check_rewrite(skill_with_sections, rewritten)
    assert result.passed
    assert not result.blocked


def test_guard_blocks_empty_content(skill_with_sections) -> None:
    result = check_rewrite(skill_with_sections, "")
    assert not result.passed
    assert result.blocked


def test_guard_blocks_whitespace_only(skill_with_sections) -> None:
    result = check_rewrite(skill_with_sections, "   \n\n  ")
    assert not result.passed
    assert result.blocked


def test_guard_warns_frontmatter_lost(skill_with_sections) -> None:
    rewritten = "## Description\n\nJust text without frontmatter."
    result = check_rewrite(skill_with_sections, rewritten)
    codes = [w.code for w in result.warnings]
    assert "frontmatter-lost" in codes


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
    # Warnings section was removed
    result = check_rewrite(skill_with_sections, rewritten)
    codes = [w.code for w in result.warnings]
    assert "section-removed" in codes


def test_guard_warns_token_shrink(skill_with_sections) -> None:
    rewritten = dedent("""\
        ---
        name: Test
        ---

        Short.
    """)
    result = check_rewrite(skill_with_sections, rewritten)
    codes = [w.code for w in result.warnings]
    assert "token-shrink" in codes
