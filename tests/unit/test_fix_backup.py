"""Tests for backup manager."""

from pathlib import Path

import pytest

from datev_lint.core.fix.backup import BackupManager
from datev_lint.core.fix.planner import compute_file_checksum


class TestBackupManager:
    """Tests for BackupManager."""

    def test_create_backup(self, tmp_path: Path) -> None:
        """Test creating a backup."""
        # Create test file
        test_file = tmp_path / "test.csv"
        test_file.write_text("test content")

        manager = BackupManager()
        backup_path = manager.create_backup(test_file)

        assert backup_path.exists()
        assert backup_path.read_text() == "test content"
        assert ".bak." in backup_path.name

    def test_create_backup_custom_dir(self, tmp_path: Path) -> None:
        """Test creating backup in custom directory."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("test content")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        manager = BackupManager(backup_dir=backup_dir)
        backup_path = manager.create_backup(test_file)

        assert backup_path.parent == backup_dir
        assert backup_path.exists()

    def test_verify_backup_valid(self, tmp_path: Path) -> None:
        """Test verifying a valid backup."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("test content")

        manager = BackupManager()
        backup_path = manager.create_backup(test_file)
        checksum = compute_file_checksum(backup_path)

        assert manager.verify_backup(backup_path, checksum) is True

    def test_verify_backup_invalid(self, tmp_path: Path) -> None:
        """Test verifying an invalid backup."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("test content")

        manager = BackupManager()
        backup_path = manager.create_backup(test_file)

        assert manager.verify_backup(backup_path, "wrong_checksum") is False

    def test_verify_backup_missing(self, tmp_path: Path) -> None:
        """Test verifying missing backup."""
        manager = BackupManager()
        result = manager.verify_backup(tmp_path / "nonexistent.bak", "checksum")
        assert result is False

    def test_restore_backup(self, tmp_path: Path) -> None:
        """Test restoring from backup."""
        # Create and modify file
        test_file = tmp_path / "test.csv"
        test_file.write_text("original content")
        original_checksum = compute_file_checksum(test_file)

        manager = BackupManager()
        backup_path = manager.create_backup(test_file)

        # Modify file
        test_file.write_text("modified content")

        # Restore
        result = manager.restore_backup(
            backup_path=backup_path,
            target_path=test_file,
            expected_checksum=original_checksum,
        )

        assert result.success
        assert result.checksums_match
        assert test_file.read_text() == "original content"

    def test_restore_backup_missing(self, tmp_path: Path) -> None:
        """Test restoring from missing backup."""
        manager = BackupManager()
        result = manager.restore_backup(
            backup_path=tmp_path / "nonexistent.bak",
            target_path=tmp_path / "test.csv",
            expected_checksum="checksum",
        )

        assert not result.success
        assert "not found" in result.error

    def test_list_backups(self, tmp_path: Path) -> None:
        """Test listing backups."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("test content")

        manager = BackupManager()

        # Create multiple backups
        backup1 = manager.create_backup(test_file)
        backup2 = manager.create_backup(test_file)

        backups = manager.list_backups(test_file)

        assert len(backups) == 2
        assert backup2 in backups  # Most recent first
        assert backup1 in backups

    def test_cleanup_old_backups(self, tmp_path: Path) -> None:
        """Test cleaning up old backups."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("test content")

        manager = BackupManager()

        # Create multiple backups
        for _ in range(5):
            manager.create_backup(test_file)

        # Keep only 2
        removed = manager.cleanup_old_backups(test_file, keep_count=2)

        assert len(removed) == 3
        remaining = manager.list_backups(test_file)
        assert len(remaining) == 2
