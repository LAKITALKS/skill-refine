"""Guard: validate rewrite results before writing to disk."""

from __future__ import annotations

import frontmatter

from skill_refine.core.config import EXPECTED_SECTIONS
from skill_refine.core.models import (
    GuardResult,
    GuardWarning,
    Severity,
    Skill,
)
from skill_refine.core.sections import extract_sections, has_section
from skill_refine.core.tokens import estimate_tokens


def check_rewrite(original: Skill, rewritten_content: str) -> GuardResult:
    """Validate a rewritten skill before it gets written to disk.

    Checks:
    - Not empty
    - Valid Markdown with parseable frontmatter
    - Frontmatter not destroyed
    - Token ratio within bounds (70%–130%)
    - Required sections not removed
    """
    warnings: list[GuardWarning] = []

    # 1. Not empty
    if not rewritten_content.strip():
        return GuardResult(
            passed=False,
            blocked=True,
            block_reason="Rewritten content is empty.",
        )

    # 2. Frontmatter parseable
    try:
        post = frontmatter.loads(rewritten_content)
    except Exception:
        return GuardResult(
            passed=False,
            blocked=True,
            block_reason="Rewritten content has invalid YAML frontmatter.",
        )

    # 3. Frontmatter not destroyed (if original had it)
    if original.metadata.raw and not post.metadata:
        warnings.append(
            GuardWarning(
                code="frontmatter-lost",
                message="Original had YAML frontmatter, but rewrite removed it.",
                severity=Severity.ERROR,
            )
        )

    # 4. Token ratio
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

    # 5. Required sections not removed
    body = post.content
    new_sections = extract_sections(body)
    for section_name in EXPECTED_SECTIONS:
        had_it = has_section(original.sections, section_name)
        still_has = has_section(new_sections, section_name)
        if had_it and not still_has:
            warnings.append(
                GuardWarning(
                    code="section-removed",
                    message=f"Section '## {section_name.title()}' was present but removed by rewrite.",
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
