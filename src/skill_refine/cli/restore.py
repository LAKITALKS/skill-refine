"""CLI restore command for skill-refine."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from skill_refine.refine.differ import print_diff
from skill_refine.safety.backup import find_backups, restore_backup

console = Console()


def restore(
    path: Path = typer.Argument(
        ..., help="Path to the skill file (.md) to restore.",
        exists=True,
    ),
    list_backups: bool = typer.Option(
        False, "--list", "-l", help="List available backups without restoring.",
    ),
    latest: bool = typer.Option(
        False, "--latest", help="Restore the most recent backup directly.",
    ),
) -> None:
    """Restore a skill file from a backup."""
    if not path.is_file() or path.suffix != ".md":
        console.print("[red]Please provide a single .md file.[/red]")
        raise typer.Exit(1)

    backups = find_backups(path)

    if not backups:
        console.print(f"[yellow]No backups found for {path.name}.[/yellow]")
        raise typer.Exit(1)

    # List mode
    if list_backups:
        _print_backup_table(backups, path)
        return

    # Select backup
    if latest:
        selected = backups[0]
    elif len(backups) == 1:
        selected = backups[0]
        console.print(f"[dim]One backup found:[/dim] {selected.path.name} ({selected.age_label})")
    else:
        _print_backup_table(backups, path)
        console.print()
        selected = _prompt_selection(backups)
        if selected is None:
            console.print("[dim]Aborted.[/dim]")
            return

    # Show diff before restore
    current_content = path.read_text(encoding="utf-8")
    backup_content = selected.path.read_text(encoding="utf-8")

    if current_content == backup_content:
        console.print("[dim]Current file is identical to the selected backup. Nothing to restore.[/dim]")
        return

    console.print()
    console.print("[bold]Diff (current → backup)[/bold]")
    print_diff(current_content, backup_content, filename=path.name, console=console)

    # Confirm
    console.print()
    if not typer.confirm(f"Restore {path.name} from {selected.path.name}?", default=False):
        console.print("[dim]Aborted — no changes.[/dim]")
        return

    # Restore
    restore_backup(selected.path, path)
    console.print(f"[green]Restored:[/green] {path} from {selected.path.name}")


def _print_backup_table(backups: list, path: Path) -> None:
    table = Table(title=f"Backups for {path.name}")
    table.add_column("#", style="dim", width=3)
    table.add_column("Backup file", style="bold")
    table.add_column("Age", style="dim")
    table.add_column("Size", justify="right", style="dim")

    for i, b in enumerate(backups, 1):
        size_kb = b.size / 1024
        table.add_row(
            str(i),
            b.path.name,
            b.age_label,
            f"{size_kb:.1f} KB" if size_kb >= 1 else f"{b.size} B",
        )
    console.print(table)


def _prompt_selection(backups: list) -> object | None:
    """Prompt user to select a backup by number."""
    while True:
        raw = typer.prompt(
            f"Select backup [1-{len(backups)}], or 'q' to cancel",
            default="1",
        ).strip()

        if raw.lower() in ("q", "quit", "cancel"):
            return None

        try:
            idx = int(raw) - 1
            if 0 <= idx < len(backups):
                return backups[idx]
        except ValueError:
            pass

        console.print(f"[dim]Enter a number 1–{len(backups)} or 'q'.[/dim]")
