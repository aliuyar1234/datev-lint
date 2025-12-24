# Data Model: Fix Engine

**Feature**: 003-fix-engine
**Date**: 2025-12-24

## Entity Overview

```
┌─────────────────┐     ┌─────────────────┐
│  Finding        │────▶│  Patch          │
└─────────────────┘     └────────┬────────┘
                                 │
                                 │ planned into
                                 ▼
                        ┌─────────────────┐
                        │  PatchPlan      │
                        └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
           ┌──────────┐  ┌──────────┐  ┌──────────┐
           │ Writer   │  │ Backup   │  │ AuditLog │
           └──────────┘  └──────────┘  └──────────┘
```

## Core Entities

### RiskLevel

```python
from enum import Enum

class RiskLevel(Enum):
    """Risk level for patches."""
    LOW = "low"       # Formatting only
    MEDIUM = "medium" # Content change (truncate, sanitize)
    HIGH = "high"     # Semantic change (delete, ID change)
```

### PatchOperation

```python
from enum import Enum

class PatchOperation(Enum):
    """Available patch operations."""
    SET_FIELD = "set_field"
    NORMALIZE_DECIMAL = "normalize_decimal"
    TRUNCATE = "truncate"
    SANITIZE_CHARS = "sanitize_chars"
    UPPER = "upper"
    DELETE_ROW = "delete_row"
    SPLIT_FILE = "split_file"
```

### Patch

```python
from pydantic import BaseModel
from typing import Optional

class Patch(BaseModel, frozen=True):
    """
    Single change to apply to a file.

    Tracks old/new values for audit trail.
    """
    row_no: int
    field: str
    operation: PatchOperation
    old_value: str
    new_value: str
    risk: RiskLevel
    rule_code: str
    requires_approval: bool = False

    # For display
    description: Optional[str] = None
```

### Conflict

```python
from pydantic import BaseModel

class Conflict(BaseModel, frozen=True):
    """
    Conflict between multiple patches for same location.
    """
    row_no: int
    field: str
    patches: list[Patch]
    winner: Patch  # Which patch will be applied
    reason: str  # Why winner was chosen
```

### PatchPlan

```python
from pydantic import BaseModel
from typing import Optional

class PatchPlan(BaseModel, frozen=True):
    """
    Complete plan of patches to apply.

    Generated from Findings with fix_candidates.
    """
    patches: list[Patch]
    conflicts: list[Conflict]

    # Statistics
    total_patches: int
    by_risk: dict[str, int]  # {"low": 10, "medium": 5}
    by_operation: dict[str, int]
    requires_approval_count: int

    def get_patches_for_row(self, row_no: int) -> list[Patch]:
        """Get all patches for a specific row."""
        return [p for p in self.patches if p.row_no == row_no]
```

### WriteMode

```python
from enum import Enum

class WriteMode(Enum):
    """File write modes."""
    PRESERVE = "preserve"    # Minimal diffs, keep original style
    CANONICAL = "canonical"  # Standardized output
```

### WriteResult

```python
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

class WriteResult(BaseModel, frozen=True):
    """Result of file write operation."""
    success: bool
    output_path: Path
    backup_path: Optional[Path] = None
    checksum_before: str
    checksum_after: str
    bytes_written: int
    mode_used: WriteMode
    fallback_reason: Optional[str] = None  # If preserve fell back to canonical
```

### AuditEntry

```python
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
from typing import Optional

class FileInfo(BaseModel, frozen=True):
    """File information for audit."""
    path: Path
    checksum_before: str
    checksum_after: str
    backup_path: Optional[Path] = None

class VersionInfo(BaseModel, frozen=True):
    """Version information for audit."""
    engine: str
    ruleset: str
    profile: str
    plugins: dict[str, str] = {}

class AuditEntry(BaseModel, frozen=True):
    """
    Complete audit trail for a fix operation.

    CRITICAL: Must contain all information to reproduce/rollback.
    """
    run_id: str
    timestamp: datetime
    versions: VersionInfo
    file: FileInfo
    patches: list[Patch]

    # Summary
    patches_applied: int
    patches_skipped: int
    conflicts: int

    # License info
    license_tier: Optional[str] = None
```

### RollbackResult

```python
from pydantic import BaseModel
from pathlib import Path

class RollbackResult(BaseModel, frozen=True):
    """Result of rollback operation."""
    success: bool
    run_id: str
    restored_path: Path
    checksum_verified: bool
    error: Optional[str] = None
```

## Service Models

### PatchPlanner

```python
from pydantic import BaseModel

class PatchPlanner:
    """
    Generates PatchPlan from Findings.

    Handles:
    - Extracting fix_candidates from findings
    - Conflict detection
    - Risk assessment
    """

    def plan(self, findings: list["Finding"]) -> PatchPlan:
        """Generate patch plan from findings."""
        patches = []
        for finding in findings:
            for candidate in finding.fix_candidates:
                patch = Patch(
                    row_no=finding.location.row_no,
                    field=finding.location.field,
                    operation=candidate.operation,
                    old_value=finding.context.get("raw_value", ""),
                    new_value=candidate.new_value,
                    risk=candidate.risk,
                    rule_code=finding.code,
                    requires_approval=candidate.requires_approval
                )
                patches.append(patch)

        # Detect conflicts
        conflicts = self._detect_conflicts(patches)
        resolved = self._resolve_conflicts(patches, conflicts)

        return PatchPlan(patches=resolved, conflicts=conflicts, ...)
```

### Writer

```python
class Writer:
    """
    Writes patched file in preserve or canonical mode.
    """

    def write(
        self,
        parse_result: "ParseResult",
        patches: list[Patch],
        output_path: Path,
        mode: WriteMode
    ) -> WriteResult:
        """Write patched file."""
        if mode == WriteMode.PRESERVE:
            return self._write_preserve(parse_result, patches, output_path)
        else:
            return self._write_canonical(parse_result, patches, output_path)

    def _write_preserve(self, parse_result, patches, output_path):
        """Preserve original formatting where possible."""
        # Use raw_tokens from parse_result
        # Only regenerate modified fields
        ...

    def _write_canonical(self, parse_result, patches, output_path):
        """Standardized output format."""
        # Always quote fields
        # CRLF line endings
        # Consistent encoding
        ...
```

### BackupManager

```python
from pathlib import Path
import time

class BackupManager:
    """Manages file backups for rollback."""

    def create_backup(self, path: Path) -> Path:
        """Create timestamped backup."""
        timestamp = int(time.time())
        backup_path = path.with_suffix(f".bak.{timestamp}")
        shutil.copy2(path, backup_path)
        return backup_path

    def restore_backup(self, backup_path: Path, target_path: Path) -> bool:
        """Restore from backup."""
        shutil.copy2(backup_path, target_path)
        return True

    def verify_checksum(self, path: Path, expected: str) -> bool:
        """Verify file checksum."""
        actual = sha256_file(path)
        return actual == expected
```

### AuditLogger

```python
from pathlib import Path
import json

class AuditLogger:
    """Manages audit log entries."""

    def __init__(self, audit_dir: Path = Path("audit")):
        self.audit_dir = audit_dir
        self.audit_dir.mkdir(exist_ok=True)

    def log(self, entry: AuditEntry) -> Path:
        """Write audit entry to file."""
        path = self.audit_dir / f"{entry.run_id}.json"
        path.write_text(entry.model_dump_json(indent=2))
        return path

    def load(self, run_id: str) -> AuditEntry | None:
        """Load audit entry by run_id."""
        path = self.audit_dir / f"{run_id}.json"
        if not path.exists():
            return None
        return AuditEntry.model_validate_json(path.read_text())
```
