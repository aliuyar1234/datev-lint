"""
Backup management for fix engine.

Handles backup creation, verification, and restoration.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from datev_lint.core.fix.models import RollbackResult
from datev_lint.core.fix.planner import compute_file_checksum

if TYPE_CHECKING:
    from pathlib import Path


class BackupManager:
    """Manages backup files for fix operations."""

    DEFAULT_SUFFIX_FORMAT = ".bak.{timestamp}"

    def __init__(self, backup_dir: Path | None = None):
        """
        Initialize backup manager.

        Args:
            backup_dir: Directory for backups (defaults to same dir as original)
        """
        self.backup_dir = backup_dir

    def create_backup(
        self,
        file_path: Path,
        timestamp: datetime | None = None,
    ) -> Path:
        """
        Create a backup of a file.

        Args:
            file_path: Path to file to backup
            timestamp: Timestamp for backup name (defaults to now)

        Returns:
            Path to backup file
        """
        if timestamp is None:
            timestamp = datetime.now(UTC)

        # Format timestamp for filename (with microseconds for uniqueness)
        ts_str = timestamp.strftime("%Y%m%d%H%M%S") + f"{timestamp.microsecond:06d}"

        # Determine backup path
        if self.backup_dir:
            backup_path = self.backup_dir / f"{file_path.name}.bak.{ts_str}"
        else:
            backup_path = file_path.with_suffix(f"{file_path.suffix}.bak.{ts_str}")

        # Ensure unique path if file already exists
        counter = 0
        while backup_path.exists():
            counter += 1
            if self.backup_dir:
                backup_path = self.backup_dir / f"{file_path.name}.bak.{ts_str}.{counter}"
            else:
                backup_path = file_path.with_suffix(f"{file_path.suffix}.bak.{ts_str}.{counter}")

        # Create backup
        shutil.copy2(file_path, backup_path)

        return backup_path

    def verify_backup(self, backup_path: Path, expected_checksum: str) -> bool:
        """
        Verify backup integrity.

        Args:
            backup_path: Path to backup file
            expected_checksum: Expected checksum

        Returns:
            True if checksums match
        """
        if not backup_path.exists():
            return False

        actual_checksum = compute_file_checksum(backup_path)
        return actual_checksum == expected_checksum

    def restore_backup(
        self,
        backup_path: Path,
        target_path: Path,
        expected_checksum: str | None = None,
        verify: bool = True,
    ) -> RollbackResult:
        """
        Restore a file from backup.

        Args:
            backup_path: Path to backup file
            target_path: Path to restore to
            expected_checksum: Expected checksum of backup
            verify: Whether to verify checksum before restore

        Returns:
            RollbackResult with status
        """
        if not backup_path.exists():
            return RollbackResult(
                success=False,
                file_path=str(target_path),
                backup_path=str(backup_path),
                old_checksum="",
                restored_checksum="",
                expected_checksum=expected_checksum or "",
                checksums_match=False,
                error=f"Backup file not found: {backup_path}",
            )

        # Compute backup checksum
        backup_checksum = compute_file_checksum(backup_path)

        # Verify if requested
        if verify and expected_checksum and backup_checksum != expected_checksum:
            return RollbackResult(
                success=False,
                file_path=str(target_path),
                backup_path=str(backup_path),
                old_checksum="",
                restored_checksum=backup_checksum,
                expected_checksum=expected_checksum,
                checksums_match=False,
                error="Backup checksum mismatch",
            )

        # Get current checksum before restore
        old_checksum = ""
        if target_path.exists():
            old_checksum = compute_file_checksum(target_path)

        # Restore
        try:
            shutil.copy2(backup_path, target_path)
        except Exception as e:
            return RollbackResult(
                success=False,
                file_path=str(target_path),
                backup_path=str(backup_path),
                old_checksum=old_checksum,
                restored_checksum=backup_checksum,
                expected_checksum=expected_checksum or backup_checksum,
                checksums_match=False,
                error=str(e),
            )

        # Verify restored file
        restored_checksum = compute_file_checksum(target_path)
        checksums_match = restored_checksum == backup_checksum

        return RollbackResult(
            success=True,
            file_path=str(target_path),
            backup_path=str(backup_path),
            old_checksum=old_checksum,
            restored_checksum=restored_checksum,
            expected_checksum=expected_checksum or backup_checksum,
            checksums_match=checksums_match,
        )

    def list_backups(self, file_path: Path) -> list[Path]:
        """
        List all backups for a file.

        Args:
            file_path: Original file path

        Returns:
            List of backup paths, sorted by timestamp (newest first)
        """
        if self.backup_dir:
            search_dir = self.backup_dir
            pattern = f"{file_path.name}.bak.*"
        else:
            search_dir = file_path.parent
            pattern = f"{file_path.name}.bak.*"

        backups = list(search_dir.glob(pattern))

        # Sort by modification time (newest first)
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        return backups

    def cleanup_old_backups(
        self,
        file_path: Path,
        keep_count: int = 5,
    ) -> list[Path]:
        """
        Remove old backups, keeping only the most recent.

        Args:
            file_path: Original file path
            keep_count: Number of backups to keep

        Returns:
            List of removed backup paths
        """
        backups = self.list_backups(file_path)
        removed: list[Path] = []

        for backup in backups[keep_count:]:
            backup.unlink()
            removed.append(backup)

        return removed
