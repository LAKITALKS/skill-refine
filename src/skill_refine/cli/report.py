"""CLI report command for skill-refine."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.markup import escape

from skill_refine import __version__
from skill_refine.lint import (
    ProfileError,
    analyze,
    load_profile,
    render_json,
    render_markdown,
)

console = Console()


class ReportFormat(str, Enum):
    JSON = "json"
    MD = "md"


def report(
    path: Path = typer.Argument(
        ...,
        help="Path to a skill file (.md / SKILL.md) or a directory.",
        exists=True,
    ),
    profile_name: str = typer.Option(
        "standard",
        "--profile",
        "-P",
        help="Lint profile: 'standard' (default), 'strict', or a path to a .toml profile.",
    ),
    fmt: ReportFormat = typer.Option(
        ReportFormat.MD,
        "--format",
        "-f",
        help="Output format.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write report to file instead of stdout.",
    ),
) -> None:
    """Generate a detailed report for skill files."""
    try:
        profile = load_profile(profile_name)
    except ProfileError as e:
        console.print(f"[red]{escape(str(e))}[/red]")
        raise typer.Exit(2)

    reports = analyze(path, profile)

    if not reports:
        console.print("[red]No skill files found (SKILL.md or *.md).[/red]")
        raise typer.Exit(1)

    if fmt == ReportFormat.JSON:
        content = render_json(reports, profile=profile.name, tool_version=__version__)
    else:
        content = render_markdown(reports, profile=profile.name)

    if output:
        output.write_text(content, encoding="utf-8")
        console.print(f"[green]Report written to:[/green] {output}")
    else:
        console.print(content, highlight=False)
