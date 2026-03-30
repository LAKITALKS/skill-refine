"""Tests for backup functionality."""

from pathlib import Path

import pytest

from skill_refine.safety.backup import (
    BackupInfo,
    create_backup,
    find_backups,
    restore_backup,
)


def test_create_backup(tmp_path: Path) -> None:
    original = tmp_path / "skill.md"
    original.write_text("original content")

    backup_path = create_backup(original)

    assert backup_path.exists()
    assert backup_path.read_text() == "original content"
    assert backup_path.suffix == ".bak"
    assert original.exists()


def test_backup_preserves_original(tmp_path: Path) -> None:
    original = tmp_path / "skill.md"
    original.write_text("keep this")

    create_backup(original)

    assert original.read_text() == "keep this"


def test_backup_nonexistent_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        create_backup(tmp_path / "missing.md")


def test_multiple_backups(tmp_path: Path) -> None:
    original = tmp_path / "skill.md"
    original.write_text("v1")
    b1 = create_backup(original)

    original.write_text("v2")
    b2 = create_backup(original)

    assert b1 != b2
    assert b1.read_text() == "v1"
    assert b2.read_text() == "v2"


def test_find_backups(tmp_path: Path) -> None:
    original = tmp_path / "skill.md"
    original.write_text("v1")
    create_backup(original)

    original.write_text("v2")
    create_backup(original)

    backups = find_backups(original)
    assert len(backups) == 2
    # Newest first
    assert backups[0].timestamp >= backups[1].timestamp


def test_find_backups_empty(tmp_path: Path) -> None:
    original = tmp_path / "skill.md"
    original.write_text("no backups")

    backups = find_backups(original)
    assert backups == []


def test_restore_backup(tmp_path: Path) -> None:
    original = tmp_path / "skill.md"
    original.write_text("original")
    backup = create_backup(original)

    original.write_text("modified")
    assert original.read_text() == "modified"

    restore_backup(backup, original)
    assert original.read_text() == "original"


def test_restore_nonexistent_backup(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        restore_backup(tmp_path / "nonexistent.bak", tmp_path / "skill.md")


def test_backup_info_age_label() -> None:
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    info = BackupInfo(path=Path("test.bak"), timestamp=ts, size=100)
    assert "m ago" in info.age_label or "0m ago" in info.age_label
