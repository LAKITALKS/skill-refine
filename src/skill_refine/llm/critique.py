"""Optional LLM-based quality critique.

This is deliberately separate from the deterministic lint scorer: it lives in
the optional LLM layer and returns a single 0-10 number as an independent data
point, never mixed into the offline ScoreCard.
"""

from __future__ import annotations

from skill_refine.lint.models import Skill
from skill_refine.llm.client import call_llm
from skill_refine.llm.providers.base import BaseProvider

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


def compute_llm_score(
    skill: Skill,
    *,
    provider: BaseProvider | None = None,
    provider_name: str | None = None,
) -> float | None:
    """Ask an LLM to rate the skill. Returns 0-10 or None on failure."""
    try:
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
