"""CLI check command for skill-refine."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from skill_refine import __version__
from skill_refine.lint import (
    ProfileError,
    Severity,
    SkillReport,
    analyze,
    load_profile,
    render_json,
)
from skill_refine.lint.sections import is_empty_section
from skill_refine.lint.smells import SMELL_MESSAGES

console = Console()


class FailOn(str, Enum):
    NEVER = "never"
    WARNING = "warning"
    ERROR = "error"


def check(
    path: Path = typer.Argument(
        ...,
        help="Path to a skill file (.md / SKILL.md) or a directory of skills.",
        exists=True,
    ),
    profile_name: str = typer.Option(
        "standard",
        "--profile",
        "-P",
        help="Lint profile: 'standard' (default), 'strict', or a path to a .toml profile.",
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed output."),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    fail_on: FailOn = typer.Option(
        FailOn.NEVER,
        "--fail-on",
        help="Exit non-zero when findings at/above this level exist.",
    ),
) -> None:
    """Check skill files for completeness, structure, and smells."""
    try:
        profile = load_profile(profile_name)
    except ProfileError as e:
        console.print(f"[red]{escape(str(e))}[/red]")
        raise typer.Exit(2)

    reports = analyze(path, profile)

    if not reports:
        console.print("[red]No skill files found (SKILL.md or *.md).[/red]")
        raise typer.Exit(1)

    if output_json:
        console.print_json(
            render_json(reports, profile=profile.name, tool_version=__version__)
        )
    elif len(reports) == 1:
        _print_single(reports[0], verbose)
    else:
        _print_summary_table(reports)
        if verbose:
            for report in sorted(reports, key=lambda r: r.score.total):
                console.print()
                _print_single(report, verbose=True)

    _apply_fail_on(reports, fail_on)


def _apply_fail_on(reports: list[SkillReport], fail_on: FailOn) -> None:
    if fail_on == FailOn.NEVER:
        return
    failing = {Severity.ERROR}
    if fail_on == FailOn.WARNING:
        failing.add(Severity.WARNING)
    for r in reports:
        if any(f.severity in failing for f in r.findings):
            raise typer.Exit(1)


def _score_color(score: float) -> str:
    if score >= 7.0:
        return "green"
    if score >= 4.0:
        return "yellow"
    return "red"


def _score_bar(score: float, width: int = 20) -> Text:
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
    section_count = len(report.skill.sections)
    location = report.skill_dir or str(report.skill.path)

    console.print(
        Panel(
            f"[bold]{report.name}[/bold]\n"
            f"[dim]{report.skill.path}[/dim]\n"
            f"[dim]format: {report.skill_format} · profile: {report.profile}[/dim]",
            title="[bold]Skill Check[/bold]",
            subtitle=f"[{color}]{sc.total}/10[/{color}]",
            border_style=color,
        )
    )

    console.print(
        f"  [dim]Words:[/dim] {report.skill.word_count}   "
        f"[dim]Tokens (est.):[/dim] ~{report.skill.estimated_tokens}   "
        f"[dim]Sections:[/dim] {section_count}   "
        f"[dim]Findings:[/dim] {len(report.findings)}   "
        f"[dim]Smells:[/dim] {len(report.smells)}"
    )
    console.print()

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

    errors = [f for f in report.findings if f.severity == Severity.ERROR]
    warnings = [f for f in report.findings if f.severity == Severity.WARNING]
    infos = [f for f in report.findings if f.severity == Severity.INFO]

    if errors or warnings or (verbose and infos):
        console.print("[bold]Findings[/bold]")
        for f in errors + warnings + (infos if verbose else []):
            style = _severity_style(f.severity)
            icon = _severity_icon(f.severity)
            console.print(
                f"  [{style}]{icon} {f.severity.value.upper():7s}[/{style}]  "
                f"[dim]{f.id}[/dim]  {f.message}"
            )
        if infos and not verbose:
            console.print(f"  [dim]  … +{len(infos)} info (use --verbose)[/dim]")
        console.print()

    if report.smells:
        console.print("[bold]Smells[/bold]")
        for smell in report.smells:
            desc = SMELL_MESSAGES.get(smell.value, "")
            console.print(f"  [magenta]⚠ {smell.value}[/magenta]  [dim]{desc}[/dim]")
        console.print()

    if verbose and report.skill.sections:
        console.print("[bold]Sections[/bold]")
        for i, sec in enumerate(report.skill.sections):
            wc_color = (
                "red"
                if sec.word_count > 500
                else ("yellow" if sec.word_count > 300 else "dim")
            )
            empty_tag = (
                " [red](empty)[/red]"
                if is_empty_section(report.skill.sections, i)
                else ""
            )
            console.print(
                f"  [bold]##[/bold] {sec.heading}  "
                f"[{wc_color}]{sec.word_count} words[/{wc_color}]{empty_tag}"
            )
        console.print()

    _ = location  # reserved for future use

    if sc.total >= 8.0:
        console.print("[green]→ Skill looks solid.[/green]")
    elif sc.total >= 5.0:
        console.print("[yellow]→ Skill has room for improvement.[/yellow]")
    else:
        console.print("[red]→ Skill needs significant work.[/red]")


def _print_summary_table(reports: list[SkillReport]) -> None:
    reports_sorted = sorted(reports, key=lambda r: r.score.total)

    table = Table(title="Skill Check Summary", title_style="bold")
    table.add_column("#", style="dim", width=3)
    table.add_column("Skill", style="bold")
    table.add_column("Format", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Findings", justify="right")
    table.add_column("Smells", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Tokens (est.)", justify="right", style="dim")

    for i, r in enumerate(reports_sorted, 1):
        color = _score_color(r.score.total)
        table.add_row(
            str(i),
            r.name,
            r.skill_format,
            f"[{color}]{r.score.total}/10[/{color}]",
            str(len(r.findings)),
            str(len(r.smells)),
            str(r.skill.word_count),
            f"~{r.skill.estimated_tokens}",
        )
    console.print(table)

    scores = [r.score.total for r in reports_sorted]
    avg = sum(scores) / len(scores)
    avg_color = _score_color(avg)
    weakest = reports_sorted[0]
    console.print(
        f"\n  [dim]Skills:[/dim] {len(reports)}   "
        f"[dim]Profile:[/dim] {reports_sorted[0].profile}   "
        f"[dim]Avg score:[/dim] [{avg_color}]{avg:.1f}/10[/{avg_color}]   "
        f"[dim]Weakest:[/dim] [{_score_color(scores[0])}]{weakest.name}[/{_score_color(scores[0])}]"
    )
