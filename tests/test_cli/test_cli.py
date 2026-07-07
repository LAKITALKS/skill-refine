"""End-to-end CLI tests via Typer's CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from skill_refine.cli.main import app

runner = CliRunner()

_GOOD = (
    "---\n"
    "name: Demo Skill\n"
    "description: A clear description that is comfortably long enough to pass\n"
    "---\n\n"
    "## Overview\n\nDoes a specific, well-defined thing.\n\n"
    "## How it works\n\n- step one\n- step two\n"
)

_NO_DESCRIPTION = "---\nname: nodesc\n---\n\n## Body\n\nstuff\n"


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_check_runs(tmp_path: Path) -> None:
    skill = _write(tmp_path, "demo.md", _GOOD)
    result = runner.invoke(app, ["check", str(skill)])
    assert result.exit_code == 0
    assert "Skill Check" in result.stdout


def test_check_json_has_schema_version(tmp_path: Path) -> None:
    skill = _write(tmp_path, "demo.md", _GOOD)
    result = runner.invoke(app, ["check", str(skill), "--json"])
    assert result.exit_code == 0
    assert '"schema_version": "2.0"' in result.stdout
    assert '"profile": "standard"' in result.stdout


def test_check_strict_profile(tmp_path: Path) -> None:
    skill = _write(tmp_path, "demo.md", _GOOD)
    result = runner.invoke(app, ["check", str(skill), "--profile", "strict", "--json"])
    assert result.exit_code == 0
    assert '"profile": "strict"' in result.stdout


def test_check_unknown_profile_exits_2(tmp_path: Path) -> None:
    skill = _write(tmp_path, "demo.md", _GOOD)
    result = runner.invoke(app, ["check", str(skill), "--profile", "bogus"])
    assert result.exit_code == 2


def test_check_fail_on_error(tmp_path: Path) -> None:
    skill = _write(tmp_path, "nodesc.md", _NO_DESCRIPTION)
    ok = runner.invoke(app, ["check", str(skill)])
    assert ok.exit_code == 0  # no --fail-on: never fails
    failed = runner.invoke(app, ["check", str(skill), "--fail-on", "error"])
    assert failed.exit_code == 1  # standard makes missing description an error


def test_check_directory_of_skills(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", _GOOD)
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "SKILL.md").write_text(_GOOD, encoding="utf-8")
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 0
    assert "Summary" in result.stdout


def test_report_json_to_file(tmp_path: Path) -> None:
    skill = _write(tmp_path, "demo.md", _GOOD)
    out = tmp_path / "report.json"
    result = runner.invoke(
        app, ["report", str(skill), "--format", "json", "--output", str(out)]
    )
    assert result.exit_code == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "2.0"
    assert doc["skills"][0]["name"] == "Demo Skill"


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.2.0" in result.stdout


def test_improve_stub_refused_without_allow_flag(tmp_path: Path) -> None:
    pytest.importorskip("httpx", reason="LLM extra not installed")
    skill = _write(tmp_path, "demo.md", _GOOD)
    before = skill.read_text(encoding="utf-8")
    result = runner.invoke(
        app, ["improve", str(skill), "--provider", "stub", "--dry-run"]
    )
    assert result.exit_code != 0
    assert "stub" in result.stdout.lower()
    assert skill.read_text(encoding="utf-8") == before  # unchanged


def test_improve_dry_run_with_stub_allowed(tmp_path: Path) -> None:
    pytest.importorskip("httpx", reason="LLM extra not installed")
    skill = _write(tmp_path, "demo.md", _GOOD)
    before = skill.read_text(encoding="utf-8")
    result = runner.invoke(
        app,
        ["improve", str(skill), "--provider", "stub", "--allow-stub", "--dry-run"],
    )
    assert result.exit_code == 0
    assert "Dry run" in result.stdout
    assert skill.read_text(encoding="utf-8") == before  # unchanged


def test_improve_refuses_without_provider(tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("httpx", reason="LLM extra not installed")
    import skill_refine.llm.providers.factory as factory

    # No real provider available and stub is not auto-selected: improve must
    # refuse rather than fabricate an improvement.
    monkeypatch.setattr(
        factory, "auto_select_provider", lambda include_stub=False: None
    )
    skill = _write(tmp_path, "demo.md", _GOOD)
    before = skill.read_text(encoding="utf-8")
    result = runner.invoke(app, ["improve", str(skill), "--dry-run"])
    assert result.exit_code != 0
    assert "provider" in result.stdout.lower()
    assert skill.read_text(encoding="utf-8") == before  # unchanged
