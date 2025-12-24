"""
Fix Engine for DATEV Lint.

Public API for applying fixes to DATEV files.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from datev_lint.core.fix.audit import AuditLogger
from datev_lint.core.fix.backup import BackupManager
from datev_lint.core.fix.conflicts import detect_conflicts
from datev_lint.core.fix.models import (
    AuditEntry,
    Conflict,
    ConflictResolution,
    Patch,
    PatchOperation,
    PatchPlan,
    RollbackResult,
    WriteMode,
    WriteResult,
)
from datev_lint.core.fix.operations import OperationRegistry
from datev_lint.core.fix.planner import PatchPlanner, compute_file_checksum, plan_fixes
from datev_lint.core.fix.preview import DiffOutput, preview_diff, preview_patch
from datev_lint.core.fix.risk import (
    filter_by_risk,
    format_risk_warning,
    get_risk_summary,
    requires_interactive_approval,
    should_apply,
)
from datev_lint.core.fix.writer import get_writer, write_file
from datev_lint.core.rules.models import RiskLevel

if TYPE_CHECKING:
    from datev_lint.core.parser.models import ParseResult
    from datev_lint.core.rules.pipeline import PipelineResult


# Default paths
DEFAULT_AUDIT_DIR = Path("audit")


# =============================================================================
# Public API Functions
# =============================================================================


def plan(
    file_path: str | Path,
    result: "PipelineResult",
    resolution: ConflictResolution = ConflictResolution.FIRST_WINS,
) -> PatchPlan:
    """
    Generate a patch plan from validation results.

    Args:
        file_path: Path to the file to fix
        result: Validation pipeline result with findings
        resolution: How to resolve conflicts

    Returns:
        PatchPlan with patches and conflicts
    """
    return plan_fixes(file_path, result, resolution)


def preview(plan: PatchPlan, colorize: bool = True) -> str:
    """
    Generate a preview diff of patches.

    Args:
        plan: Patch plan to preview
        colorize: Add ANSI colors

    Returns:
        Formatted diff string
    """
    return preview_diff(plan, colorize)


def apply_fixes(
    plan: PatchPlan,
    parse_result: "ParseResult",
    mode: WriteMode = WriteMode.PRESERVE,
    create_backup: bool = True,
    audit_dir: Path | None = None,
    accept_risk: RiskLevel = RiskLevel.LOW,
    profile_id: str = "default",
    profile_version: str = "1.0.0",
) -> tuple[WriteResult, AuditEntry | None]:
    """
    Apply fixes to a file.

    Args:
        plan: Patch plan to apply
        parse_result: Original parse result
        mode: Write mode (preserve or canonical)
        create_backup: Create backup before write
        audit_dir: Directory for audit logs
        accept_risk: Maximum risk level to apply without confirmation
        profile_id: Profile ID for audit
        profile_version: Profile version for audit

    Returns:
        Tuple of (WriteResult, AuditEntry or None)
    """
    from datev_lint.core.parser import parse_file

    file_path = Path(plan.file_path)

    # Filter patches by risk
    accepted_patches = filter_by_risk(plan, accept_risk)

    # Create filtered plan
    filtered_plan = PatchPlan(
        file_path=plan.file_path,
        file_checksum=plan.file_checksum,
        patches=accepted_patches,
        conflicts=plan.conflicts,
        low_risk_count=sum(1 for p in accepted_patches if p.risk == RiskLevel.LOW),
        medium_risk_count=sum(1 for p in accepted_patches if p.risk == RiskLevel.MEDIUM),
        high_risk_count=sum(1 for p in accepted_patches if p.risk == RiskLevel.HIGH),
        requires_approval=any(p.requires_approval for p in accepted_patches),
    )

    # Setup backup
    backup_path = None
    if create_backup:
        backup_mgr = BackupManager()
        backup_path = backup_mgr.create_backup(file_path)

    # Write file
    result = write_file(
        filtered_plan,
        parse_result,
        output_path=file_path,
        mode=mode,
        backup_path=backup_path,
        atomic=True,
    )

    # Create audit entry
    audit_entry = None
    if result.success:
        if audit_dir is None:
            audit_dir = file_path.parent / "audit"
        audit_logger = AuditLogger(audit_dir)
        run_id = audit_logger.generate_run_id()
        audit_entry = audit_logger.log_fix(
            run_id=run_id,
            plan=filtered_plan,
            result=result,
            profile_id=profile_id,
            profile_version=profile_version,
        )

    return result, audit_entry


def apply_fixes_interactive(
    plan: PatchPlan,
    parse_result: "ParseResult",
    mode: WriteMode = WriteMode.PRESERVE,
    audit_dir: Path | None = None,
    profile_id: str = "default",
    profile_version: str = "1.0.0",
) -> tuple[WriteResult, AuditEntry | None] | None:
    """
    Apply fixes with interactive approval for high-risk patches.

    This is a placeholder for CLI integration.

    Args:
        plan: Patch plan to apply
        parse_result: Original parse result
        mode: Write mode
        audit_dir: Audit directory
        profile_id: Profile ID
        profile_version: Profile version

    Returns:
        Tuple of (WriteResult, AuditEntry) or None if cancelled
    """
    # Check if approval needed
    if requires_interactive_approval(plan):
        # In a real CLI, this would prompt the user
        # For now, we just proceed with high risk level
        pass

    return apply_fixes(
        plan,
        parse_result,
        mode=mode,
        create_backup=True,
        audit_dir=audit_dir,
        accept_risk=RiskLevel.HIGH,
        profile_id=profile_id,
        profile_version=profile_version,
    )


def rollback(
    run_id: str,
    audit_dir: Path | None = None,
) -> RollbackResult:
    """
    Rollback a fix operation by run ID.

    Args:
        run_id: Run ID from apply operation
        audit_dir: Directory containing audit logs

    Returns:
        RollbackResult with status
    """
    if audit_dir is None:
        audit_dir = DEFAULT_AUDIT_DIR

    # Load audit entry
    audit_logger = AuditLogger(audit_dir)
    entry = audit_logger.get_entry(run_id)

    if entry is None:
        return RollbackResult(
            success=False,
            file_path="",
            backup_path="",
            old_checksum="",
            restored_checksum="",
            expected_checksum="",
            checksums_match=False,
            error=f"Run ID not found: {run_id}",
        )

    if entry.backup_path is None:
        return RollbackResult(
            success=False,
            file_path=entry.file_path,
            backup_path="",
            old_checksum="",
            restored_checksum="",
            expected_checksum=entry.file_checksum_before,
            checksums_match=False,
            error="No backup available for this run",
        )

    # Restore from backup
    backup_mgr = BackupManager()
    result = backup_mgr.restore_backup(
        backup_path=Path(entry.backup_path),
        target_path=Path(entry.file_path),
        expected_checksum=entry.file_checksum_before,
        verify=True,
    )

    # Log rollback
    if result.success:
        audit_logger.log_rollback(run_id, run_id)

    return result


def get_audit_entry(run_id: str, audit_dir: Path | None = None) -> AuditEntry | None:
    """
    Get an audit entry by run ID.

    Args:
        run_id: Run ID to look up
        audit_dir: Audit directory

    Returns:
        AuditEntry or None
    """
    if audit_dir is None:
        audit_dir = DEFAULT_AUDIT_DIR
    audit_logger = AuditLogger(audit_dir)
    return audit_logger.get_entry(run_id)


def list_audit_entries(
    file_path: str | None = None,
    audit_dir: Path | None = None,
    limit: int = 100,
) -> list[AuditEntry]:
    """
    List audit entries.

    Args:
        file_path: Filter by file path
        audit_dir: Audit directory
        limit: Maximum entries

    Returns:
        List of audit entries
    """
    if audit_dir is None:
        audit_dir = DEFAULT_AUDIT_DIR
    audit_logger = AuditLogger(audit_dir)
    return audit_logger.list_entries(file_path, limit)


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    # Functions
    "plan",
    "plan_fixes",
    "preview",
    "preview_diff",
    "preview_patch",
    "apply_fixes",
    "apply_fixes_interactive",
    "rollback",
    "get_audit_entry",
    "list_audit_entries",
    "filter_by_risk",
    "should_apply",
    "get_risk_summary",
    "format_risk_warning",
    "requires_interactive_approval",
    "detect_conflicts",
    "compute_file_checksum",
    # Models
    "Patch",
    "PatchPlan",
    "PatchOperation",
    "Conflict",
    "ConflictResolution",
    "WriteMode",
    "WriteResult",
    "RollbackResult",
    "AuditEntry",
    "DiffOutput",
    # Classes
    "PatchPlanner",
    "BackupManager",
    "AuditLogger",
    "OperationRegistry",
    "RiskLevel",
]
