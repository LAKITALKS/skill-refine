"""Discovery of skill files: folder-based Agent Skills and legacy flat Markdown.

A folder-based Agent Skill is a directory containing a ``SKILL.md`` file; the
skill's identity is the directory name. Legacy flat skills are plain ``.md``
files. Both are supported.

Discovery rules for a directory target:
- Every ``SKILL.md`` found (recursively, up to ``MAX_DEPTH``) is a folder skill.
- Other ``*.md`` files are legacy flat skills, EXCEPT:
    * files inside a folder-skill directory tree (they are treated as the
      skill's supporting files, not standalone skills);
    * common project docs (README, CHANGELOG, LICENSE, ...).
- Hidden directories (``.git``, ``.archive`` etc.) and heavy build/vendor
  directories (``.venv``, ``node_modules`` ...) are never descended into.
- Traversal stops at ``MAX_DEPTH`` levels below the target to avoid scanning
  arbitrarily deep trees.

Part of the offline, deterministic lint core: no LLM/provider/network imports.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SKILL_FILENAME = "SKILL.md"

#: How many directory levels below the target we are willing to descend.
MAX_DEPTH = 5

#: Directories we never descend into (in addition to any dotted directory).
IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        ".env",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".archive",
        "dist",
        "build",
        ".eggs",
        "site-packages",
        ".tox",
        ".idea",
        ".vscode",
    }
)

#: Flat markdown filenames that are project docs, not skills (case-insensitive).
NON_SKILL_DOCS: frozenset[str] = frozenset(
    {
        "readme.md",
        "changelog.md",
        "contributing.md",
        "license.md",
        "code_of_conduct.md",
        "security.md",
    }
)


@dataclass(frozen=True)
class SkillFile:
    """A located skill file plus its structural identity."""

    path: Path  # the .md file itself
    skill_format: str  # "folder" | "flat"
    skill_dir: Path | None  # the skill directory for folder skills, else None
    name: str  # directory name (folder) or file stem (flat)


def discover(path: Path) -> list[SkillFile]:
    """Discover skill files under ``path``.

    - A single file: classified as a folder skill (if named ``SKILL.md``) or a
      flat skill (any other ``.md``).
    - A directory: folder skills (``SKILL.md``) and legacy flat skills, applying
      the rules documented in this module. Results are de-duplicated and
      returned in a stable, path-sorted order.
    """
    if path.is_file():
        sf = _classify_file(path)
        return [sf] if sf else []

    if not path.is_dir():
        return []

    markdown = list(_iter_markdown(path))
    skill_dirs = {md.parent for md in markdown if md.name == SKILL_FILENAME}

    seen: set[Path] = set()
    results: list[SkillFile] = []

    for md in markdown:
        resolved = md.resolve()
        if resolved in seen:
            continue

        if md.name == SKILL_FILENAME:
            seen.add(resolved)
            results.append(
                SkillFile(
                    path=md,
                    skill_format="folder",
                    skill_dir=md.parent,
                    name=md.parent.name,
                )
            )
            continue

        # A non-SKILL.md file: only a flat skill if it is not a supporting file
        # inside a folder skill and not a common project document.
        if any(ancestor in skill_dirs for ancestor in md.parents):
            continue
        if md.name.lower() in NON_SKILL_DOCS:
            continue

        seen.add(resolved)
        results.append(
            SkillFile(path=md, skill_format="flat", skill_dir=None, name=md.stem)
        )

    results.sort(key=lambda s: str(s.path))
    return results


def _iter_markdown(root: Path) -> list[Path]:
    """Yield ``*.md`` files under ``root``, pruning ignored/hidden dirs and depth."""
    base_depth = len(root.parts)
    found: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        depth = len(current.parts) - base_depth

        # Prune: don't descend past MAX_DEPTH, and skip hidden/ignored dirs.
        if depth >= MAX_DEPTH:
            dirnames[:] = []
        else:
            dirnames[:] = [
                d
                for d in dirnames
                if d not in IGNORE_DIRS and not d.startswith(".")
            ]

        for filename in filenames:
            if filename.endswith(".md"):
                found.append(current / filename)

    return found


def _classify_file(path: Path) -> SkillFile | None:
    if path.suffix != ".md":
        return None
    if path.name == SKILL_FILENAME:
        return SkillFile(
            path=path,
            skill_format="folder",
            skill_dir=path.parent,
            name=path.parent.name,
        )
    return SkillFile(path=path, skill_format="flat", skill_dir=None, name=path.stem)
