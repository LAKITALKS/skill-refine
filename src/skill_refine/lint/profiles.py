"""Lint profiles: the calibration behind checks, smells, and scoring.

A profile bundles every tunable assumption (expected sections, frontmatter
requirements, thresholds, scoring weights, active smells) so the lint core is
never hardwired to one private schema.

Built-in profiles:
- ``standard`` (default): aligned with Agent Skills / ``SKILL.md`` best
  practices. Frontmatter ``name`` + ``description`` are required; there is no
  forced section taxonomy.
- ``strict``: preserves the legacy v0.1 schema (eight expected sections,
  section-driven smells) for backwards-compatible measuring.

Custom profiles can be loaded from TOML via :func:`load_profile`.

Part of the offline, deterministic lint core: no LLM/provider/network imports.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

_DEFAULT_VAGUE_PHRASES: tuple[str, ...] = (
    "when needed",
    "as appropriate",
    "if necessary",
    "when applicable",
    "as needed",
    "use this when you need to",
    "whenever",
    "in general",
    "sometimes",
    "usually",
)

_ALL_SMELLS: frozenset[str] = frozenset(
    {
        "VAGUE_TRIGGER",
        "NO_WARNINGS",
        "NO_FAILURE_CASES",
        "TOKEN_BLOAT",
        "NO_INPUTS_OUTPUTS",
        "NO_BOUNDARIES",
        "WALL_OF_TEXT",
        "EMPTY_FRONTMATTER",
    }
)

_WEIGHT_KEYS = ("completeness", "structure", "metadata", "conciseness")


class ProfileError(ValueError):
    """Raised when a profile name cannot be resolved or a TOML profile is invalid."""


@dataclass(frozen=True)
class Profile:
    """A named bundle of lint calibration settings."""

    name: str
    # Frontmatter
    required_frontmatter: tuple[str, ...]
    recommended_frontmatter: tuple[str, ...]
    min_frontmatter_description_words: int
    max_frontmatter_description_chars: int  # 0 disables the check
    # Sections
    expected_sections: tuple[str, ...]
    min_description_words: int  # for a literal "## Description" section
    # Thresholds
    max_section_words: int
    max_paragraph_words: int
    max_total_words: int
    # Structure scoring
    structure_no_sections_score: float
    structure_min_sections: int
    # Scoring weights (should sum to 1.0)
    weights: dict[str, float]
    # Smells + heuristics
    smells: frozenset[str]
    vague_trigger_phrases: tuple[str, ...]


STANDARD = Profile(
    name="standard",
    required_frontmatter=("name", "description"),
    recommended_frontmatter=("name", "description"),
    min_frontmatter_description_words=6,
    max_frontmatter_description_chars=1024,
    expected_sections=(),
    min_description_words=0,
    max_section_words=500,
    max_paragraph_words=150,
    max_total_words=5000,
    structure_no_sections_score=5.0,
    structure_min_sections=2,
    weights={
        "completeness": 0.30,
        "structure": 0.20,
        "metadata": 0.30,
        "conciseness": 0.20,
    },
    smells=frozenset({"TOKEN_BLOAT", "WALL_OF_TEXT"}),
    vague_trigger_phrases=_DEFAULT_VAGUE_PHRASES,
)

STRICT = Profile(
    name="strict",
    required_frontmatter=(),
    recommended_frontmatter=("name", "description", "tags"),
    min_frontmatter_description_words=0,
    max_frontmatter_description_chars=0,
    expected_sections=(
        "description",
        "when to apply",
        "when not to apply",
        "warnings",
        "inputs",
        "outputs",
        "steps",
        "examples",
    ),
    min_description_words=10,
    max_section_words=500,
    max_paragraph_words=150,
    max_total_words=3000,
    structure_no_sections_score=0.0,
    structure_min_sections=3,
    weights={
        "completeness": 0.35,
        "structure": 0.25,
        "metadata": 0.15,
        "conciseness": 0.25,
    },
    smells=_ALL_SMELLS,
    vague_trigger_phrases=_DEFAULT_VAGUE_PHRASES,
)

BUILTINS: dict[str, Profile] = {"standard": STANDARD, "strict": STRICT}

DEFAULT_PROFILE = "standard"


def load_profile(name_or_path: str) -> Profile:
    """Resolve a profile by built-in name or path to a ``.toml`` file.

    - ``"standard"`` / ``"strict"`` return the built-ins.
    - Anything that looks like a TOML file (``.toml`` suffix or an existing
      path) is loaded as a custom profile.
    """
    if name_or_path in BUILTINS:
        return BUILTINS[name_or_path]

    path = Path(name_or_path)
    if path.suffix == ".toml" or path.exists():
        return load_toml_profile(path)

    available = ", ".join(sorted(BUILTINS))
    raise ProfileError(
        f"Unknown profile '{name_or_path}'. "
        f"Use a built-in ({available}) or a path to a .toml profile."
    )


def load_toml_profile(path: Path) -> Profile:
    """Load a custom profile from a TOML file.

    The file may set ``extends = "standard"`` (default) or ``"strict"`` to pick
    a base, then override any Profile field. A ``name`` key is required.
    """
    if not path.exists():
        raise ProfileError(f"Profile file not found: {path}")

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ProfileError(f"Invalid TOML in profile '{path}': {e}") from e

    # Allow the settings to be nested under [profile] or [tool.skill_refine].
    if "profile" in data and isinstance(data["profile"], dict):
        data = data["profile"]

    base_name = str(data.get("extends", DEFAULT_PROFILE))
    if base_name not in BUILTINS:
        raise ProfileError(
            f"Profile '{path}' extends unknown base '{base_name}'. "
            f"Use one of: {', '.join(sorted(BUILTINS))}."
        )
    base = BUILTINS[base_name]

    name = str(data.get("name") or path.stem)

    overrides: dict[str, object] = {"name": name}
    _apply_tuple(overrides, data, "required_frontmatter")
    _apply_tuple(overrides, data, "recommended_frontmatter")
    _apply_tuple(overrides, data, "expected_sections")
    _apply_tuple(overrides, data, "vague_trigger_phrases")
    _apply_int(overrides, data, "min_frontmatter_description_words")
    _apply_int(overrides, data, "max_frontmatter_description_chars")
    _apply_int(overrides, data, "min_description_words")
    _apply_int(overrides, data, "max_section_words")
    _apply_int(overrides, data, "max_paragraph_words")
    _apply_int(overrides, data, "max_total_words")
    _apply_int(overrides, data, "structure_min_sections")
    _apply_float(overrides, data, "structure_no_sections_score")

    if "smells" in data:
        smells = data["smells"]
        if not isinstance(smells, list):
            raise ProfileError(f"Profile '{path}': 'smells' must be an array.")
        unknown = {str(s) for s in smells} - _ALL_SMELLS
        if unknown:
            raise ProfileError(
                f"Profile '{path}': unknown smells {sorted(unknown)}. "
                f"Valid smells: {sorted(_ALL_SMELLS)}."
            )
        overrides["smells"] = frozenset(str(s) for s in smells)

    if "weights" in data:
        weights = data["weights"]
        if not isinstance(weights, dict):
            raise ProfileError(f"Profile '{path}': 'weights' must be a table.")
        merged = dict(base.weights)
        for key, value in weights.items():
            if key not in _WEIGHT_KEYS:
                raise ProfileError(
                    f"Profile '{path}': unknown weight '{key}'. "
                    f"Valid weights: {list(_WEIGHT_KEYS)}."
                )
            merged[key] = float(value)
        overrides["weights"] = merged

    return replace(base, **overrides)


def _apply_tuple(out: dict, data: dict, key: str) -> None:
    if key in data:
        value = data[key]
        if not isinstance(value, list):
            raise ProfileError(f"Profile field '{key}' must be an array.")
        out[key] = tuple(str(v) for v in value)


def _apply_int(out: dict, data: dict, key: str) -> None:
    if key in data:
        out[key] = int(data[key])


def _apply_float(out: dict, data: dict, key: str) -> None:
    if key in data:
        out[key] = float(data[key])
