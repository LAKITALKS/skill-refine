"""Shared fixtures for the test suite."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def strict_full_skill(tmp_path: Path) -> Path:
    """A skill that satisfies the legacy strict schema (all 8 sections)."""
    return _write(
        tmp_path / "full.md",
        dedent("""\
            ---
            name: Full Skill
            description: A fully complete skill for testing
            tags: [a, b]
            ---

            ## Description

            A thorough description of what this skill does and how it works.

            ## When to apply

            When a specific, well-defined condition is met.

            ## When not to apply

            When the task is outside the scope of this skill.

            ## Warnings

            Handle edge cases with care.

            ## Inputs

            - Input A

            ## Outputs

            - Output B

            ## Steps

            1. Do X
            2. Do Y

            ## Examples

            Example usage here.
        """),
    )


@pytest.fixture
def standard_skill(tmp_path: Path) -> Path:
    """A skill aligned with Agent Skills best practices (frontmatter + body)."""
    return _write(
        tmp_path / "standard.md",
        dedent("""\
            ---
            name: Commit Helper
            description: Writes clear conventional commit messages from a staged diff
            ---

            ## Overview

            This skill turns a staged git diff into a conventional commit message.

            ## How it works

            - Read the staged changes
            - Summarize the intent
            - Emit a single conventional commit subject and body
        """),
    )


@pytest.fixture
def name_only_skill(tmp_path: Path) -> Path:
    """Frontmatter with a name but no description."""
    return _write(
        tmp_path / "name-only.md",
        dedent("""\
            ---
            name: Bad
            ---

            ## Description

            Short.
        """),
    )


@pytest.fixture
def empty_skill(tmp_path: Path) -> Path:
    return _write(tmp_path / "empty.md", "")


@pytest.fixture
def no_frontmatter_skill(tmp_path: Path) -> Path:
    return _write(tmp_path / "bare.md", "Just some text without frontmatter.\n")
