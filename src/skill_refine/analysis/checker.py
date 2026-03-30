"""Rule-based checker for skill files."""

from __future__ import annotations

from skill_refine.core.config import (
    EXPECTED_SECTIONS,
    MAX_PARAGRAPH_WORDS,
    MAX_SECTION_WORDS,
    MIN_DESCRIPTION_WORDS,
)
from skill_refine.core.models import Finding, Severity, Skill
from skill_refine.core.sections import find_section, has_section
from skill_refine.core.tokens import count_words


def run_checks(skill: Skill) -> list[Finding]:
    """Run all rule-based checks on a skill and return findings."""
    findings: list[Finding] = []
    findings.extend(_check_frontmatter(skill))
    findings.extend(_check_sections(skill))
    findings.extend(_check_content_quality(skill))
    return findings


def _check_frontmatter(skill: Skill) -> list[Finding]:
    findings: list[Finding] = []

    if not skill.metadata.raw:
        findings.append(
            Finding(
                rule="missing-frontmatter",
                message="YAML frontmatter is missing entirely.",
                severity=Severity.ERROR,
            )
        )
        return findings

    if not skill.metadata.name:
        findings.append(
            Finding(
                rule="missing-name",
                message="Frontmatter field 'name' is missing.",
                severity=Severity.WARNING,
            )
        )

    if not skill.metadata.description:
        findings.append(
            Finding(
                rule="missing-meta-description",
                message="Frontmatter field 'description' is missing.",
                severity=Severity.WARNING,
            )
        )

    if not skill.metadata.tags:
        findings.append(
            Finding(
                rule="missing-tags",
                message="No tags defined in frontmatter.",
                severity=Severity.WARNING,
            )
        )

    return findings


def _check_sections(skill: Skill) -> list[Finding]:
    findings: list[Finding] = []

    for expected in EXPECTED_SECTIONS:
        if not has_section(skill.sections, expected):
            findings.append(
                Finding(
                    rule="missing-section",
                    message=f"Section '## {expected.title()}' is missing.",
                    severity=Severity.WARNING,
                    section=expected,
                )
            )

    for section in skill.sections:
        if not section.content.strip():
            findings.append(
                Finding(
                    rule="empty-section",
                    message=f"Section '## {section.heading}' is empty.",
                    severity=Severity.WARNING,
                    section=section.heading.lower(),
                )
            )

        if section.word_count > MAX_SECTION_WORDS:
            findings.append(
                Finding(
                    rule="long-section",
                    message=(
                        f"Section '## {section.heading}' has {section.word_count} words "
                        f"(threshold: {MAX_SECTION_WORDS})."
                    ),
                    severity=Severity.INFO,
                    section=section.heading.lower(),
                )
            )

    desc_section = find_section(skill.sections, "description")
    if desc_section and desc_section.word_count < MIN_DESCRIPTION_WORDS:
        findings.append(
            Finding(
                rule="short-description",
                message=(
                    f"Description section has only {desc_section.word_count} words "
                    f"(minimum: {MIN_DESCRIPTION_WORDS})."
                ),
                severity=Severity.WARNING,
                section="description",
            )
        )

    return findings


def _check_content_quality(skill: Skill) -> list[Finding]:
    findings: list[Finding] = []

    paragraphs = skill.body.split("\n\n")
    for i, para in enumerate(paragraphs, 1):
        para_stripped = para.strip()
        if not para_stripped or para_stripped.startswith("#"):
            continue
        wc = count_words(para_stripped)
        if wc > MAX_PARAGRAPH_WORDS:
            findings.append(
                Finding(
                    rule="long-paragraph",
                    message=f"Paragraph {i} has {wc} words (threshold: {MAX_PARAGRAPH_WORDS}).",
                    severity=Severity.INFO,
                )
            )

    return findings
