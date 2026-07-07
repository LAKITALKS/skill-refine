"""Profile-driven, deterministic scoring for skill files.

Each sub-score is 0.0-10.0. The total is a weighted average of the sub-scores,
also on a 0-10 scale, using the active profile's weights.

There is no LLM scoring here: the lint core is offline and deterministic. An
optional LLM critique lives separately in ``skill_refine.llm.critique``.
"""

from __future__ import annotations

from skill_refine.lint.models import ScoreCard, Skill
from skill_refine.lint.profiles import Profile
from skill_refine.lint.sections import find_section, is_empty_section


def compute_score(skill: Skill, profile: Profile) -> ScoreCard:
    """Compute a deterministic, rule-based score for a skill."""
    completeness = _score_completeness(skill, profile)
    structure = _score_structure(skill, profile)
    metadata = _score_metadata(skill, profile)
    conciseness = _score_conciseness(skill, profile)

    weights = profile.weights
    total = (
        completeness * weights.get("completeness", 0.0)
        + structure * weights.get("structure", 0.0)
        + metadata * weights.get("metadata", 0.0)
        + conciseness * weights.get("conciseness", 0.0)
    )

    return ScoreCard(
        completeness=round(completeness, 1),
        structure=round(structure, 1),
        metadata=round(metadata, 1),
        conciseness=round(conciseness, 1),
        total=round(total, 1),
    )


def _score_completeness(skill: Skill, profile: Profile) -> float:
    """Completeness of the skill relative to the profile's expectations.

    When a profile defines expected sections, completeness is the fraction of
    those present and non-empty. When it does not (e.g. ``standard``), it
    reflects the essential ingredients of an Agent Skill: a frontmatter
    description, a substantive body, and some structure.
    """
    if profile.expected_sections:
        present = 0
        for name in profile.expected_sections:
            sec = find_section(skill.sections, name)
            if sec and sec.content.strip():
                present += 1
        return (present / len(profile.expected_sections)) * 10.0

    score = 0.0
    if skill.metadata.description.strip():
        score += 5.0
    if skill.word_count >= 20:
        score += 3.0
    if skill.sections:
        score += 2.0
    return min(10.0, score)


def _score_structure(skill: Skill, profile: Profile) -> float:
    """Reward well-structured skills: sections exist, none empty, sane sizes."""
    if not skill.sections:
        return profile.structure_no_sections_score

    score = 10.0

    empty_count = sum(
        1 for i in range(len(skill.sections)) if is_empty_section(skill.sections, i)
    )
    score -= empty_count * 2.0

    oversized_count = sum(
        1 for s in skill.sections if s.word_count > profile.max_section_words
    )
    score -= oversized_count * 1.5

    if len(skill.sections) < profile.structure_min_sections:
        score -= 2.0

    return max(0.0, min(10.0, score))


def _score_metadata(skill: Skill, profile: Profile) -> float:
    """Score based on frontmatter completeness against recommended fields."""
    if not skill.metadata.raw:
        return 0.0

    fields = profile.recommended_frontmatter
    if not fields:
        return 10.0

    present = sum(1 for field in fields if skill.metadata.raw.get(field))
    return (present / len(fields)) * 10.0


def _score_conciseness(skill: Skill, profile: Profile) -> float:
    """Penalize bloated skills. Full marks if within the word budget."""
    if skill.word_count == 0:
        return 10.0

    if skill.word_count <= profile.max_total_words:
        return 10.0

    ratio = skill.word_count / profile.max_total_words
    if ratio > 3.0:
        return 0.0

    return max(0.0, 10.0 - (ratio - 1.0) * 5.0)
