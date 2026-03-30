"""Backup utilities for safe file writes and restore."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_BAK_PATTERN = re.compile(r"\.(\d{8}_\d{6})(?:_\d+)?\.bak$")


@dataclass
class BackupInfo:
    path: Path
    timestamp: str
    size: int

    @property
    def age_label(self) -> str:
        try:
            ts = datetime.strptime(self.timestamp, "%Y%m%d_%H%M%S")
            delta = datetime.now() - ts
            if delta.days > 0:
                return f"{delta.days}d ago"
            hours = delta.seconds // 3600
            if hours > 0:
                return f"{hours}h ago"
            minutes = delta.seconds // 60
            return f"{minutes}m ago"
        except ValueError:
            return "unknown"


def create_backup(path: Path) -> Path:
    """Create a .bak copy of the file before overwriting.

    Returns the path to the backup file.
    Raises FileNotFoundError if the original doesn't exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Cannot backup: {path} does not exist")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".{timestamp}.bak")

    counter = 0
    while backup_path.exists():
        counter += 1
        backup_path = path.with_suffix(f".{timestamp}_{counter}.bak")

    shutil.copy2(path, backup_path)
    return backup_path


def find_backups(path: Path) -> list[BackupInfo]:
    """Find all .bak files for the given skill file.

    Returns a list sorted by timestamp, newest first.
    """
    if not path.exists() and not path.parent.exists():
        return []

    parent = path.parent
    stem = path.stem
    backups: list[BackupInfo] = []

    for candidate in parent.iterdir():
        if not candidate.name.startswith(stem):
            continue
        match = _BAK_PATTERN.search(candidate.name)
        if match:
            backups.append(
                BackupInfo(
                    path=candidate,
                    timestamp=match.group(1),
                    size=candidate.stat().st_size,
                )
            )

    backups.sort(key=lambda b: b.timestamp, reverse=True)
    return backups


def restore_backup(backup_path: Path, target_path: Path) -> None:
    """Restore a backup file to the target path.

    Overwrites target_path with the contents of backup_path.
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    shutil.copy2(backup_path, target_path)
