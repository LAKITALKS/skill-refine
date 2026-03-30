"""CLI check command for skill-refine."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from skill_refine.analysis.checker import run_checks
from skill_refine.analysis.scorer import compute_score
from skill_refine.analysis.smells import detect_smells
from skill_refine.core.models import Severity, SkillReport
from skill_refine.core.parser import parse_skill

console = Console()

_SMELL_DESCRIPTIONS: dict[str, str] = {
    "VAGUE_TRIGGER": "Trigger condition uses imprecise language",
    "NO_WARNINGS": "No warnings or caveats defined",
    "NO_FAILURE_CASES": "No negative cases (When not to apply)",
    "TOKEN_BLOAT": "Skill exceeds reasonable token budget",
    "NO_INPUTS_OUTPUTS": "Inputs/Outputs not specified",
    "NO_BOUNDARIES": "No application boundaries defined",
    "WALL_OF_TEXT": "Oversized paragraphs without structure",
    "EMPTY_FRONTMATTER": "YAML frontmatter missing entirely",
}


def check(
    path: Path = typer.Argument(
        ..., help="Path to a skill file (.md) or directory containing skill files.",
        exists=True,
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed output."),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Check skill files for completeness, structure, and smells."""
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

    if output_json:
        _print_json(reports)
    elif len(reports) == 1:
        _print_single(reports[0], verbose)
    else:
        _print_summary_table(reports)
        if verbose:
            for report in sorted(reports, key=lambda r: r.score.total):
                console.print()
                _print_single(report, verbose=True)


def _resolve_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix == ".md" else []
    return list(path.glob("*.md"))


def _score_color(score: float) -> str:
    if score >= 7.0:
        return "green"
    if score >= 4.0:
        return "yellow"
    return "red"


def _score_bar(score: float, width: int = 20) -> Text:
    """Render a visual score bar like ████████░░░░░░░░░░░░ 6.5/10."""
    filled = int(score / 10.0 * width)
    empty = width - filled
    color = _score_color(score)
    bar = Text()
    bar.append("█" * filled, style=color)
    bar.append("░" * empty, style="dim")
    bar.append(f" {score}/10", style=f"bold {color}")
    return bar


def _severity_style(severity: Severity) -> str:
    return {"error": "red bold", "warning": "yellow", "info": "dim"}[severity.value]


def _severity_icon(severity: Severity) -> str:
    return {"error": "✗", "warning": "!", "info": "·"}[severity.value]


def _print_single(report: SkillReport, verbose: bool) -> None:
    sc = report.score
    color = _score_color(sc.total)
    name = report.skill.metadata.name or report.skill.path.name
    section_count = len(report.skill.sections)

    # Header panel
    console.print(
        Panel(
            f"[bold]{name}[/bold]\n"
            f"[dim]{report.skill.path}[/dim]",
            title="[bold]Skill Check[/bold]",
            subtitle=f"[{color}]{sc.total}/10[/{color}]",
            border_style=color,
        )
    )

    # Stats line
    console.print(
        f"  [dim]Words:[/dim] {report.skill.word_count}   "
        f"[dim]Tokens (est.):[/dim] ~{report.skill.estimated_tokens}   "
        f"[dim]Sections:[/dim] {section_count}   "
        f"[dim]Findings:[/dim] {len(report.findings)}   "
        f"[dim]Smells:[/dim] {len(report.smells)}"
    )
    console.print()

    # Sub-scores with bars
    score_table = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    score_table.add_column("Category", style="bold", width=16)
    score_table.add_column("Bar", no_wrap=True)
    for label, value in [
        ("Completeness", sc.completeness),
        ("Structure", sc.structure),
        ("Metadata", sc.metadata),
        ("Conciseness", sc.conciseness),
    ]:
        score_table.add_row(label, _score_bar(value))
    console.print(score_table)
    console.print()

    # Findings
    errors = [f for f in report.findings if f.severity == Severity.ERROR]
    warnings = [f for f in report.findings if f.severity == Severity.WARNING]
    infos = [f for f in report.findings if f.severity == Severity.INFO]

    if errors or warnings or (verbose and infos):
        console.print("[bold]Findings[/bold]")
        for f in errors + warnings + (infos if verbose else []):
            style = _severity_style(f.severity)
            icon = _severity_icon(f.severity)
            console.print(f"  [{style}]{icon} {f.severity.value.upper():7s}[/{style}]  {f.message}")
        if infos and not verbose:
            console.print(f"  [dim]  … +{len(infos)} info (use --verbose)[/dim]")
        console.print()

    # Smells
    if report.smells:
        console.print("[bold]Smells[/bold]")
        for smell in report.smells:
            desc = _SMELL_DESCRIPTIONS.get(smell.value, "")
            console.print(f"  [magenta]⚠ {smell.value}[/magenta]  [dim]{desc}[/dim]")
        console.print()

    # Verbose: section listing
    if verbose and report.skill.sections:
        console.print("[bold]Sections[/bold]")
        for sec in report.skill.sections:
            wc_color = "red" if sec.word_count > 500 else ("yellow" if sec.word_count > 300 else "dim")
            empty_tag = " [red](empty)[/red]" if not sec.content.strip() else ""
            console.print(
                f"  [bold]##[/bold] {sec.heading}  [{wc_color}]{sec.word_count} words[/{wc_color}]{empty_tag}"
            )
        console.print()

    # Verdict
    if sc.total >= 8.0:
        console.print("[green]→ Skill looks solid.[/green]")
    elif sc.total >= 5.0:
        console.print("[yellow]→ Skill has room for improvement.[/yellow]")
    else:
        console.print("[red]→ Skill needs significant work.[/red]")


def _print_summary_table(reports: list[SkillReport]) -> None:
    # Sort weakest first
    reports_sorted = sorted(reports, key=lambda r: r.score.total)

    table = Table(title="Skill Check Summary", title_style="bold")
    table.add_column("#", style="dim", width=3)
    table.add_column("File", style="bold")
    table.add_column("Name", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Findings", justify="right")
    table.add_column("Smells", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Tokens (est.)", justify="right", style="dim")

    for i, r in enumerate(reports_sorted, 1):
        color = _score_color(r.score.total)
        name = r.skill.metadata.name or "—"
        table.add_row(
            str(i),
            r.skill.path.name,
            name,
            f"[{color}]{r.score.total}/10[/{color}]",
            str(len(r.findings)),
            str(len(r.smells)),
            str(r.skill.word_count),
            f"~{r.skill.estimated_tokens}",
        )
    console.print(table)

    # Summary stats
    scores = [r.score.total for r in reports_sorted]
    avg = sum(scores) / len(scores)
    avg_color = _score_color(avg)
    console.print(
        f"\n  [dim]Files:[/dim] {len(reports)}   "
        f"[dim]Avg score:[/dim] [{avg_color}]{avg:.1f}/10[/{avg_color}]   "
        f"[dim]Weakest:[/dim] [{_score_color(scores[0])}]{reports_sorted[0].skill.path.name}[/{_score_color(scores[0])}]"
    )


def _print_json(reports: list[SkillReport]) -> None:
    data = []
    for r in reports:
        data.append({
            "file": str(r.skill.path),
            "name": r.skill.metadata.name,
            "word_count": r.skill.word_count,
            "estimated_tokens": r.skill.estimated_tokens,
            "score": {
                "total": r.score.total,
                "completeness": r.score.completeness,
                "structure": r.score.structure,
                "metadata": r.score.metadata,
                "conciseness": r.score.conciseness,
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
        })

    console.print_json(json.dumps(data, indent=2))
