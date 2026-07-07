"""Tests for the stable JSON schema (2.0) and Markdown rendering."""

from __future__ import annotations

import json
from pathlib import Path

from skill_refine.lint.engine import analyze
from skill_refine.lint.profiles import STANDARD, STRICT
from skill_refine.lint.serialize import (
    SCHEMA_VERSION,
    render_json,
    render_markdown,
)


def _reports(tmp_path: Path, profile=STANDARD):
    (tmp_path / "s.md").write_text(
        "---\nname: Demo\n"
        "description: a description that is clearly long enough\n"
        "---\n\n## Body\n\nstuff here\n",
        encoding="utf-8",
    )
    return analyze(tmp_path, profile)


def test_json_top_level_contract(tmp_path: Path) -> None:
    reports = _reports(tmp_path)
    doc = json.loads(render_json(reports, profile="standard", tool_version="0.2.0"))
    assert doc["schema_version"] == SCHEMA_VERSION == "2.0"
    assert doc["tool"] == "skill-refine"
    assert doc["tool_version"] == "0.2.0"
    assert doc["profile"] == "standard"
    assert "generated_at" in doc
    assert isinstance(doc["skills"], list) and len(doc["skills"]) == 1
    assert doc["summary"]["skill_count"] == 1
    assert set(doc["summary"]["counts"]) == {"error", "warning", "info", "smell"}


def test_json_skill_entry_is_machine_readable(tmp_path: Path) -> None:
    reports = _reports(tmp_path)
    doc = json.loads(render_json(reports, profile="standard", tool_version="0.2.0"))
    skill = doc["skills"][0]
    assert skill["name"] == "Demo"
    assert skill["format"] == "flat"
    assert "path" in skill
    assert isinstance(skill["word_count"], int)
    assert set(skill["score"]["components"]) == {
        "completeness",
        "structure",
        "metadata",
        "conciseness",
    }
    assert isinstance(skill["score"]["total"], (int, float))


def test_json_findings_have_id_and_severity(tmp_path: Path) -> None:
    (tmp_path / "bad" / "SKILL.md").parent.mkdir()
    (tmp_path / "bad" / "SKILL.md").write_text(
        "---\nname: bad\n---\n\nbody\n", encoding="utf-8"
    )
    reports = analyze(tmp_path / "bad" / "SKILL.md", STANDARD)
    doc = json.loads(render_json(reports, profile="standard", tool_version="0.2.0"))
    findings = doc["skills"][0]["findings"]
    assert findings, "expected at least one finding for a skill missing description"
    for f in findings:
        assert set(f) == {"id", "severity", "message", "section"}
        assert f["severity"] in {"error", "warning", "info"}
    ids = {f["id"] for f in findings}
    assert "missing-frontmatter-description" in ids


def test_json_reports_profile_name_used(tmp_path: Path) -> None:
    reports = _reports(tmp_path, STRICT)
    doc = json.loads(render_json(reports, profile="strict", tool_version="0.2.0"))
    assert doc["profile"] == "strict"


def test_markdown_render_contains_key_sections(tmp_path: Path) -> None:
    reports = _reports(tmp_path)
    md = render_markdown(reports, profile="standard")
    assert "# Skill Report" in md
    assert "Profile: `standard`" in md
    assert "### Scores" in md
    assert "### Verdict" in md
