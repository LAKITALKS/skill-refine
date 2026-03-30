"""Heuristic smell detection for skill files."""

from __future__ import annotations

from skill_refine.core.config import (
    MAX_PARAGRAPH_WORDS,
    MAX_TOTAL_WORDS,
    VAGUE_TRIGGER_PHRASES,
)
from skill_refine.core.models import Skill, SmellType
from skill_refine.core.sections import find_section, has_section


def detect_smells(skill: Skill) -> list[SmellType]:
    """Detect heuristic smells in a skill."""
    smells: list[SmellType] = []

    if not skill.metadata.raw:
        smells.append(SmellType.EMPTY_FRONTMATTER)

    if _has_vague_trigger(skill):
        smells.append(SmellType.VAGUE_TRIGGER)

    if not has_section(skill.sections, "warnings"):
        smells.append(SmellType.NO_WARNINGS)

    if not has_section(skill.sections, "when not to apply"):
        smells.append(SmellType.NO_FAILURE_CASES)

    if skill.word_count > MAX_TOTAL_WORDS:
        smells.append(SmellType.TOKEN_BLOAT)

    if not has_section(skill.sections, "inputs") and not has_section(
        skill.sections, "outputs"
    ):
        smells.append(SmellType.NO_INPUTS_OUTPUTS)

    if not has_section(skill.sections, "when to apply") and not has_section(
        skill.sections, "when not to apply"
    ):
        smells.append(SmellType.NO_BOUNDARIES)

    if _has_wall_of_text(skill):
        smells.append(SmellType.WALL_OF_TEXT)

    return smells


def _has_vague_trigger(skill: Skill) -> bool:
    """Check if 'when to apply' section contains vague language."""
    section = find_section(skill.sections, "when to apply")
    if not section:
        return False
    lower = section.content.lower()
    return any(phrase in lower for phrase in VAGUE_TRIGGER_PHRASES)


def _has_wall_of_text(skill: Skill) -> bool:
    """Check if any paragraph exceeds the word threshold."""
    paragraphs = skill.body.split("\n\n")
    return any(
        len(p.split()) > MAX_PARAGRAPH_WORDS
        for p in paragraphs
        if p.strip() and not p.strip().startswith("#")
    )
