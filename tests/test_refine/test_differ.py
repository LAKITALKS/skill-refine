"""Tests for differ functionality."""

from skill_refine.refine.differ import unified_diff


def test_unified_diff_detects_changes() -> None:
    original = "line 1\nline 2\nline 3\n"
    rewritten = "line 1\nline changed\nline 3\n"
    diff = unified_diff(original, rewritten)
    assert "-line 2" in diff
    assert "+line changed" in diff


def test_unified_diff_no_changes() -> None:
    text = "same content\n"
    diff = unified_diff(text, text)
    assert diff.strip() == ""


def test_unified_diff_additions() -> None:
    original = "line 1\n"
    rewritten = "line 1\nline 2\n"
    diff = unified_diff(original, rewritten)
    assert "+line 2" in diff


def test_unified_diff_filename() -> None:
    diff = unified_diff("a\n", "b\n", filename="my-skill.md")
    assert "a/my-skill.md" in diff
    assert "b/my-skill.md" in diff
