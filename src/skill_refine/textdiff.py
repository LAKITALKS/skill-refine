"""Colored unified diff output using rich.

Offline and dependency-clean (stdlib ``difflib`` + ``rich``). Shared by the
``improve`` and ``restore`` commands so ``restore`` never needs the LLM layer.
"""

from __future__ import annotations

import difflib

from rich.console import Console
from rich.text import Text


def unified_diff(
    original: str,
    rewritten: str,
    filename: str = "skill.md",
) -> str:
    """Generate a unified diff string between original and rewritten content."""
    orig_lines = original.splitlines(keepends=True)
    new_lines = rewritten.splitlines(keepends=True)

    diff = difflib.unified_diff(
        orig_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "\n".join(diff)


def print_diff(
    original: str,
    rewritten: str,
    filename: str = "skill.md",
    console: Console | None = None,
) -> None:
    """Print a colored unified diff to the console."""
    if console is None:
        console = Console()

    diff_text = unified_diff(original, rewritten, filename)

    if not diff_text.strip():
        console.print("[dim]No changes.[/dim]")
        return

    for line in diff_text.split("\n"):
        console.print(_style_diff_line(line), highlight=False)


def _style_diff_line(line: str) -> Text:
    text = Text(line)
    if line.startswith("+++") or line.startswith("---"):
        text.stylize("bold")
    elif line.startswith("@@"):
        text.stylize("cyan")
    elif line.startswith("+"):
        text.stylize("green")
    elif line.startswith("-"):
        text.stylize("red")
    return text
