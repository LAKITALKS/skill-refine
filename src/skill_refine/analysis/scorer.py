"""Rule-based and optional LLM-based scoring for skill files.

Each sub-score is 0.0–10.0. The total is a weighted average of sub-scores,
also on a 0–10 scale. Weights are defined in config.SCORE_WEIGHTS.

The optional llm_score is independent and shown separately.
"""

from __future__ import annotations

from skill_refine.core.config import (
    EXPECTED_SECTIONS,
    MAX_SECTION_WORDS,
    MAX_TOTAL_WORDS,
    RECOMMENDED_FRONTMATTER_FIELDS,
    SCORE_WEIGHTS,
)
from skill_refine.core.models import ScoreCard, Skill
from skill_refine.core.sections import find_section, has_section
from skill_refine.providers.base import BaseProvider


def compute_score(
    skill: Skill,
    *,
    llm: bool = False,
    provider: BaseProvider | None = None,
    provider_name: str | None = None,
) -> ScoreCard:
    """Compute a rule-based score for a skill.

    If llm=True and a provider is available, also computes an LLM-based
    quality score (0–10) as a separate data point.
    """
    completeness = _score_completeness(skill)
    structure = _score_structure(skill)
    metadata = _score_metadata(skill)
    conciseness = _score_conciseness(skill)

    total = (
        completeness * SCORE_WEIGHTS["completeness"]
        + structure * SCORE_WEIGHTS["structure"]
        + metadata * SCORE_WEIGHTS["metadata"]
        + conciseness * SCORE_WEIGHTS["conciseness"]
    )

    llm_score = None
    if llm:
        llm_score = _compute_llm_score(
            skill, provider=provider, provider_name=provider_name
        )

    return ScoreCard(
        completeness=round(completeness, 1),
        structure=round(structure, 1),
        metadata=round(metadata, 1),
        conciseness=round(conciseness, 1),
        total=round(total, 1),
        llm_score=round(llm_score, 1) if llm_score is not None else None,
    )


def _score_completeness(skill: Skill) -> float:
    """How many expected sections are present and non-empty."""
    if not EXPECTED_SECTIONS:
        return 10.0

    present = 0
    for name in EXPECTED_SECTIONS:
        sec = find_section(skill.sections, name)
        if sec and sec.content.strip():
            present += 1

    return (present / len(EXPECTED_SECTIONS)) * 10.0


def _score_structure(skill: Skill) -> float:
    """Reward well-structured skills: sections exist, none empty, reasonable sizes."""
    if not skill.sections:
        return 0.0

    score = 10.0

    empty_count = sum(1 for s in skill.sections if not s.content.strip())
    score -= empty_count * 2.0

    oversized_count = sum(1 for s in skill.sections if s.word_count > MAX_SECTION_WORDS)
    score -= oversized_count * 1.5

    if len(skill.sections) < 3:
        score -= 2.0

    return max(0.0, min(10.0, score))


def _score_metadata(skill: Skill) -> float:
    """Score based on frontmatter completeness."""
    if not skill.metadata.raw:
        return 0.0

    present = 0
    for field in RECOMMENDED_FRONTMATTER_FIELDS:
        value = skill.metadata.raw.get(field)
        if value:
            present += 1

    return (present / len(RECOMMENDED_FRONTMATTER_FIELDS)) * 10.0


def _score_conciseness(skill: Skill) -> float:
    """Penalize bloated skills. Full marks if within word budget."""
    if skill.word_count == 0:
        return 10.0

    if skill.word_count <= MAX_TOTAL_WORDS:
        return 10.0

    ratio = skill.word_count / MAX_TOTAL_WORDS
    if ratio > 3.0:
        return 0.0

    return max(0.0, 10.0 - (ratio - 1.0) * 5.0)


_LLM_SCORE_SYSTEM = """\
You are a skill-file quality assessor. Rate the overall quality of the \
given skill file on a scale from 0 to 10.

Criteria:
- Clarity: Is the skill easy to understand?
- Completeness: Does it cover when/how/why to apply?
- Structure: Is it well-organized with appropriate sections?
- Safety: Does it include warnings and boundary conditions?
- Actionability: Can someone follow the steps?

Return ONLY a single number between 0 and 10 (may include one decimal).
No commentary, no explanation.
"""


def _compute_llm_score(
    skill: Skill,
    *,
    provider: BaseProvider | None = None,
    provider_name: str | None = None,
) -> float | None:
    """Ask an LLM to rate the skill. Returns 0–10 or None on failure."""
    try:
        from skill_refine.core.llm import call_llm

        response = call_llm(
            f"Rate this skill file:\n\n{skill.raw_content}",
            system=_LLM_SCORE_SYSTEM,
            provider=provider,
            provider_name=provider_name,
            max_tokens=16,
            temperature=0.0,
        )
        score = float(response.text.strip())
        return max(0.0, min(10.0, score))
    except Exception:
        return None
