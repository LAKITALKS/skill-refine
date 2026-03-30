"""Tests for section extraction."""

from skill_refine.core.sections import extract_sections, find_section, has_section


def test_extract_sections() -> None:
    body = """\
## Description

This is a description.

## Steps

1. Step one
2. Step two

## Warnings

Be careful.
"""
    sections = extract_sections(body)
    assert len(sections) == 3
    assert sections[0].heading == "Description"
    assert sections[1].heading == "Steps"
    assert sections[2].heading == "Warnings"


def test_section_content() -> None:
    body = "## Foo\n\nContent of foo.\n\n## Bar\n\nContent of bar."
    sections = extract_sections(body)
    assert "Content of foo." in sections[0].content
    assert "Content of bar." in sections[1].content


def test_find_section_case_insensitive() -> None:
    body = "## When To Apply\n\nDo this when X."
    sections = extract_sections(body)
    assert find_section(sections, "when to apply") is not None
    assert find_section(sections, "When To Apply") is not None


def test_has_section() -> None:
    body = "## Description\n\nHello."
    sections = extract_sections(body)
    assert has_section(sections, "description")
    assert not has_section(sections, "warnings")


def test_no_headings() -> None:
    sections = extract_sections("Just plain text without headings.")
    assert sections == []


def test_word_count() -> None:
    body = "## Test\n\none two three four five"
    sections = extract_sections(body)
    assert sections[0].word_count == 5
