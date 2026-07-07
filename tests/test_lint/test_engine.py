"""Tests for the analysis engine (discover + analyze)."""

from __future__ import annotations

from pathlib import Path

from skill_refine.lint.engine import analyze
from skill_refine.lint.profiles import STANDARD

# No frontmatter 'name' here, so folder/flat identity falls back to the
# directory name / file stem (the frontmatter-name preference is tested below).
_BODY = "---\ndescription: a decent description here now\n---\n\n## Body\n\nstuff\n"


def _mk(path: Path, text: str = _BODY) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_analyze_folder_skill(tmp_path: Path) -> None:
    _mk(tmp_path / "my-skill" / "SKILL.md")
    reports = analyze(tmp_path, STANDARD)
    assert len(reports) == 1
    r = reports[0]
    assert r.skill_format == "folder"
    assert r.name == "my-skill"
    assert r.profile == "standard"
    assert r.skill_dir is not None


def test_analyze_mixed_directory(tmp_path: Path) -> None:
    _mk(tmp_path / "alpha" / "SKILL.md")
    _mk(tmp_path / "legacy.md")
    reports = analyze(tmp_path, STANDARD)
    assert {r.name for r in reports} == {"alpha", "legacy"}


def test_analyze_is_deterministic(tmp_path: Path) -> None:
    _mk(tmp_path / "a" / "SKILL.md")
    _mk(tmp_path / "b.md")
    first = analyze(tmp_path, STANDARD)
    second = analyze(tmp_path, STANDARD)
    assert [r.model_dump() for r in first] == [r.model_dump() for r in second]


def test_flat_skill_name_prefers_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "file-stem.md"
    p.write_text("---\nname: Nice Name\ndescription: a decent description here now\n---\n\nbody\n")
    reports = analyze(p, STANDARD)
    assert reports[0].name == "Nice Name"
