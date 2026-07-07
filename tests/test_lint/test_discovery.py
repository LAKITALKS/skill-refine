"""Tests for skill discovery (folder-based Agent Skills + legacy flat)."""

from __future__ import annotations

from pathlib import Path

from skill_refine.lint.discovery import discover


def _mk(path: Path, text: str = "---\nname: x\ndescription: y\n---\n\nbody\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_single_flat_file(tmp_path: Path) -> None:
    p = tmp_path / "solo.md"
    _mk(p)
    found = discover(p)
    assert len(found) == 1
    assert found[0].skill_format == "flat"
    assert found[0].name == "solo"
    assert found[0].skill_dir is None


def test_single_skill_md_is_folder(tmp_path: Path) -> None:
    p = tmp_path / "my-skill" / "SKILL.md"
    _mk(p)
    found = discover(p)
    assert len(found) == 1
    assert found[0].skill_format == "folder"
    assert found[0].name == "my-skill"
    assert found[0].skill_dir == p.parent


def test_non_markdown_file_ignored(tmp_path: Path) -> None:
    p = tmp_path / "notes.txt"
    _mk(p)
    assert discover(p) == []


def test_directory_finds_folder_and_flat(tmp_path: Path) -> None:
    _mk(tmp_path / "alpha" / "SKILL.md")
    _mk(tmp_path / "beta" / "SKILL.md")
    _mk(tmp_path / "legacy.md")
    found = discover(tmp_path)
    names = sorted(s.name for s in found)
    assert names == ["alpha", "beta", "legacy"]
    formats = {s.name: s.skill_format for s in found}
    assert formats["alpha"] == "folder"
    assert formats["legacy"] == "flat"


def test_directory_recurses_for_skill_md(tmp_path: Path) -> None:
    _mk(tmp_path / "nested" / "deep" / "SKILL.md")
    found = discover(tmp_path)
    assert len(found) == 1
    assert found[0].name == "deep"
    assert found[0].skill_format == "folder"


def test_top_level_skill_md_not_double_counted(tmp_path: Path) -> None:
    _mk(tmp_path / "SKILL.md")
    found = discover(tmp_path)
    # The top-level SKILL.md is a folder skill named after tmp_path, once.
    assert len(found) == 1
    assert found[0].skill_format == "folder"


def test_results_are_sorted_and_stable(tmp_path: Path) -> None:
    _mk(tmp_path / "c.md")
    _mk(tmp_path / "a.md")
    _mk(tmp_path / "b.md")
    found = discover(tmp_path)
    assert [s.path for s in found] == sorted(s.path for s in found)


def test_flat_files_found_recursively(tmp_path: Path) -> None:
    # Mirrors examples/ -> examples/skills/*.md living one level down.
    _mk(tmp_path / "skills" / "one.md")
    _mk(tmp_path / "skills" / "two.md")
    found = discover(tmp_path)
    assert sorted(s.name for s in found) == ["one", "two"]
    assert all(s.skill_format == "flat" for s in found)


def test_support_markdown_inside_folder_skill_ignored(tmp_path: Path) -> None:
    _mk(tmp_path / "my-skill" / "SKILL.md")
    _mk(tmp_path / "my-skill" / "notes.md")  # supporting file, not a skill
    _mk(tmp_path / "my-skill" / "reference" / "deep.md")  # nested support file
    found = discover(tmp_path)
    assert len(found) == 1
    assert found[0].name == "my-skill"
    assert found[0].skill_format == "folder"


def test_common_docs_excluded(tmp_path: Path) -> None:
    _mk(tmp_path / "README.md")
    _mk(tmp_path / "CHANGELOG.md")
    _mk(tmp_path / "real-skill.md")
    found = discover(tmp_path)
    assert [s.name for s in found] == ["real-skill"]


def test_ignored_and_hidden_dirs_not_scanned(tmp_path: Path) -> None:
    _mk(tmp_path / ".venv" / "lib" / "pkg.md")
    _mk(tmp_path / "node_modules" / "dep" / "SKILL.md")
    _mk(tmp_path / ".archive" / "old.md")
    _mk(tmp_path / ".hidden" / "secret.md")
    _mk(tmp_path / "keep.md")
    found = discover(tmp_path)
    assert [s.name for s in found] == ["keep"]


def test_depth_limit_respected(tmp_path: Path) -> None:
    from skill_refine.lint.discovery import MAX_DEPTH

    too_deep = tmp_path.joinpath(*[f"lvl{i}" for i in range(MAX_DEPTH + 2)]) / "x.md"
    _mk(too_deep)
    _mk(tmp_path / "shallow.md")
    found = discover(tmp_path)
    names = {s.name for s in found}
    assert "shallow" in names
    assert "x" not in names
