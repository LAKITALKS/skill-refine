"""Tests for restore-related backup operations."""

from pathlib import Path

from skill_refine.safety.backup import create_backup, find_backups, restore_backup


def test_restore_roundtrip(tmp_path: Path) -> None:
    """Create -> modify -> backup -> restore cycle."""
    original = tmp_path / "skill.md"
    original.write_text("version 1")

    # Create backup of v1
    backup = create_backup(original)

    # Modify to v2
    original.write_text("version 2")
    assert original.read_text() == "version 2"

    # Restore v1
    restore_backup(backup, original)
    assert original.read_text() == "version 1"


def test_find_backups_ignores_other_files(tmp_path: Path) -> None:
    """Only .bak files matching the pattern should be found."""
    original = tmp_path / "skill.md"
    original.write_text("content")
    create_backup(original)

    # Create unrelated file
    (tmp_path / "other.bak").write_text("not a skill backup")
    (tmp_path / "skill.txt").write_text("not a backup")

    backups = find_backups(original)
    assert len(backups) == 1


def test_find_backups_sorted_newest_first(tmp_path: Path) -> None:
    original = tmp_path / "skill.md"
    original.write_text("v1")
    create_backup(original)
    original.write_text("v2")
    create_backup(original)
    original.write_text("v3")
    create_backup(original)

    backups = find_backups(original)
    assert len(backups) == 3
    # Newest first
    for i in range(len(backups) - 1):
        assert backups[i].timestamp >= backups[i + 1].timestamp
