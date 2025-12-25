"""
Fix Engine data models.

Core models for patches, audit, and write operations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

from datev_lint.core.rules.models import RiskLevel


def _utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(UTC)


# =============================================================================
# Enums
# =============================================================================


class PatchOperation(Enum):
    """Patch operation types."""

    SET_FIELD = "set_field"
    NORMALIZE_DECIMAL = "normalize_decimal"
    TRUNCATE = "truncate"
    SANITIZE_CHARS = "sanitize_chars"
    UPPER = "upper"
    DELETE_ROW = "delete_row"
    SPLIT_FILE = "split_file"


class WriteMode(Enum):
    """Writer modes."""

    PRESERVE = "preserve"  # Minimal diffs, keep original formatting
    CANONICAL = "canonical"  # Standardized output


class ConflictResolution(Enum):
    """Conflict resolution strategies."""

    FIRST_WINS = "first_wins"
    LAST_WINS = "last_wins"
    MANUAL = "manual"


# =============================================================================
# Patch Models
# =============================================================================


class Patch(BaseModel, frozen=True):
    """Single patch operation."""

    row_no: int = Field(ge=3, description="Row number (1-indexed, data starts at row 3)")
    field: str = Field(description="Field name to modify")
    operation: PatchOperation = Field(description="Patch operation type")
    old_value: str = Field(description="Original value")
    new_value: str = Field(description="New value after patch")
    risk: RiskLevel = Field(default=RiskLevel.MEDIUM)
    requires_approval: bool = Field(default=False)

    # Source information
    rule_id: str = Field(description="Rule that triggered this patch")
    rule_version: str = Field(description="Version of the rule")

    model_config = {"frozen": True}


class Conflict(BaseModel, frozen=True):
    """Conflict between patches."""

    row_no: int = Field(description="Row where conflict occurred")
    field: str = Field(description="Field with conflict")
    patches: list[Patch] = Field(description="Conflicting patches")
    resolution: ConflictResolution = Field(default=ConflictResolution.FIRST_WINS)
    selected_patch: Patch | None = Field(default=None)

    model_config = {"frozen": True}


class PatchPlan(BaseModel, frozen=True):
    """Complete patch plan for a file."""

    file_path: str = Field(description="Path to file being patched")
    file_checksum: str = Field(description="Checksum of original file")

    patches: list[Patch] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)

    # Counts by risk level
    low_risk_count: int = Field(default=0)
    medium_risk_count: int = Field(default=0)
    high_risk_count: int = Field(default=0)

    # Approval
    requires_approval: bool = Field(default=False)

    model_config = {"frozen": True}

    @property
    def total_patches(self) -> int:
        """Total number of patches."""
        return len(self.patches)

    @property
    def has_conflicts(self) -> bool:
        """Check if there are unresolved conflicts."""
        return len(self.conflicts) > 0

    def patches_for_row(self, row_no: int) -> list[Patch]:
        """Get all patches for a specific row."""
        return [p for p in self.patches if p.row_no == row_no]


# =============================================================================
# Write Result Models
# =============================================================================


class WriteResult(BaseModel, frozen=True):
    """Result of a write operation."""

    success: bool = Field(description="Whether write succeeded")
    output_path: str = Field(description="Path to written file")
    backup_path: str | None = Field(default=None, description="Path to backup file")

    old_checksum: str = Field(description="Checksum before changes")
    new_checksum: str = Field(description="Checksum after changes")

    mode: WriteMode = Field(description="Write mode used")
    fallback_used: bool = Field(
        default=False, description="True if preserve fell back to canonical"
    )

    patches_applied: int = Field(default=0)
    duration_ms: int = Field(default=0)

    error: str | None = Field(default=None, description="Error message if failed")

    model_config = {"frozen": True}


class RollbackResult(BaseModel, frozen=True):
    """Result of a rollback operation."""

    success: bool = Field(description="Whether rollback succeeded")
    file_path: str = Field(description="Path to restored file")
    backup_path: str = Field(description="Path to backup used")

    old_checksum: str = Field(description="Checksum before rollback")
    restored_checksum: str = Field(description="Checksum after rollback")
    expected_checksum: str = Field(description="Expected checksum from audit")

    checksums_match: bool = Field(description="Whether restored checksum matches expected")

    error: str | None = Field(default=None)

    model_config = {"frozen": True}


# =============================================================================
# Audit Models
# =============================================================================


class AuditPatchEntry(BaseModel, frozen=True):
    """Patch info stored in audit log."""

    row_no: int
    field: str
    operation: str
    old_value: str
    new_value: str
    rule_id: str
    rule_version: str
    risk: str

    model_config = {"frozen": True}


class AuditEntry(BaseModel, frozen=True):
    """Complete audit log entry for a fix operation."""

    run_id: str = Field(description="Unique run identifier")
    timestamp: datetime = Field(default_factory=_utc_now)

    # File info
    file_path: str
    file_checksum_before: str
    file_checksum_after: str

    # Backup info
    backup_path: str | None = None

    # Versions
    engine_version: str
    profile_id: str
    profile_version: str

    # Patches applied
    patches: list[AuditPatchEntry] = Field(default_factory=list)

    # Conflicts
    conflicts_detected: int = Field(default=0)
    conflicts_resolved: int = Field(default=0)

    # Write mode
    write_mode: str

    # Duration
    duration_ms: int = Field(default=0)

    # Rollback info
    rolled_back: bool = Field(default=False)
    rollback_timestamp: datetime | None = Field(default=None)

    model_config = {"frozen": True}


# =============================================================================
# Operation Context
# =============================================================================


class OperationContext(BaseModel):
    """Context for applying operations."""

    field_name: str
    max_length: int | None = None
    allowed_pattern: str | None = None
    charset_pattern: str | None = None

    model_config = {"frozen": False}
