"""Profile-driven, rule-based checker for skill files.

Part of the offline, deterministic lint core: no LLM/provider/network imports.
"""

from __future__ import annotations

from skill_refine.lint.models import Finding, Severity, Skill
from skill_refine.lint.profiles import Profile
from skill_refine.lint.sections import find_section, has_section, is_empty_section
from skill_refine.lint.tokens import count_words


def run_checks(skill: Skill, profile: Profile) -> list[Finding]:
    """Run all rule-based checks on a skill and return findings."""
    findings: list[Finding] = []
    findings.extend(_check_frontmatter(skill, profile))
    findings.extend(_check_sections(skill, profile))
    findings.extend(_check_content_quality(skill, profile))
    return findings


def _check_frontmatter(skill: Skill, profile: Profile) -> list[Finding]:
    findings: list[Finding] = []

    if not skill.metadata.raw:
        findings.append(
            Finding(
                id="missing-frontmatter",
                message="YAML frontmatter is missing entirely.",
                severity=Severity.ERROR,
            )
        )
        return findings

    for field in profile.required_frontmatter:
        if not skill.metadata.raw.get(field):
            findings.append(
                Finding(
                    id=f"missing-frontmatter-{field}",
                    message=f"Required frontmatter field '{field}' is missing.",
                    severity=Severity.ERROR,
                )
            )

    for field in profile.recommended_frontmatter:
        if field in profile.required_frontmatter:
            continue
        if not skill.metadata.raw.get(field):
            findings.append(
                Finding(
                    id=f"missing-frontmatter-{field}",
                    message=f"Recommended frontmatter field '{field}' is missing.",
                    severity=Severity.WARNING,
                )
            )

    findings.extend(_check_frontmatter_description(skill, profile))
    return findings


def _check_frontmatter_description(skill: Skill, profile: Profile) -> list[Finding]:
    findings: list[Finding] = []
    description = skill.metadata.description.strip()
    if not description:
        return findings

    if profile.min_frontmatter_description_words > 0:
        words = count_words(description)
        if words < profile.min_frontmatter_description_words:
            findings.append(
                Finding(
                    id="short-frontmatter-description",
                    message=(
                        f"Frontmatter description has only {words} words "
                        f"(minimum: {profile.min_frontmatter_description_words}). "
                        "A specific description improves skill triggering."
                    ),
                    severity=Severity.WARNING,
                )
            )

    if (
        profile.max_frontmatter_description_chars > 0
        and len(description) > profile.max_frontmatter_description_chars
    ):
        findings.append(
            Finding(
                id="long-frontmatter-description",
                message=(
                    f"Frontmatter description is {len(description)} characters "
                    f"(recommended max: {profile.max_frontmatter_description_chars})."
                ),
                severity=Severity.INFO,
            )
        )

    return findings


def _check_sections(skill: Skill, profile: Profile) -> list[Finding]:
    findings: list[Finding] = []

    for expected in profile.expected_sections:
        if not has_section(skill.sections, expected):
            findings.append(
                Finding(
                    id="missing-section",
                    message=f"Section '## {expected.title()}' is missing.",
                    severity=Severity.WARNING,
                    section=expected,
                )
            )

    for i, section in enumerate(skill.sections):
        if is_empty_section(skill.sections, i):
            findings.append(
                Finding(
                    id="empty-section",
                    message=f"Section '## {section.heading}' is empty.",
                    severity=Severity.WARNING,
                    section=section.heading.lower(),
                )
            )

        if section.word_count > profile.max_section_words:
            findings.append(
                Finding(
                    id="long-section",
                    message=(
                        f"Section '## {section.heading}' has {section.word_count} words "
                        f"(threshold: {profile.max_section_words})."
                    ),
                    severity=Severity.INFO,
                    section=section.heading.lower(),
                )
            )

    if profile.min_description_words > 0:
        desc_section = find_section(skill.sections, "description")
        if desc_section and desc_section.word_count < profile.min_description_words:
            findings.append(
                Finding(
                    id="short-description",
                    message=(
                        f"Description section has only {desc_section.word_count} words "
                        f"(minimum: {profile.min_description_words})."
                    ),
                    severity=Severity.WARNING,
                    section="description",
                )
            )

    return findings


def _check_content_quality(skill: Skill, profile: Profile) -> list[Finding]:
    findings: list[Finding] = []

    paragraphs = skill.body.split("\n\n")
    for i, para in enumerate(paragraphs, 1):
        para_stripped = para.strip()
        if not para_stripped or para_stripped.startswith("#"):
            continue
        wc = count_words(para_stripped)
        if wc > profile.max_paragraph_words:
            findings.append(
                Finding(
                    id="long-paragraph",
                    message=(
                        f"Paragraph {i} has {wc} words "
                        f"(threshold: {profile.max_paragraph_words})."
                    ),
                    severity=Severity.INFO,
                )
            )

    return findings
