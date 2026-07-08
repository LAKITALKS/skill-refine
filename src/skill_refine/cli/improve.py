"""CLI improve command for skill-refine.

The deterministic analysis uses the offline lint core. The rewriting/refinement
machinery is imported lazily from the optional ``skill_refine.llm`` layer, so
the command shows a friendly message (not a traceback) when the LLM extras are
not installed.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from skill_refine.lint import (
    ProfileError,
    ScoreCard,
    Severity,
    compute_score,
    detect_smells,
    load_profile,
    parse_skill,
    run_checks,
)
from skill_refine.textdiff import print_diff

console = Console()


def _load_llm() -> SimpleNamespace:
    """Lazily import the optional LLM layer.

    Exits with a friendly message (exit code 3) if the extras are missing.
    """
    try:
        from skill_refine.llm.critique import compute_llm_score
        from skill_refine.llm.guard import check_rewrite
        from skill_refine.llm.models import BoundaryConfidence, RewriteMode
        from skill_refine.llm.providers.factory import (
            auto_select_provider,
            get_provider,
        )
        from skill_refine.llm.refine.generator import (
            find_missing_sections,
            generate_sections,
        )
        from skill_refine.llm.refine.patcher import (
            apply_patch,
            assess_boundary_confidence,
            patch_section,
        )
        from skill_refine.llm.refine.rewriter import rewrite_skill
    except ImportError:
        console.print(
            "[red]The 'improve' command requires the optional LLM layer, "
            "which is not installed.[/red]"
        )
        console.print("[dim]Install it with one of:[/dim]")
        for extra, note in (
            ("llm", "local models via Ollama"),
            ("anthropic", "Anthropic API"),
            ("ollama", "local models via Ollama"),
            ("all", "everything"),
        ):
            # escape() keeps the [extra] brackets literal instead of letting
            # rich parse them as markup tags.
            hint = escape(f"skill-refine[{extra}]")
            console.print(f"  [bold]pip install '{hint}'[/bold]  [dim]# {note}[/dim]")
        raise typer.Exit(3)

    return SimpleNamespace(
        compute_llm_score=compute_llm_score,
        check_rewrite=check_rewrite,
        BoundaryConfidence=BoundaryConfidence,
        RewriteMode=RewriteMode,
        auto_select_provider=auto_select_provider,
        get_provider=get_provider,
        find_missing_sections=find_missing_sections,
        generate_sections=generate_sections,
        apply_patch=apply_patch,
        assess_boundary_confidence=assess_boundary_confidence,
        patch_section=patch_section,
        rewrite_skill=rewrite_skill,
    )


def improve(
    path: Path = typer.Argument(
        ...,
        help="Path to a single skill file (.md / SKILL.md).",
        exists=True,
    ),
    profile_name: str = typer.Option(
        "standard",
        "--profile",
        "-P",
        help="Lint profile used for scoring and section expectations.",
    ),
    mode: str = typer.Option(
        "all",
        "--mode",
        "-m",
        help="Rewrite mode: all, clarity, compact, robustness, structure, safety.",
    ),
    section: str | None = typer.Option(
        None,
        "--section",
        "-s",
        help="Patch a single section instead of full rewrite.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show diff without writing."
    ),
    provider_name: str | None = typer.Option(
        None, "--provider", "-p", help="LLM provider (anthropic, ollama, stub)."
    ),
    critique: bool = typer.Option(
        False, "--critique", help="Also show an LLM-based quality score."
    ),
    allow_stub: bool = typer.Option(
        False,
        "--allow-stub-provider",
        "--allow-stub",
        help=(
            "Allow the test-only stub provider (echoes input, no real "
            "improvement). --allow-stub is a backward-compatible alias."
        ),
    ),
    generate_missing: bool = typer.Option(
        False,
        "--generate-missing",
        "-g",
        help="Generate missing sections before rewriting.",
    ),
) -> None:
    """Improve a skill file using LLM-assisted rewriting."""
    if not path.is_file() or path.suffix != ".md":
        console.print("[red]Please provide a single .md file.[/red]")
        raise typer.Exit(1)

    try:
        profile = load_profile(profile_name)
    except ProfileError as e:
        console.print(f"[red]{escape(str(e))}[/red]")
        raise typer.Exit(2)

    llm = _load_llm()

    try:
        rewrite_mode = llm.RewriteMode(mode)
    except ValueError:
        valid = ", ".join(m.value for m in llm.RewriteMode)
        console.print(f"[red]Unknown mode '{mode}'. Valid modes: {valid}.[/red]")
        raise typer.Exit(2)

    # Resolve provider. The stub provider only echoes the input and produces no
    # real improvement, so it is test-only and must be requested explicitly.
    if provider_name == "stub" and not allow_stub:
        console.print(
            "[red]The 'stub' provider is test-only and produces no real "
            "improvement.[/red]\n"
            "[dim]Re-run with --allow-stub-provider only if you deliberately "
            "want it (e.g. for pipeline testing).[/dim]"
        )
        raise typer.Exit(2)

    try:
        if provider_name:
            provider = llm.get_provider(provider_name)
        else:
            provider = llm.auto_select_provider(include_stub=allow_stub)
    except RuntimeError as e:
        console.print(f"[red]{escape(str(e))}[/red]")
        raise typer.Exit(1)

    if provider is None:
        anthropic_hint = escape("pip install 'skill-refine[anthropic]'")
        ollama_hint = escape("pip install 'skill-refine[ollama]'")
        console.print(
            "[red]'improve' requires an LLM provider, but none is available.[/red]"
        )
        console.print(
            "[dim]It will not fabricate an improvement. Configure a provider:[/dim]"
        )
        console.print(
            f"[dim]  • Anthropic: set ANTHROPIC_API_KEY, then {anthropic_hint}[/dim]"
        )
        console.print(
            f"[dim]  • Ollama:    run 'ollama serve', then {ollama_hint}[/dim]"
        )
        raise typer.Exit(1)

    console.print(
        f"[dim]Provider:[/dim] [bold]{provider.name}[/bold] "
        f"[dim]({provider.model_id()})[/dim]   "
        f"[dim]Profile:[/dim] [bold]{profile.name}[/bold]"
    )
    console.print()

    # 1. Parse and analyze
    skill = parse_skill(path)
    findings = run_checks(skill, profile)
    smells = detect_smells(skill, profile)
    score_before = compute_score(skill, profile)
    critique_before = (
        llm.compute_llm_score(skill, provider=provider) if critique else None
    )

    _print_score_summary("Before", score_before, critique_before)

    # 2. Generate missing sections if requested or implied by the mode
    should_generate = generate_missing or rewrite_mode in (
        llm.RewriteMode.STRUCTURE,
        llm.RewriteMode.ALL,
    )

    if should_generate and not section:
        missing = llm.find_missing_sections(skill, profile.expected_sections)
        if missing:
            console.print()
            console.print(
                "[bold]Missing sections:[/bold] "
                + ", ".join(f"[yellow]{n.title()}[/yellow]" for n in missing)
            )
            with console.status("[bold]Generating missing sections…[/bold]"):
                generated_text = llm.generate_sections(
                    skill, missing, provider=provider
                )

            if generated_text.strip():
                augmented_content = skill.raw_content.rstrip() + "\n\n" + generated_text
                console.print(f"[dim]Generated {len(missing)} section(s).[/dim]")
                skill = _reparse_content(augmented_content, path)
                findings = run_checks(skill, profile)
                smells = detect_smells(skill, profile)

    # 3. Rewrite or patch
    console.print()
    if section:
        rewritten_content = _do_section_patch(llm, skill, section)
    else:
        with console.status(f"[bold]Rewriting ({rewrite_mode.value})…[/bold]"):
            rewritten_content = llm.rewrite_skill(
                skill,
                findings,
                smells,
                mode=rewrite_mode,
                provider=provider,
            )

    if rewritten_content is None:
        raise typer.Exit(1)

    # 4. Guard check
    original_skill = parse_skill(path)
    guard_result = llm.check_rewrite(original_skill, rewritten_content, profile)

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
    rewritten_skill = _reparse_content(rewritten_content, path)
    score_after = compute_score(rewritten_skill, profile)
    critique_after = (
        llm.compute_llm_score(rewritten_skill, provider=provider) if critique else None
    )

    console.print()
    _print_score_summary("After", score_after, critique_after)

    # 6. Token comparison
    console.print()
    _print_token_comparison(
        original_skill.estimated_tokens, rewritten_skill.estimated_tokens
    )

    # 7. Diff
    console.print()
    console.print("[bold]Diff[/bold]")
    print_diff(
        original_skill.raw_content,
        rewritten_content,
        filename=path.name,
        console=console,
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
        console.print(
            Panel(rewritten_content, title="Full Result", border_style="dim")
        )
        console.print()
        answer = _prompt_apply()

    if answer != "y":
        console.print("[dim]Aborted — no changes written.[/dim]")
        return

    # 9. Backup + write
    from skill_refine.safety.backup import create_backup

    backup_path = create_backup(path)
    console.print(f"[dim]Backup:[/dim] {backup_path}")

    path.write_text(rewritten_content, encoding="utf-8")
    console.print(f"[green]Written:[/green] {path}")


def _reparse_content(content: str, original_path: Path):
    """Parse arbitrary content by round-tripping through a temp file."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    )
    tmp.write(content)
    tmp.close()
    try:
        skill = parse_skill(Path(tmp.name))
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    skill.path = original_path
    return skill


def _do_section_patch(llm: SimpleNamespace, skill, section_name: str) -> str | None:
    """Patch a single section with a boundary confidence check."""
    confidence = llm.assess_boundary_confidence(skill, section_name)

    if confidence == llm.BoundaryConfidence.LOW:
        console.print(
            f"[red]Section '{section_name}' has low boundary confidence.[/red]\n"
            "[dim]Cannot safely isolate this section for patching. "
            "Consider using a full rewrite instead.[/dim]"
        )
        return None

    if confidence == llm.BoundaryConfidence.MEDIUM:
        console.print(
            f"[yellow]Section '{section_name}' has medium boundary confidence.[/yellow]\n"
            "[dim]Section boundaries may not be perfectly clear.[/dim]"
        )
        if not typer.confirm("Continue with patch?", default=True):
            return None

    with console.status(f"[bold]Patching section '{section_name}'…[/bold]"):
        proposal = llm.patch_section(skill, section_name)

    if proposal is None:
        console.print(f"[red]Section '{section_name}' not found in skill.[/red]")
        return None

    console.print(
        f"[dim]Boundary confidence:[/dim] [bold]{proposal.confidence.value}[/bold]"
    )

    return llm.apply_patch(skill, proposal)


def _print_score_summary(
    label: str, score: ScoreCard, critique_score: float | None
) -> None:
    color = _score_color(score.total)
    parts = [
        f"[bold]{label}:[/bold]",
        f"[{color}]{score.total}/10[/{color}]",
        f"[dim](C:{score.completeness} S:{score.structure} "
        f"M:{score.metadata} K:{score.conciseness})[/dim]",
    ]
    if critique_score is not None:
        llm_color = _score_color(critique_score)
        parts.append(
            f"  [dim]LLM:[/dim] [{llm_color}]{critique_score}/10[/{llm_color}]"
        )
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
    console.print(
        "[bold]Apply changes?[/bold]  [dim][y]es / [n]o / [e] show full result[/dim]"
    )
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
