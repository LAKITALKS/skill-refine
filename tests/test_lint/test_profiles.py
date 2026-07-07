"""Tests for the profile system (standard, strict, custom TOML)."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_refine.lint.profiles import (
    STANDARD,
    STRICT,
    Profile,
    ProfileError,
    load_profile,
)


def test_default_is_standard() -> None:
    from skill_refine.lint.profiles import DEFAULT_PROFILE

    assert DEFAULT_PROFILE == "standard"


def test_load_builtins() -> None:
    assert load_profile("standard") is STANDARD
    assert load_profile("strict") is STRICT


def test_standard_shape() -> None:
    assert STANDARD.required_frontmatter == ("name", "description")
    assert STANDARD.expected_sections == ()
    # Section-schema smells are off by default under standard.
    assert "NO_WARNINGS" not in STANDARD.smells
    assert "TOKEN_BLOAT" in STANDARD.smells


def test_strict_shape_preserves_legacy_schema() -> None:
    assert len(STRICT.expected_sections) == 8
    assert "when to apply" in STRICT.expected_sections
    assert "NO_WARNINGS" in STRICT.smells
    assert STRICT.recommended_frontmatter == ("name", "description", "tags")


def test_unknown_profile_raises() -> None:
    with pytest.raises(ProfileError):
        load_profile("does-not-exist")


def test_custom_toml_extends_and_overrides(tmp_path: Path) -> None:
    toml = tmp_path / "custom.toml"
    toml.write_text(
        "\n".join(
            [
                'name = "house"',
                'extends = "strict"',
                "max_total_words = 1234",
                'expected_sections = ["description", "steps"]',
                "[weights]",
                "conciseness = 0.5",
            ]
        ),
        encoding="utf-8",
    )
    profile = load_profile(str(toml))
    assert isinstance(profile, Profile)
    assert profile.name == "house"
    assert profile.max_total_words == 1234
    assert profile.expected_sections == ("description", "steps")
    assert profile.weights["conciseness"] == 0.5
    # Untouched weights come from the strict base.
    assert profile.weights["completeness"] == STRICT.weights["completeness"]


def test_custom_toml_defaults_to_standard_base(tmp_path: Path) -> None:
    toml = tmp_path / "c.toml"
    toml.write_text('name = "x"\n', encoding="utf-8")
    profile = load_profile(str(toml))
    assert profile.required_frontmatter == STANDARD.required_frontmatter


def test_custom_toml_invalid_smell_rejected(tmp_path: Path) -> None:
    toml = tmp_path / "bad.toml"
    toml.write_text('name = "x"\nsmells = ["NOT_A_SMELL"]\n', encoding="utf-8")
    with pytest.raises(ProfileError):
        load_profile(str(toml))


def test_custom_toml_invalid_syntax_rejected(tmp_path: Path) -> None:
    toml = tmp_path / "broken.toml"
    toml.write_text("name = = =\n", encoding="utf-8")
    with pytest.raises(ProfileError):
        load_profile(str(toml))


def test_custom_toml_unknown_base_rejected(tmp_path: Path) -> None:
    toml = tmp_path / "x.toml"
    toml.write_text('name = "x"\nextends = "nope"\n', encoding="utf-8")
    with pytest.raises(ProfileError):
        load_profile(str(toml))
