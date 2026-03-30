"""CLI entry point for skill-refine."""

import typer

from skill_refine import __version__
from skill_refine.cli.check import check
from skill_refine.cli.improve import improve
from skill_refine.cli.report import report
from skill_refine.cli.restore import restore

app = typer.Typer(
    name="skill-refine",
    help=(
        "Analyze and improve skill files (Markdown + YAML frontmatter). "
        "Local-first, diff-first, safe-by-default."
    ),
    no_args_is_help=True,
)

app.command()(check)
app.command()(improve)
app.command()(report)
app.command()(restore)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"skill-refine {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """skill-refine: Analyze and improve skill files."""
