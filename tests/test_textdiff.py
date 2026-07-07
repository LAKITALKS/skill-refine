"""Tests for the offline unified-diff helper."""

from skill_refine.textdiff import unified_diff


def test_unified_diff_detects_changes() -> None:
    diff = unified_diff("line 1\nline 2\nline 3\n", "line 1\nline changed\nline 3\n")
    assert "-line 2" in diff
    assert "+line changed" in diff


def test_unified_diff_no_changes() -> None:
    assert unified_diff("same content\n", "same content\n").strip() == ""


def test_unified_diff_additions() -> None:
    diff = unified_diff("line 1\n", "line 1\nline 2\n")
    assert "+line 2" in diff


def test_unified_diff_filename() -> None:
    diff = unified_diff("a\n", "b\n", filename="my-skill.md")
    assert "a/my-skill.md" in diff
    assert "b/my-skill.md" in diff
