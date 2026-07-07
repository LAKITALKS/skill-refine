"""LLM-based skill rewriter with multiple modes."""

from __future__ import annotations

from skill_refine.lint.models import Finding, Skill, SmellType
from skill_refine.llm.client import call_llm
from skill_refine.llm.models import RewriteMode
from skill_refine.llm.providers.base import BaseProvider

_MODE_INSTRUCTIONS: dict[RewriteMode, str] = {
    RewriteMode.CLARITY: (
        "Focus on making the skill clearer and easier to understand. "
        "Improve descriptions, make trigger conditions more precise, "
        "and clarify ambiguous language."
    ),
    RewriteMode.COMPACT: (
        "Focus on making the skill more concise without losing information. "
        "Remove redundancy, tighten phrasing, merge overlapping sections."
    ),
    RewriteMode.ROBUSTNESS: (
        "Focus on making the skill more robust. "
        "Add missing warnings, failure cases, edge cases, and boundary conditions. "
        "Add 'When not to apply' if missing."
    ),
    RewriteMode.STRUCTURE: (
        "Focus on improving the structure. "
        "Add missing sections (Description, When to apply, When not to apply, "
        "Warnings, Inputs, Outputs, Steps, Examples). "
        "Ensure proper ## heading hierarchy."
    ),
    RewriteMode.SAFETY: (
        "Focus on safety aspects. "
        "Add or improve Warnings section, add failure cases, "
        "make boundary conditions explicit, add 'When not to apply'."
    ),
    RewriteMode.ALL: (
        "Perform a comprehensive improvement: "
        "improve clarity, structure, robustness, conciseness, and safety. "
        "Add any missing sections. Fix all identified issues."
    ),
}

SYSTEM_PROMPT = """\
You are a precise skill-file editor. You receive a skill file (Markdown with \
YAML frontmatter) and a list of findings/smells from a static analyzer.

Your job:
- Return ONLY the improved skill file (complete Markdown with YAML frontmatter).
- Do NOT wrap the output in code fences or add any commentary.
- Preserve the author's voice and intent.
- Do NOT invent facts, URLs, or tool names that are not in the original.
- Do NOT remove sections that already exist unless they are truly redundant.
- Keep frontmatter fields that already exist; add missing recommended fields.
- If adding new sections, use ## level headings.
- Be precise and deterministic. Do not hallucinate content.
"""


def rewrite_skill(
    skill: Skill,
    findings: list[Finding],
    smells: list[SmellType],
    *,
    mode: RewriteMode = RewriteMode.ALL,
    provider: BaseProvider | None = None,
    provider_name: str | None = None,
) -> str:
    """Rewrite a skill file using an LLM.

    Returns the full rewritten Markdown content (including frontmatter).
    """
    prompt = _build_prompt(skill, findings, smells, mode)

    response = call_llm(
        prompt,
        system=SYSTEM_PROMPT,
        provider=provider,
        provider_name=provider_name,
        max_tokens=8192,
        temperature=0.3,
    )

    return _clean_response(response.text)


def _build_prompt(
    skill: Skill,
    findings: list[Finding],
    smells: list[SmellType],
    mode: RewriteMode,
) -> str:
    mode_instruction = _MODE_INSTRUCTIONS[mode]

    findings_text = (
        "\n".join(f"- [{f.severity.value.upper()}] {f.message}" for f in findings)
        or "- No findings."
    )

    smells_text = "\n".join(f"- {s.value}" for s in smells) or "- No smells."

    return f"""\
## Task

Improve this skill file according to the mode below.

## Mode: {mode.value}

{mode_instruction}

## Findings from static analysis

{findings_text}

## Smells detected

{smells_text}

## Original skill file

{skill.raw_content}

## Instructions

Return the complete improved skill file. Include YAML frontmatter and all sections.
Do NOT add code fences or commentary around your output.
"""


def _clean_response(text: str) -> str:
    """Strip code fences if the LLM wrapped the output."""
    text = text.strip()

    if text.startswith("```"):
        first_newline = text.index("\n") if "\n" in text else len(text)
        text = text[first_newline + 1 :]
    if text.endswith("```"):
        text = text[:-3]

    return text.strip() + "\n"
