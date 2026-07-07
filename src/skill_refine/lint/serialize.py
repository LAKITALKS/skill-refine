"""Stable, machine-readable serialization of lint results.

The JSON output is a documented, versioned contract (``schema_version``). Both
``check --json`` and ``report --format json`` use :func:`render_json`, so there
is exactly one JSON shape.

Part of the offline, deterministic lint core: no LLM/provider/network imports.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from skill_refine.lint.models import Severity, SkillReport
from skill_refine.lint.smells import SMELL_MESSAGES

SCHEMA_VERSION = "2.0"


def _verdict(total: float) -> str:
    if total >= 8.0:
        return "Solid — skill is well-structured and complete."
    if total >= 5.0:
        return "Acceptable — has room for improvement."
    return "Needs work — significant gaps in structure or content."


def _skill_dict(report: SkillReport) -> dict:
    sk = report.skill
    return {
        "path": str(sk.path),
        "name": report.name,
        "format": report.skill_format,
        "skill_dir": report.skill_dir,
        "word_count": sk.word_count,
        "estimated_tokens": sk.estimated_tokens,
        "score": {
            "total": report.score.total,
            "components": {
                "completeness": report.score.completeness,
                "structure": report.score.structure,
                "metadata": report.score.metadata,
                "conciseness": report.score.conciseness,
            },
        },
        "findings": [
            {
                "id": f.id,
                "severity": f.severity.value,
                "message": f.message,
                "section": f.section,
            }
            for f in report.findings
        ],
        "smells": [
            {"id": s.value, "message": SMELL_MESSAGES.get(s.value, "")}
            for s in report.smells
        ],
        "verdict": _verdict(report.score.total),
    }


def build_document(
    reports: list[SkillReport],
    *,
    profile: str,
    tool_version: str,
    generated_at: str | None = None,
) -> dict:
    """Build the versioned result document as a plain dict."""
    skills = [_skill_dict(r) for r in reports]

    severity_counts = {level.value: 0 for level in Severity}
    smell_count = 0
    for r in reports:
        for f in r.findings:
            severity_counts[f.severity.value] += 1
        smell_count += len(r.smells)

    scores = [r.score.total for r in reports]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "skill-refine",
        "tool_version": tool_version,
        "profile": profile,
        "generated_at": generated_at
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "skills": skills,
        "summary": {
            "skill_count": len(reports),
            "avg_score": avg_score,
            "counts": {
                "error": severity_counts["error"],
                "warning": severity_counts["warning"],
                "info": severity_counts["info"],
                "smell": smell_count,
            },
        },
    }


def render_json(
    reports: list[SkillReport],
    *,
    profile: str,
    tool_version: str,
    generated_at: str | None = None,
) -> str:
    """Render the versioned JSON contract (schema_version = ``2.0``)."""
    document = build_document(
        reports,
        profile=profile,
        tool_version=tool_version,
        generated_at=generated_at,
    )
    return json.dumps(document, indent=2, ensure_ascii=False)


def render_markdown(reports: list[SkillReport], *, profile: str) -> str:
    """Render a human-readable Markdown report."""
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines.append("# Skill Report")
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append(f"Profile: `{profile}`")
    lines.append("")

    if len(reports) > 1:
        lines.extend(_md_summary_table(reports))
        lines.append("")

    for r in reports:
        lines.extend(_md_single(r))
        lines.append("")

    return "\n".join(lines)


def _md_summary_table(reports: list[SkillReport]) -> list[str]:
    lines = [
        "## Summary",
        "",
        "| Skill | Format | Score | Findings | Smells | Words |",
        "|-------|--------|------:|---------:|-------:|------:|",
    ]
    for r in sorted(reports, key=lambda r: r.score.total):
        lines.append(
            f"| {r.name} | {r.skill_format} "
            f"| {r.score.total}/10 | {len(r.findings)} "
            f"| {len(r.smells)} | {r.skill.word_count} |"
        )
    return lines


def _md_single(r: SkillReport) -> list[str]:
    lines: list[str] = []
    sc = r.score

    lines.append(f"## {r.name}")
    lines.append("")
    lines.append(f"- **File:** `{r.skill.path}`")
    lines.append(f"- **Format:** {r.skill_format}")
    lines.append(f"- **Words:** {r.skill.word_count}")
    lines.append(f"- **Tokens (est.):** ~{r.skill.estimated_tokens}")
    lines.append(f"- **Score:** {sc.total}/10")
    lines.append("")

    lines.append("### Scores")
    lines.append("")
    lines.append("| Category | Score |")
    lines.append("|----------|------:|")
    lines.append(f"| Completeness | {sc.completeness}/10 |")
    lines.append(f"| Structure | {sc.structure}/10 |")
    lines.append(f"| Metadata | {sc.metadata}/10 |")
    lines.append(f"| Conciseness | {sc.conciseness}/10 |")
    lines.append(f"| **Total** | **{sc.total}/10** |")
    lines.append("")

    if r.skill.sections:
        lines.append("### Sections")
        lines.append("")
        for sec in r.skill.sections:
            empty_tag = " *(empty)*" if not sec.content.strip() else ""
            lines.append(f"- `## {sec.heading}` — {sec.word_count} words{empty_tag}")
        lines.append("")

    if r.findings:
        lines.append("### Findings")
        lines.append("")
        for f in r.findings:
            lines.append(f"- **{f.severity.value.upper()}** `{f.id}` — {f.message}")
        lines.append("")

    if r.smells:
        lines.append("### Smells")
        lines.append("")
        for s in r.smells:
            lines.append(f"- `{s.value}` — {SMELL_MESSAGES.get(s.value, '')}")
        lines.append("")

    lines.append("### Verdict")
    lines.append("")
    lines.append(f"> {_verdict(sc.total)}")
    lines.append("")

    return lines
