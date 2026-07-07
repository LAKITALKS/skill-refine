"""Guard: validate rewrite results before writing to disk.

Depends only on the offline lint core (plus ``frontmatter``); it needs no
network access itself, but lives in the LLM layer because it only makes sense
when validating LLM-produced rewrites.
"""

from __future__ import annotations

import frontmatter

from skill_refine.lint.models import Skill
from skill_refine.lint.profiles import Profile
from skill_refine.lint.sections import extract_sections, has_section
from skill_refine.lint.tokens import estimate_tokens
from skill_refine.llm.models import GuardResult, GuardWarning, Severity


def check_rewrite(
    original: Skill, rewritten_content: str, profile: Profile
) -> GuardResult:
    """Validate a rewritten skill before it gets written to disk.

    Checks:
    - Not empty
    - Valid Markdown with parseable frontmatter
    - Frontmatter not destroyed
    - Token ratio within bounds (70%-130%)
    - Sections expected by the profile that existed are not removed
    """
    warnings: list[GuardWarning] = []

    if not rewritten_content.strip():
        return GuardResult(
            passed=False,
            blocked=True,
            block_reason="Rewritten content is empty.",
        )

    try:
        post = frontmatter.loads(rewritten_content)
    except Exception:
        return GuardResult(
            passed=False,
            blocked=True,
            block_reason="Rewritten content has invalid YAML frontmatter.",
        )

    if original.metadata.raw and not post.metadata:
        warnings.append(
            GuardWarning(
                code="frontmatter-lost",
                message="Original had YAML frontmatter, but rewrite removed it.",
                severity=Severity.ERROR,
            )
        )

    new_tokens = estimate_tokens(rewritten_content)
    if original.estimated_tokens > 0:
        ratio = new_tokens / original.estimated_tokens
        if ratio < 0.70:
            warnings.append(
                GuardWarning(
                    code="token-shrink",
                    message=(
                        f"Rewrite is ~{ratio:.0%} of original token count "
                        f"({new_tokens} vs ~{original.estimated_tokens} est.). "
                        "Significant content may have been lost."
                    ),
                    severity=Severity.WARNING,
                )
            )
        elif ratio > 1.30:
            warnings.append(
                GuardWarning(
                    code="token-bloat",
                    message=(
                        f"Rewrite is ~{ratio:.0%} of original token count "
                        f"({new_tokens} vs ~{original.estimated_tokens} est.). "
                        "May contain unnecessary additions."
                    ),
                    severity=Severity.WARNING,
                )
            )

    body = post.content
    new_sections = extract_sections(body)
    for section_name in profile.expected_sections:
        had_it = has_section(original.sections, section_name)
        still_has = has_section(new_sections, section_name)
        if had_it and not still_has:
            warnings.append(
                GuardWarning(
                    code="section-removed",
                    message=(
                        f"Section '## {section_name.title()}' was present but "
                        "removed by rewrite."
                    ),
                    severity=Severity.WARNING,
                )
            )

    has_blockers = any(w.severity == Severity.ERROR for w in warnings)

    return GuardResult(
        passed=not has_blockers,
        warnings=warnings,
        blocked=has_blockers,
        block_reason="Critical guard warnings detected." if has_blockers else "",
    )
