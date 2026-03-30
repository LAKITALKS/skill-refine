"""Parser for Markdown skill files with YAML frontmatter."""

from __future__ import annotations

from pathlib import Path

import frontmatter

from skill_refine.core.models import Skill, SkillMetadata
from skill_refine.core.sections import extract_sections
from skill_refine.core.tokens import count_words, estimate_tokens


def parse_skill(path: Path) -> Skill:
    """Parse a Markdown skill file into a Skill object.

    Handles gracefully:
    - Empty files
    - Files without frontmatter
    - Files with partial frontmatter
    - Files without any ## sections
    """
    raw_content = path.read_text(encoding="utf-8")

    if not raw_content.strip():
        return Skill(
            path=path,
            raw_content=raw_content,
            metadata=SkillMetadata(),
            body="",
            sections=[],
            word_count=0,
            estimated_tokens=0,
        )

    post = frontmatter.loads(raw_content)

    raw_meta = dict(post.metadata) if post.metadata else {}
    metadata = SkillMetadata(
        name=str(raw_meta.get("name", "") or ""),
        description=str(raw_meta.get("description", "") or ""),
        tags=_normalize_tags(raw_meta.get("tags")),
        raw=raw_meta,
    )

    body = post.content
    sections = extract_sections(body)

    return Skill(
        path=path,
        raw_content=raw_content,
        metadata=metadata,
        body=body,
        sections=sections,
        word_count=count_words(raw_content),
        estimated_tokens=estimate_tokens(raw_content),
    )


def _normalize_tags(tags: object) -> list[str]:
    """Normalize tags to a list of strings."""
    if tags is None:
        return []
    if isinstance(tags, list):
        return [str(t) for t in tags if t is not None]
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    return []
