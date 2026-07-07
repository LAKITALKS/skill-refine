"""Selective section patching with boundary confidence.

Uses positional section detection (start/end offsets in the body) rather than
string replacement, so it works correctly even when multiple sections contain
similar text.
"""

from __future__ import annotations

import re

from skill_refine.lint.models import Skill
from skill_refine.lint.sections import find_section
from skill_refine.llm.client import call_llm
from skill_refine.llm.models import BoundaryConfidence, PatchProposal
from skill_refine.llm.providers.base import BaseProvider

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

SYSTEM_PROMPT = """\
You are a precise skill-file section editor. You rewrite a single section \
of a skill file.

Rules:
- Return ONLY the rewritten section content (without the ## heading).
- Do NOT wrap output in code fences or add commentary.
- Preserve the author's intent and voice.
- Be concise and actionable.
- Do NOT invent facts not present in the original skill.
"""


def assess_boundary_confidence(skill: Skill, section_name: str) -> BoundaryConfidence:
    """Assess how confidently we can isolate a section for patching."""
    if not skill.sections:
        return BoundaryConfidence.LOW

    section = find_section(skill.sections, section_name)
    if section is None:
        return BoundaryConfidence.LOW

    headings = _HEADING_RE.findall(skill.body)
    if len(headings) < 2:
        return BoundaryConfidence.MEDIUM

    if section.word_count < 3:
        return BoundaryConfidence.MEDIUM

    return BoundaryConfidence.HIGH


def patch_section(
    skill: Skill,
    section_name: str,
    *,
    provider: BaseProvider | None = None,
    provider_name: str | None = None,
    instruction: str = "",
) -> PatchProposal | None:
    """Rewrite a single section of a skill file.

    Returns a PatchProposal with original and proposed content,
    or None if the section doesn't exist.
    """
    section = find_section(skill.sections, section_name)
    if section is None:
        return None

    confidence = assess_boundary_confidence(skill, section_name)

    extra = f"\nAdditional instruction: {instruction}" if instruction else ""

    prompt = f"""\
## Task

Rewrite the following section of a skill file.

## Section: ## {section.heading}

{section.content}

## Full skill context (read-only)

{skill.raw_content}
{extra}
## Instructions

Return ONLY the improved section content (without the ## heading line).
"""

    response = call_llm(
        prompt,
        system=SYSTEM_PROMPT,
        provider=provider,
        provider_name=provider_name,
        max_tokens=2048,
        temperature=0.3,
    )

    proposed = _clean_response(response.text)

    return PatchProposal(
        section_name=section_name,
        original=section.content,
        proposed=proposed,
        confidence=confidence,
        reason="LLM-rewritten with mode: improve",
    )


def apply_patch(skill: Skill, proposal: PatchProposal) -> str:
    """Apply a PatchProposal to the skill's raw content.

    Uses positional offsets in the body to find the exact section range,
    then reconstructs the full file. If the section cannot be located
    unambiguously, returns the original content unchanged.
    """
    body = skill.body
    span = _find_section_span(body, proposal.section_name)

    if span is None:
        return skill.raw_content

    content_start, content_end = span

    new_body = (
        body[:content_start]
        + "\n\n"
        + proposal.proposed.strip()
        + "\n\n"
        + body[content_end:].lstrip("\n")
    )

    body_start_in_raw = skill.raw_content.find(body)
    if body_start_in_raw == -1:
        return skill.raw_content

    return (
        skill.raw_content[:body_start_in_raw]
        + new_body
        + skill.raw_content[body_start_in_raw + len(body) :]
    )


def _find_section_span(body: str, section_name: str) -> tuple[int, int] | None:
    """Find the content span (start, end) of a section in the body.

    Returns None if the section cannot be found or if multiple sections match
    (ambiguous).
    """
    matches = list(_HEADING_RE.finditer(body))
    if not matches:
        return None

    target = section_name.lower().strip()
    found: list[tuple[int, int]] = []

    for i, match in enumerate(matches):
        heading_text = match.group(2).strip().lower()
        if heading_text == target:
            content_start = match.end()
            content_end = (
                matches[i + 1].start() if i + 1 < len(matches) else len(body)
            )
            found.append((content_start, content_end))

    if len(found) == 1:
        return found[0]

    return None


def _clean_response(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.index("\n") if "\n" in text else len(text)
        text = text[first_newline + 1 :]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
