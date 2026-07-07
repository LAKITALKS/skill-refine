"""The analysis engine: discover skills, then check/smell/score each one.

This is the single entry point shared by every command, so ``check``,
``report``, and ``improve`` can never drift apart.

Part of the offline, deterministic lint core: no LLM/provider/network imports.
"""

from __future__ import annotations

from pathlib import Path

from skill_refine.lint.checker import run_checks
from skill_refine.lint.discovery import SkillFile, discover
from skill_refine.lint.models import SkillReport
from skill_refine.lint.parser import parse_skill
from skill_refine.lint.profiles import DEFAULT_PROFILE, Profile, load_profile
from skill_refine.lint.scorer import compute_score
from skill_refine.lint.smells import detect_smells


def analyze(target: Path, profile: Profile) -> list[SkillReport]:
    """Discover and analyze every skill under ``target`` with ``profile``.

    Returns a list of reports in a stable, path-sorted order. Deterministic and
    offline: the same inputs always produce the same output.
    """
    reports: list[SkillReport] = []
    for sf in discover(Path(target)):
        reports.append(analyze_file(sf, profile))
    return reports


def lint_path(
    target: str | Path,
    profile: str | Profile = DEFAULT_PROFILE,
) -> list[SkillReport]:
    """Lint a path (file or directory) and return one report per skill.

    A convenience wrapper around :func:`analyze` that also accepts a profile by
    name (built-in or path to a ``.toml``). This is the primary public entry
    point of the lint core.

    Args:
        target: A skill file, a ``SKILL.md``, or a directory of skills.
        profile: A :class:`~skill_refine.lint.profiles.Profile`, or a string
            naming a built-in (``"standard"``/``"strict"``) or a ``.toml`` path.

    Returns:
        A list of :class:`~skill_refine.lint.models.SkillReport`, path-sorted and
        deterministic. Empty if no skills are found.
    """
    resolved = profile if isinstance(profile, Profile) else load_profile(profile)
    return analyze(Path(target), resolved)


def analyze_file(sf: SkillFile, profile: Profile) -> SkillReport:
    """Analyze a single discovered skill file."""
    skill = parse_skill(sf.path)
    findings = run_checks(skill, profile)
    smells = detect_smells(skill, profile)
    score = compute_score(skill, profile)
    name = skill.metadata.name or sf.name
    return SkillReport(
        skill=skill,
        findings=findings,
        smells=smells,
        score=score,
        profile=profile.name,
        name=name,
        skill_format=sf.skill_format,
        skill_dir=str(sf.skill_dir) if sf.skill_dir else None,
    )
