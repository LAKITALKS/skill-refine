"""Section detection for Markdown skill files.

Part of the offline, deterministic lint core: no LLM/provider/network imports.
"""

from __future__ import annotations

import re

from skill_refine.lint.models import Section
from skill_refine.lint.tokens import count_words

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def extract_sections(body: str) -> list[Section]:
    """Extract sections from a Markdown body based on ATX headings."""
    matches = list(_HEADING_RE.finditer(body))
    if not matches:
        return []

    sections: list[Section] = []
    for i, match in enumerate(matches):
        level = len(match.group(1))
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        sections.append(
            Section(
                heading=heading,
                level=level,
                content=content,
                word_count=count_words(content),
            )
        )
    return sections


def find_section(sections: list[Section], name: str) -> Section | None:
    """Find a section by name (case-insensitive)."""
    normalized = name.lower().strip()
    for section in sections:
        if section.heading.lower().strip() == normalized:
            return section
    return None


def has_section(sections: list[Section], name: str) -> bool:
    """Check if a section exists by name."""
    return find_section(sections, name) is not None


def has_child_sections(sections: list[Section], index: int) -> bool:
    """Whether the section at ``index`` is a parent of deeper subsections.

    Sections are split at every heading, so a heading immediately followed by a
    deeper heading (e.g. ``## Tools`` then ``### Tool A``) has no direct text of
    its own — but it is not empty, its content lives in its subsections.
    """
    if index + 1 >= len(sections):
        return False
    return sections[index + 1].level > sections[index].level


def is_empty_section(sections: list[Section], index: int) -> bool:
    """Whether the section at ``index`` is genuinely empty.

    A section counts as empty only if it has no direct textual content (which
    already includes code blocks, since those live between headings) AND no
    child subsections nested under it.
    """
    section = sections[index]
    if section.content.strip():
        return False
    return not has_child_sections(sections, index)
