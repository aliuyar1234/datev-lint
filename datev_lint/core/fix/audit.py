"""
Audit logging for fix engine.

Logs all fix operations with versions and checksums.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from datev_lint.core.fix.models import (
    AuditEntry,
    AuditPatchEntry,
    PatchPlan,
    WriteResult,
)


class AuditLogger:
    """Logs fix operations for audit trail."""

    def __init__(
        self,
        audit_dir: Path,
        engine_version: str = "0.1.0",
    ):
        """
        Initialize audit logger.

        Args:
            audit_dir: Directory for audit logs
            engine_version: Current engine version
        """
        self.audit_dir = Path(audit_dir)
        self.engine_version = engine_version
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def generate_run_id(self) -> str:
        """Generate a unique run ID."""
        return str(uuid.uuid4())[:12]

    def log_fix(
        self,
        run_id: str,
        plan: PatchPlan,
        result: WriteResult,
        profile_id: str = "default",
        profile_version: str = "1.0.0",
    ) -> AuditEntry:
        """
        Log a fix operation.

        Args:
            run_id: Unique run identifier
            plan: Patch plan that was applied
            result: Write result
            profile_id: ID of profile used
            profile_version: Version of profile

        Returns:
            AuditEntry that was logged
        """
        # Convert patches to audit entries
        patch_entries: list[AuditPatchEntry] = []
        for patch in plan.patches:
            entry = AuditPatchEntry(
                row_no=patch.row_no,
                field=patch.field,
                operation=patch.operation.value,
                old_value=patch.old_value,
                new_value=patch.new_value,
                rule_id=patch.rule_id,
                rule_version=patch.rule_version,
                risk=patch.risk.value,
            )
            patch_entries.append(entry)

        # Create audit entry
        audit_entry = AuditEntry(
            run_id=run_id,
            timestamp=datetime.now(UTC),
            file_path=plan.file_path,
            file_checksum_before=result.old_checksum,
            file_checksum_after=result.new_checksum,
            backup_path=result.backup_path,
            engine_version=self.engine_version,
            profile_id=profile_id,
            profile_version=profile_version,
            patches=patch_entries,
            conflicts_detected=len(plan.conflicts),
            conflicts_resolved=len(plan.conflicts),  # All conflicts resolved by plan
            write_mode=result.mode.value,
            duration_ms=result.duration_ms,
        )

        # Write to file
        self._write_entry(audit_entry)

        return audit_entry

    def log_rollback(
        self,
        run_id: str,
        original_run_id: str,
    ) -> None:
        """
        Log a rollback operation.

        Args:
            run_id: Run ID of the original fix
            original_run_id: Run ID that was rolled back
        """
        # Load original entry
        entry = self.get_entry(original_run_id)
        if entry is None:
            return

        # Update with rollback info
        updated = AuditEntry(
            run_id=entry.run_id,
            timestamp=entry.timestamp,
            file_path=entry.file_path,
            file_checksum_before=entry.file_checksum_before,
            file_checksum_after=entry.file_checksum_after,
            backup_path=entry.backup_path,
            engine_version=entry.engine_version,
            profile_id=entry.profile_id,
            profile_version=entry.profile_version,
            patches=entry.patches,
            conflicts_detected=entry.conflicts_detected,
            conflicts_resolved=entry.conflicts_resolved,
            write_mode=entry.write_mode,
            duration_ms=entry.duration_ms,
            rolled_back=True,
            rollback_timestamp=datetime.now(UTC),
        )

        # Overwrite entry
        self._write_entry(updated)

    def get_entry(self, run_id: str) -> AuditEntry | None:
        """
        Get an audit entry by run ID.

        Args:
            run_id: Run ID to look up

        Returns:
            AuditEntry or None if not found
        """
        entry_path = self._entry_path(run_id)
        if not entry_path.exists():
            return None

        with open(entry_path, encoding="utf-8") as f:
            data = json.load(f)

        return self._dict_to_entry(data)

    def list_entries(
        self,
        file_path: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """
        List audit entries.

        Args:
            file_path: Filter by file path
            limit: Maximum entries to return

        Returns:
            List of audit entries (newest first)
        """
        entries: list[AuditEntry] = []

        for path in sorted(self.audit_dir.glob("*.json"), reverse=True):
            if len(entries) >= limit:
                break

            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                entry = self._dict_to_entry(data)

                if file_path is None or entry.file_path == file_path:
                    entries.append(entry)
            except Exception:
                continue

        return entries

    def _entry_path(self, run_id: str) -> Path:
        """Get file path for an audit entry."""
        return self.audit_dir / f"{run_id}.json"

    def _write_entry(self, entry: AuditEntry) -> None:
        """Write audit entry to file."""
        entry_path = self._entry_path(entry.run_id)

        data = self._entry_to_dict(entry)

        with open(entry_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _entry_to_dict(self, entry: AuditEntry) -> dict[str, Any]:
        """Convert audit entry to dictionary."""
        return {
            "run_id": entry.run_id,
            "timestamp": entry.timestamp.isoformat(),
            "file_path": entry.file_path,
            "file_checksum_before": entry.file_checksum_before,
            "file_checksum_after": entry.file_checksum_after,
            "backup_path": entry.backup_path,
            "engine_version": entry.engine_version,
            "profile_id": entry.profile_id,
            "profile_version": entry.profile_version,
            "patches": [
                {
                    "row_no": p.row_no,
                    "field": p.field,
                    "operation": p.operation,
                    "old_value": p.old_value,
                    "new_value": p.new_value,
                    "rule_id": p.rule_id,
                    "rule_version": p.rule_version,
                    "risk": p.risk,
                }
                for p in entry.patches
            ],
            "conflicts_detected": entry.conflicts_detected,
            "conflicts_resolved": entry.conflicts_resolved,
            "write_mode": entry.write_mode,
            "duration_ms": entry.duration_ms,
            "rolled_back": entry.rolled_back,
            "rollback_timestamp": entry.rollback_timestamp.isoformat() if entry.rollback_timestamp else None,
        }

    def _dict_to_entry(self, data: dict[str, Any]) -> AuditEntry:
        """Convert dictionary to audit entry."""
        patches = [
            AuditPatchEntry(
                row_no=p["row_no"],
                field=p["field"],
                operation=p["operation"],
                old_value=p["old_value"],
                new_value=p["new_value"],
                rule_id=p["rule_id"],
                rule_version=p["rule_version"],
                risk=p["risk"],
            )
            for p in data.get("patches", [])
        ]

        rollback_ts = data.get("rollback_timestamp")
        if rollback_ts:
            rollback_ts = datetime.fromisoformat(rollback_ts)

        return AuditEntry(
            run_id=data["run_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            file_path=data["file_path"],
            file_checksum_before=data["file_checksum_before"],
            file_checksum_after=data["file_checksum_after"],
            backup_path=data.get("backup_path"),
            engine_version=data["engine_version"],
            profile_id=data["profile_id"],
            profile_version=data["profile_version"],
            patches=patches,
            conflicts_detected=data.get("conflicts_detected", 0),
            conflicts_resolved=data.get("conflicts_resolved", 0),
            write_mode=data["write_mode"],
            duration_ms=data.get("duration_ms", 0),
            rolled_back=data.get("rolled_back", False),
            rollback_timestamp=rollback_ts,
        )
