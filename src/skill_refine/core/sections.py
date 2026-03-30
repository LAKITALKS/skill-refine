"""Section detection for Markdown skill files."""

from __future__ import annotations

import re

from skill_refine.core.models import Section
from skill_refine.core.tokens import count_words


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def extract_sections(body: str) -> list[Section]:
    """Extract sections from Markdown body based on ## headings."""
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
