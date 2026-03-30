"""Generate missing sections for a skill file via LLM."""

from __future__ import annotations

from skill_refine.core.config import EXPECTED_SECTIONS
from skill_refine.core.llm import call_llm
from skill_refine.core.models import Skill
from skill_refine.core.sections import has_section
from skill_refine.providers.base import BaseProvider

SYSTEM_PROMPT = """\
You are a precise skill-file editor. You generate missing sections for \
skill files (Markdown with YAML frontmatter).

Rules:
- Return ONLY the generated sections, each starting with ## heading.
- Do NOT return the full file, only the new sections.
- Do NOT wrap output in code fences.
- Base content on what exists in the skill. Do NOT invent facts.
- Keep sections concise and actionable.
- Use bullet points or numbered lists where appropriate.
"""


def find_missing_sections(skill: Skill) -> list[str]:
    """Return list of expected section names missing from the skill."""
    return [
        name for name in EXPECTED_SECTIONS
        if not has_section(skill.sections, name)
    ]


def generate_sections(
    skill: Skill,
    section_names: list[str] | None = None,
    *,
    provider: BaseProvider | None = None,
    provider_name: str | None = None,
) -> str:
    """Generate content for missing sections.

    If section_names is None, generates all missing sections.
    Returns Markdown text with ## headings for each generated section.
    """
    if section_names is None:
        section_names = find_missing_sections(skill)

    if not section_names:
        return ""

    sections_list = "\n".join(f"- ## {name.title()}" for name in section_names)

    prompt = f"""\
## Task

Generate the following missing sections for this skill file.

## Sections to generate

{sections_list}

## Existing skill file

{skill.raw_content}

## Instructions

Return ONLY the generated sections, each starting with a ## heading.
Do NOT include sections that already exist.
Do NOT wrap in code fences.
Base your content on what already exists in the skill. Be precise.
"""

    response = call_llm(
        prompt,
        system=SYSTEM_PROMPT,
        provider=provider,
        provider_name=provider_name,
        max_tokens=4096,
        temperature=0.3,
    )

    return _clean_response(response.text)


def _clean_response(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.index("\n") if "\n" in text else len(text)
        text = text[first_newline + 1:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip() + "\n"
