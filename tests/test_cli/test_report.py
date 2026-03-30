"""Tests for report generation."""

import json
from pathlib import Path
from textwrap import dedent

import pytest

from skill_refine.analysis.checker import run_checks
from skill_refine.analysis.scorer import compute_score
from skill_refine.analysis.smells import detect_smells
from skill_refine.core.models import SkillReport
from skill_refine.core.parser import parse_skill


def _make_report(tmp_path: Path, content: str) -> SkillReport:
    p = tmp_path / "test-skill.md"
    p.write_text(content)
    skill = parse_skill(p)
    findings = run_checks(skill)
    smells = detect_smells(skill)
    score = compute_score(skill)
    return SkillReport(skill=skill, findings=findings, smells=smells, score=score)


@pytest.fixture
def sample_report(tmp_path: Path) -> SkillReport:
    content = dedent("""\
        ---
        name: Sample
        description: A sample skill
        tags: [test]
        ---

        ## Description

        This is a sample skill for testing report generation.

        ## Steps

        1. Do something.
    """)
    return _make_report(tmp_path, content)


def test_json_report_structure(sample_report: SkillReport) -> None:
    from skill_refine.cli.report import _render_json
    raw = _render_json([sample_report])
    data = json.loads(raw)
    assert isinstance(data, list)
    assert len(data) == 1
    entry = data[0]
    assert "file" in entry
    assert "score" in entry
    assert "findings" in entry
    assert "smells" in entry
    assert "sections" in entry
    assert "verdict" in entry
    assert entry["score"]["total"] >= 0


def test_json_report_multiple(tmp_path: Path) -> None:
    from skill_refine.cli.report import _render_json
    reports = []
    for name in ("a", "b"):
        content = f"---\nname: {name}\n---\n\n## Description\n\nContent for {name} skill.\n"
        reports.append(_make_report(tmp_path, content))

    raw = _render_json(reports)
    data = json.loads(raw)
    assert len(data) == 2


def test_markdown_report_contains_key_sections(sample_report: SkillReport) -> None:
    from skill_refine.cli.report import _render_markdown
    md = _render_markdown([sample_report])
    assert "# Skill Report" in md
    assert "## Sample" in md
    assert "### Scores" in md
    assert "### Findings" in md
    assert "### Verdict" in md
    assert "Completeness" in md


def test_markdown_report_summary_table(tmp_path: Path) -> None:
    from skill_refine.cli.report import _render_markdown
    reports = []
    for name in ("a", "b"):
        content = f"---\nname: {name}\n---\n\n## Description\n\nContent for {name}.\n"
        reports.append(_make_report(tmp_path, content))

    md = _render_markdown(reports)
    assert "## Summary" in md
    assert "| File " in md
