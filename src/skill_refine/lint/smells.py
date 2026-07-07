"""Profile-driven heuristic smell detection for skill files.

Only smells enabled by the active profile are reported, so the section-schema
smells (``NO_WARNINGS`` etc.) do not fire under the ``standard`` profile.

Part of the offline, deterministic lint core: no LLM/provider/network imports.
"""

from __future__ import annotations

from skill_refine.lint.models import Skill, SmellType
from skill_refine.lint.profiles import Profile
from skill_refine.lint.sections import find_section, has_section

SMELL_MESSAGES: dict[str, str] = {
    "VAGUE_TRIGGER": "Trigger condition uses imprecise language.",
    "NO_WARNINGS": "No warnings or caveats defined.",
    "NO_FAILURE_CASES": "No negative cases (when not to apply).",
    "TOKEN_BLOAT": "Skill exceeds reasonable token budget.",
    "NO_INPUTS_OUTPUTS": "Inputs/Outputs not specified.",
    "NO_BOUNDARIES": "No application boundaries defined.",
    "WALL_OF_TEXT": "Oversized paragraphs without structure.",
    "EMPTY_FRONTMATTER": "YAML frontmatter missing entirely.",
}


def detect_smells(skill: Skill, profile: Profile) -> list[SmellType]:
    """Detect heuristic smells enabled by the active profile."""
    enabled = profile.smells
    smells: list[SmellType] = []

    def add(smell: SmellType) -> None:
        if smell.value in enabled:
            smells.append(smell)

    if not skill.metadata.raw:
        add(SmellType.EMPTY_FRONTMATTER)

    if _has_vague_trigger(skill, profile):
        add(SmellType.VAGUE_TRIGGER)

    if not has_section(skill.sections, "warnings"):
        add(SmellType.NO_WARNINGS)

    if not has_section(skill.sections, "when not to apply"):
        add(SmellType.NO_FAILURE_CASES)

    if skill.word_count > profile.max_total_words:
        add(SmellType.TOKEN_BLOAT)

    if not has_section(skill.sections, "inputs") and not has_section(
        skill.sections, "outputs"
    ):
        add(SmellType.NO_INPUTS_OUTPUTS)

    if not has_section(skill.sections, "when to apply") and not has_section(
        skill.sections, "when not to apply"
    ):
        add(SmellType.NO_BOUNDARIES)

    if _has_wall_of_text(skill, profile):
        add(SmellType.WALL_OF_TEXT)

    return smells


def _has_vague_trigger(skill: Skill, profile: Profile) -> bool:
    """Check if the 'when to apply' section contains vague language."""
    section = find_section(skill.sections, "when to apply")
    if not section:
        return False
    lower = section.content.lower()
    return any(phrase in lower for phrase in profile.vague_trigger_phrases)


def _has_wall_of_text(skill: Skill, profile: Profile) -> bool:
    """Check if any paragraph exceeds the word threshold."""
    paragraphs = skill.body.split("\n\n")
    return any(
        len(p.split()) > profile.max_paragraph_words
        for p in paragraphs
        if p.strip() and not p.strip().startswith("#")
    )
