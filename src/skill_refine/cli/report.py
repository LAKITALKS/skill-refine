"""CLI report command for skill-refine."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console

from skill_refine.analysis.checker import run_checks
from skill_refine.analysis.scorer import compute_score
from skill_refine.analysis.smells import detect_smells
from skill_refine.core.models import Severity, SkillReport
from skill_refine.core.parser import parse_skill

console = Console()


class ReportFormat(str, Enum):
    JSON = "json"
    MD = "md"


def report(
    path: Path = typer.Argument(
        ..., help="Path to a skill file (.md) or directory.",
        exists=True,
    ),
    fmt: ReportFormat = typer.Option(
        ReportFormat.MD, "--format", "-f", help="Output format.",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Write report to file instead of stdout.",
    ),
) -> None:
    """Generate a detailed report for skill files."""
    files = _resolve_files(path)

    if not files:
        console.print("[red]No .md files found.[/red]")
        raise typer.Exit(1)

    reports: list[SkillReport] = []
    for file in sorted(files):
        try:
            skill = parse_skill(file)
            findings = run_checks(skill)
            smells = detect_smells(skill)
            score = compute_score(skill)
            reports.append(
                SkillReport(skill=skill, findings=findings, smells=smells, score=score)
            )
        except Exception as e:
            console.print(f"[red]Error parsing {file}: {e}[/red]")

    if not reports:
        raise typer.Exit(1)

    if fmt == ReportFormat.JSON:
        content = _render_json(reports)
    else:
        content = _render_markdown(reports)

    if output:
        output.write_text(content, encoding="utf-8")
        console.print(f"[green]Report written to:[/green] {output}")
    else:
        console.print(content, highlight=False)


def _resolve_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix == ".md" else []
    return list(path.glob("*.md"))


def _verdict(total: float) -> str:
    if total >= 8.0:
        return "Solid — skill is well-structured and complete."
    if total >= 5.0:
        return "Acceptable — has room for improvement."
    return "Needs work — significant gaps in structure or content."


# --- JSON ---

def _render_json(reports: list[SkillReport]) -> str:
    data = []
    for r in reports:
        data.append({
            "file": str(r.skill.path),
            "name": r.skill.metadata.name or None,
            "word_count": r.skill.word_count,
            "estimated_tokens": r.skill.estimated_tokens,
            "score": {
                "total": r.score.total,
                "completeness": r.score.completeness,
                "structure": r.score.structure,
                "metadata": r.score.metadata,
                "conciseness": r.score.conciseness,
                "llm_score": r.score.llm_score,
            },
            "findings": [
                {
                    "rule": f.rule,
                    "message": f.message,
                    "severity": f.severity.value,
                    "section": f.section,
                }
                for f in r.findings
            ],
            "smells": [s.value for s in r.smells],
            "sections": [
                {
                    "heading": s.heading,
                    "level": s.level,
                    "word_count": s.word_count,
                    "empty": not s.content.strip(),
                }
                for s in r.skill.sections
            ],
            "verdict": _verdict(r.score.total),
        })
    return json.dumps(data, indent=2, ensure_ascii=False)


# --- Markdown ---

def _render_markdown(reports: list[SkillReport]) -> str:
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines.append(f"# Skill Report")
    lines.append(f"")
    lines.append(f"Generated: {now}")
    lines.append(f"")

    if len(reports) > 1:
        lines.extend(_render_md_summary_table(reports))
        lines.append("")

    for r in reports:
        lines.extend(_render_md_single(r))
        lines.append("")

    return "\n".join(lines)


def _render_md_summary_table(reports: list[SkillReport]) -> list[str]:
    lines = [
        "## Summary",
        "",
        "| File | Name | Score | Findings | Smells | Words |",
        "|------|------|------:|--------:|-------:|------:|",
    ]
    for r in sorted(reports, key=lambda r: r.score.total):
        name = r.skill.metadata.name or "—"
        lines.append(
            f"| {r.skill.path.name} | {name} "
            f"| {r.score.total}/10 | {len(r.findings)} "
            f"| {len(r.smells)} | {r.skill.word_count} |"
        )
    return lines


def _render_md_single(r: SkillReport) -> list[str]:
    lines: list[str] = []
    name = r.skill.metadata.name or r.skill.path.name
    sc = r.score

    lines.append(f"## {name}")
    lines.append(f"")
    lines.append(f"- **File:** `{r.skill.path}`")
    lines.append(f"- **Words:** {r.skill.word_count}")
    lines.append(f"- **Tokens (est.):** ~{r.skill.estimated_tokens}")
    lines.append(f"- **Score:** {sc.total}/10")
    if sc.llm_score is not None:
        lines.append(f"- **LLM Score:** {sc.llm_score}/10")
    lines.append(f"")

    # Sub-scores
    lines.append(f"### Scores")
    lines.append(f"")
    lines.append(f"| Category | Score |")
    lines.append(f"|----------|------:|")
    lines.append(f"| Completeness | {sc.completeness}/10 |")
    lines.append(f"| Structure | {sc.structure}/10 |")
    lines.append(f"| Metadata | {sc.metadata}/10 |")
    lines.append(f"| Conciseness | {sc.conciseness}/10 |")
    lines.append(f"| **Total** | **{sc.total}/10** |")
    lines.append(f"")

    # Sections
    if r.skill.sections:
        lines.append(f"### Sections")
        lines.append(f"")
        for sec in r.skill.sections:
            empty_tag = " *(empty)*" if not sec.content.strip() else ""
            lines.append(f"- `## {sec.heading}` — {sec.word_count} words{empty_tag}")
        lines.append(f"")

    # Findings
    if r.findings:
        lines.append(f"### Findings")
        lines.append(f"")
        for f in r.findings:
            icon = {"error": "!!!", "warning": "!!", "info": "."}[f.severity.value]
            lines.append(f"- **{f.severity.value.upper()}** {f.message}")
        lines.append(f"")

    # Smells
    if r.smells:
        lines.append(f"### Smells")
        lines.append(f"")
        for s in r.smells:
            lines.append(f"- `{s.value}`")
        lines.append(f"")

    # Verdict
    lines.append(f"### Verdict")
    lines.append(f"")
    lines.append(f"> {_verdict(sc.total)}")
    lines.append(f"")

    return lines
