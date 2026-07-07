"""Tests for section extraction."""

from skill_refine.lint.sections import extract_sections, find_section, has_section


def test_extract_sections() -> None:
    body = "## Description\n\nA description.\n\n## Steps\n\n1. one\n\n## Warnings\n\nCareful."
    sections = extract_sections(body)
    assert [s.heading for s in sections] == ["Description", "Steps", "Warnings"]


def test_section_content() -> None:
    body = "## Foo\n\nContent of foo.\n\n## Bar\n\nContent of bar."
    sections = extract_sections(body)
    assert "Content of foo." in sections[0].content
    assert "Content of bar." in sections[1].content


def test_find_section_case_insensitive() -> None:
    sections = extract_sections("## When To Apply\n\nDo this when X.")
    assert find_section(sections, "when to apply") is not None
    assert find_section(sections, "When To Apply") is not None


def test_has_section() -> None:
    sections = extract_sections("## Description\n\nHello.")
    assert has_section(sections, "description")
    assert not has_section(sections, "warnings")


def test_no_headings() -> None:
    assert extract_sections("Just plain text without headings.") == []


def test_word_count() -> None:
    sections = extract_sections("## Test\n\none two three four five")
    assert sections[0].word_count == 5
