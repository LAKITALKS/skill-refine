"""skill_refine.lint: the offline, deterministic lint core.

This package is importable, deterministic, and offline. It must never import
any LLM, provider, or network dependency (no ``httpx``, no ``anthropic``, no
``skill_refine.llm``). That guarantee is covered by a dedicated test.

Public API:
    lint_path(target, profile="standard") -> list[SkillReport]   # primary entry
    analyze(target, profile) -> list[SkillReport]
    discover(path) -> list[SkillFile]
    load_profile(name_or_path) -> Profile
    render_json(...) / render_markdown(...)
"""

from __future__ import annotations

from skill_refine.lint.checker import run_checks
from skill_refine.lint.discovery import SkillFile, discover
from skill_refine.lint.engine import analyze, analyze_file, lint_path
from skill_refine.lint.models import (
    Finding,
    ScoreCard,
    Section,
    Severity,
    Skill,
    SkillMetadata,
    SkillReport,
    SmellType,
)
from skill_refine.lint.parser import parse_skill
from skill_refine.lint.profiles import (
    BUILTINS,
    DEFAULT_PROFILE,
    Profile,
    ProfileError,
    load_profile,
)
from skill_refine.lint.scorer import compute_score
from skill_refine.lint.serialize import (
    SCHEMA_VERSION,
    build_document,
    render_json,
    render_markdown,
)
from skill_refine.lint.smells import SMELL_MESSAGES, detect_smells

__all__ = [
    "lint_path",
    "analyze",
    "analyze_file",
    "discover",
    "SkillFile",
    "parse_skill",
    "run_checks",
    "detect_smells",
    "compute_score",
    "load_profile",
    "Profile",
    "ProfileError",
    "BUILTINS",
    "DEFAULT_PROFILE",
    "render_json",
    "render_markdown",
    "build_document",
    "SCHEMA_VERSION",
    "SMELL_MESSAGES",
    "Finding",
    "ScoreCard",
    "Section",
    "Severity",
    "Skill",
    "SkillMetadata",
    "SkillReport",
    "SmellType",
]
