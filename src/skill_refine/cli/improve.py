"""CLI improve command for skill-refine."""

from __future__ import annotations

import tempfile
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from skill_refine.analysis.checker import run_checks
from skill_refine.analysis.scorer import compute_score
from skill_refine.analysis.smells import detect_smells
from skill_refine.core.models import (
    BoundaryConfidence,
    RewriteMode,
    Severity,
)
from skill_refine.core.parser import parse_skill
from skill_refine.providers.factory import auto_select_provider, get_provider
from skill_refine.refine.differ import print_diff
from skill_refine.refine.generator import find_missing_sections, generate_sections
from skill_refine.refine.patcher import apply_patch, assess_boundary_confidence, patch_section
from skill_refine.refine.rewriter import rewrite_skill
from skill_refine.safety.backup import create_backup
from skill_refine.safety.guard import check_rewrite

console = Console()


def improve(
    path: Path = typer.Argument(
        ..., help="Path to a skill file (.md).", exists=True,
    ),
    mode: RewriteMode = typer.Option(
        RewriteMode.ALL, "--mode", "-m", help="Rewrite mode.",
    ),
    section: str | None = typer.Option(
        None, "--section", "-s",
        help="Patch a single section instead of full rewrite.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show diff without writing.",
    ),
    provider_name: str | None = typer.Option(
        None, "--provider", "-p", help="LLM provider (anthropic, ollama, stub).",
    ),
    critique: bool = typer.Option(
        False, "--critique", help="Also show LLM-based quality score.",
    ),
    generate_missing: bool = typer.Option(
        False, "--generate-missing", "-g",
        help="Generate missing sections before rewriting.",
    ),
) -> None:
    """Improve a skill file using LLM-assisted rewriting."""
    if not path.is_file() or path.suffix != ".md":
        console.print("[red]Please provide a single .md file.[/red]")
        raise typer.Exit(1)

    # Resolve provider
    try:
        provider = (
            get_provider(provider_name) if provider_name
            else auto_select_provider()
        )
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if provider is None:
        console.print(
            "[red]No LLM provider available.[/red]\n"
            "[dim]Set ANTHROPIC_API_KEY or start Ollama (ollama serve).[/dim]"
        )
        raise typer.Exit(1)

    console.print(
        f"[dim]Provider:[/dim] [bold]{provider.name}[/bold] "
        f"[dim]({provider.model_id()})[/dim]"
    )
    console.print()

    # 1. Parse and analyze
    skill = parse_skill(path)
    findings = run_checks(skill)
    smells = detect_smells(skill)
    score_before = compute_score(skill, llm=critique, provider=provider)

    _print_score_summary("Before", score_before)

    # 2. Generate missing sections if requested or mode implies it
    should_generate = generate_missing or mode in (RewriteMode.STRUCTURE, RewriteMode.ALL)
    rewritten_content: str | None = None

    if should_generate and not section:
        missing = find_missing_sections(skill)
        if missing:
            console.print()
            console.print(
                f"[bold]Missing sections:[/bold] "
                + ", ".join(f"[yellow]{n.title()}[/yellow]" for n in missing)
            )
            with console.status("[bold]Generating missing sections…[/bold]"):
                generated_text = generate_sections(
                    skill, missing, provider=provider,
                )

            if generated_text.strip():
                # Append generated sections to the raw content
                augmented_content = skill.raw_content.rstrip() + "\n\n" + generated_text
                console.print(f"[dim]Generated {len(missing)} section(s).[/dim]")

                # Re-parse augmented content for the rewriter
                tmp_aug = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".md", delete=False, encoding="utf-8"
                )
                tmp_aug.write(augmented_content)
                tmp_aug.close()
                try:
                    skill = parse_skill(Path(tmp_aug.name))
                    findings = run_checks(skill)
                    smells = detect_smells(skill)
                finally:
                    Path(tmp_aug.name).unlink(missing_ok=True)

                # Use augmented content as base for rewrite
                skill.path = path  # Restore original path

    # 3. Rewrite or patch
    console.print()
    if section:
        rewritten_content = _do_section_patch(
            skill, section, provider, provider_name
        )
    else:
        with console.status(f"[bold]Rewriting ({mode.value})…[/bold]"):
            rewritten_content = rewrite_skill(
                skill, findings, smells,
                mode=mode,
                provider=provider,
            )

    if rewritten_content is None:
        raise typer.Exit(1)

    # 4. Guard check
    original_skill = parse_skill(path)
    guard_result = check_rewrite(original_skill, rewritten_content)

    if guard_result.warnings:
        console.print()
        console.print("[bold]Guard Warnings[/bold]")
        for w in guard_result.warnings:
            style = "red bold" if w.severity == Severity.ERROR else "yellow"
            console.print(f"  [{style}]{w.code}[/{style}]  {w.message}")

    if guard_result.blocked:
        console.print()
        console.print(
            f"[red bold]Blocked:[/red bold] {guard_result.block_reason}\n"
            "[dim]Rewrite will not be applied.[/dim]"
        )
        raise typer.Exit(1)

    # 5. Score the rewrite
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(rewritten_content)
        tmp.flush()
        tmp_path = Path(tmp.name)

    try:
        rewritten_skill = parse_skill(tmp_path)
        score_after = compute_score(
            rewritten_skill, llm=critique, provider=provider,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    console.print()
    _print_score_summary("After", score_after)

    # 6. Token comparison
    console.print()
    _print_token_comparison(original_skill.estimated_tokens, rewritten_skill.estimated_tokens)

    # 7. Diff
    console.print()
    console.print("[bold]Diff[/bold]")
    print_diff(
        original_skill.raw_content, rewritten_content,
        filename=path.name, console=console,
    )

    # 8. Dry run or confirm
    if dry_run:
        console.print()
        console.print("[dim]Dry run — no changes written.[/dim]")
        return

    console.print()
    answer = _prompt_user()

    if answer == "e":
        console.print()
        console.print(Panel(rewritten_content, title="Full Result", border_style="dim"))
        console.print()
        answer = _prompt_apply()

    if answer != "y":
        console.print("[dim]Aborted — no changes written.[/dim]")
        return

    # 9. Backup + write
    backup_path = create_backup(path)
    console.print(f"[dim]Backup:[/dim] {backup_path}")

    path.write_text(rewritten_content, encoding="utf-8")
    console.print(f"[green]Written:[/green] {path}")


def _do_section_patch(
    skill, section_name: str, provider, provider_name: str | None,
) -> str | None:
    """Patch a single section with boundary confidence check."""
    confidence = assess_boundary_confidence(skill, section_name)

    if confidence == BoundaryConfidence.LOW:
        console.print(
            f"[red]Section '{section_name}' has low boundary confidence.[/red]\n"
            "[dim]Cannot safely isolate this section for patching. "
            "Consider using full rewrite instead.[/dim]"
        )
        return None

    if confidence == BoundaryConfidence.MEDIUM:
        console.print(
            f"[yellow]Section '{section_name}' has medium boundary confidence.[/yellow]\n"
            "[dim]Section boundaries may not be perfectly clear.[/dim]"
        )
        proceed = typer.confirm("Continue with patch?", default=True)
        if not proceed:
            return None

    with console.status(f"[bold]Patching section '{section_name}'…[/bold]"):
        proposal = patch_section(
            skill, section_name,
            provider=provider,
            provider_name=provider_name,
        )

    if proposal is None:
        console.print(f"[red]Section '{section_name}' not found in skill.[/red]")
        return None

    console.print(
        f"[dim]Boundary confidence:[/dim] [bold]{proposal.confidence.value}[/bold]"
    )

    return apply_patch(skill, proposal)


def _print_score_summary(label: str, score) -> None:
    color = _score_color(score.total)
    parts = [
        f"[bold]{label}:[/bold]",
        f"[{color}]{score.total}/10[/{color}]",
        f"[dim](C:{score.completeness} S:{score.structure} M:{score.metadata} K:{score.conciseness})[/dim]",
    ]
    if score.llm_score is not None:
        llm_color = _score_color(score.llm_score)
        parts.append(f"  [dim]LLM:[/dim] [{llm_color}]{score.llm_score}/10[/{llm_color}]")
    console.print("  " + "  ".join(parts))


def _print_token_comparison(before: int, after: int) -> None:
    delta = after - before
    sign = "+" if delta > 0 else ""
    color = "green" if before == 0 or abs(delta) < before * 0.15 else "yellow"

    console.print(
        f"  [dim]Tokens (est.):[/dim]  "
        f"~{before} → ~{after}  "
        f"[{color}]({sign}{delta})[/{color}]"
    )


def _score_color(score: float) -> str:
    if score >= 7.0:
        return "green"
    if score >= 4.0:
        return "yellow"
    return "red"


def _prompt_user() -> str:
    console.print("[bold]Apply changes?[/bold]  [dim][y]es / [n]o / [e] show full result[/dim]")
    while True:
        answer = typer.prompt("", default="n").strip().lower()
        if answer in ("y", "yes", "n", "no", "e"):
            return answer[0]
        console.print("[dim]Please enter y, n, or e.[/dim]")


def _prompt_apply() -> str:
    console.print("[bold]Apply changes?[/bold]  [dim][y]es / [n]o[/dim]")
    while True:
        answer = typer.prompt("", default="n").strip().lower()
        if answer in ("y", "yes", "n", "no"):
            return answer[0]
        console.print("[dim]Please enter y or n.[/dim]")
