"""Tests for audit logging."""

from pathlib import Path

from datev_lint.core.fix.audit import AuditLogger
from datev_lint.core.fix.models import (
    Patch,
    PatchOperation,
    PatchPlan,
    WriteMode,
    WriteResult,
)
from datev_lint.core.rules.models import RiskLevel


def make_patch() -> Patch:
    """Create a test patch."""
    return Patch(
        row_no=3,
        field="belegfeld1",
        operation=PatchOperation.UPPER,
        old_value="test",
        new_value="TEST",
        risk=RiskLevel.LOW,
        rule_id="DVL-TEST-001",
        rule_version="1.0.0",
    )


def make_plan(patches: list[Patch] | None = None) -> PatchPlan:
    """Create a test plan."""
    if patches is None:
        patches = [make_patch()]
    return PatchPlan(
        file_path="test.csv",
        file_checksum="abc123",
        patches=patches,
        conflicts=[],
        low_risk_count=len([p for p in patches if p.risk == RiskLevel.LOW]),
    )


def make_result() -> WriteResult:
    """Create a test write result."""
    return WriteResult(
        success=True,
        output_path="test.csv",
        backup_path="test.csv.bak.20250101120000",
        old_checksum="abc123",
        new_checksum="def456",
        mode=WriteMode.PRESERVE,
        patches_applied=1,
        duration_ms=100,
    )


class TestAuditLogger:
    """Tests for AuditLogger."""

    def test_generate_run_id(self, tmp_path: Path) -> None:
        """Test generating run ID."""
        logger = AuditLogger(audit_dir=tmp_path)
        run_id = logger.generate_run_id()

        assert len(run_id) == 12
        assert run_id.replace("-", "").isalnum()

    def test_log_fix(self, tmp_path: Path) -> None:
        """Test logging a fix operation."""
        logger = AuditLogger(audit_dir=tmp_path)
        run_id = logger.generate_run_id()

        plan = make_plan()
        result = make_result()

        entry = logger.log_fix(
            run_id=run_id,
            plan=plan,
            result=result,
            profile_id="default",
            profile_version="1.0.0",
        )

        assert entry.run_id == run_id
        assert entry.file_path == "test.csv"
        assert entry.file_checksum_before == "abc123"
        assert entry.file_checksum_after == "def456"
        assert len(entry.patches) == 1

        # Verify file was written
        entry_path = tmp_path / f"{run_id}.json"
        assert entry_path.exists()

    def test_get_entry(self, tmp_path: Path) -> None:
        """Test getting an entry by run ID."""
        logger = AuditLogger(audit_dir=tmp_path)
        run_id = logger.generate_run_id()

        plan = make_plan()
        result = make_result()

        logger.log_fix(run_id=run_id, plan=plan, result=result)

        # Retrieve entry
        entry = logger.get_entry(run_id)

        assert entry is not None
        assert entry.run_id == run_id
        assert entry.file_path == "test.csv"

    def test_get_entry_not_found(self, tmp_path: Path) -> None:
        """Test getting non-existent entry."""
        logger = AuditLogger(audit_dir=tmp_path)
        entry = logger.get_entry("nonexistent")
        assert entry is None

    def test_get_entry_rejects_path_traversal(self, tmp_path: Path) -> None:
        """Test that unsafe run IDs are rejected."""
        logger = AuditLogger(audit_dir=tmp_path)
        entry = logger.get_entry("../evil")
        assert entry is None

    def test_list_entries(self, tmp_path: Path) -> None:
        """Test listing entries."""
        logger = AuditLogger(audit_dir=tmp_path)
        plan = make_plan()
        result = make_result()

        # Create multiple entries
        for _ in range(3):
            run_id = logger.generate_run_id()
            logger.log_fix(run_id=run_id, plan=plan, result=result)

        entries = logger.list_entries()
        assert len(entries) == 3

    def test_list_entries_with_filter(self, tmp_path: Path) -> None:
        """Test listing entries with file filter."""
        logger = AuditLogger(audit_dir=tmp_path)
        result = make_result()

        # Create entries for different files
        plan1 = PatchPlan(
            file_path="file1.csv",
            file_checksum="abc",
            patches=[make_patch()],
            conflicts=[],
        )
        plan2 = PatchPlan(
            file_path="file2.csv",
            file_checksum="def",
            patches=[make_patch()],
            conflicts=[],
        )

        logger.log_fix(run_id=logger.generate_run_id(), plan=plan1, result=result)
        logger.log_fix(run_id=logger.generate_run_id(), plan=plan2, result=result)

        entries = logger.list_entries(file_path="file1.csv")
        assert len(entries) == 1
        assert entries[0].file_path == "file1.csv"

    def test_log_rollback(self, tmp_path: Path) -> None:
        """Test logging a rollback."""
        logger = AuditLogger(audit_dir=tmp_path)
        run_id = logger.generate_run_id()

        plan = make_plan()
        result = make_result()

        logger.log_fix(run_id=run_id, plan=plan, result=result)
        logger.log_rollback(run_id=run_id, original_run_id=run_id)

        # Retrieve and check rollback flag
        entry = logger.get_entry(run_id)
        assert entry is not None
        assert entry.rolled_back is True
        assert entry.rollback_timestamp is not None
