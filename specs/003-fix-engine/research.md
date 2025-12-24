# Research: Fix Engine

**Feature**: 003-fix-engine
**Date**: 2025-12-24
**Status**: Complete

## Research Questions

### RQ-1: Patch Operation Design

**Decision**: Typed Patch Operations with Risk Levels

| Operation | Description | Risk | Auto-Apply? |
|-----------|-------------|------|-------------|
| `set_field` | Set field value | varies | No |
| `normalize_decimal` | Fix decimal format | low | Yes |
| `truncate` | Shorten field | medium | No |
| `sanitize_chars` | Replace invalid chars | medium | No |
| `upper` | Convert to uppercase | low | Yes |
| `delete_row` | Remove row | high | Never |
| `split_file` | Split >99,999 rows | medium | No |

**Patch Model**:
```python
class Patch(BaseModel, frozen=True):
    row_no: int
    field: str
    operation: str
    old_value: str
    new_value: str
    risk: RiskLevel
    rule_code: str
    requires_approval: bool
```

---

### RQ-2: Writer Modes

**Decision**: Two modes - preserve (default) and canonical

**Preserve Mode**:
- Keep original quoting style
- Keep original line endings where possible
- Only modify affected fields
- Best-effort minimal diff

**Canonical Mode**:
- Standardized quoting (always quote)
- CRLF line endings
- UTF-8 or Windows-1252 (configurable)
- Deterministic output

**Implementation**:
```python
class Writer:
    def write(self, rows, original_tokens, mode: WriteMode):
        if mode == WriteMode.PRESERVE:
            return self._write_preserve(rows, original_tokens)
        else:
            return self._write_canonical(rows)

    def _write_preserve(self, rows, original_tokens):
        # Use original_tokens for unchanged fields
        # Only regenerate modified fields
        pass

    def _write_canonical(self, rows):
        # Standardize everything
        pass
```

---

### RQ-3: Atomic Write Strategy

**Decision**: temp file + rename

**Flow**:
1. Create backup: `original.csv` → `original.csv.bak.{timestamp}`
2. Write to temp: `original.csv.tmp`
3. Atomic rename: `original.csv.tmp` → `original.csv`
4. On error: temp file is deleted, backup remains

```python
def atomic_write(path: Path, content: bytes):
    backup_path = path.with_suffix(f".bak.{int(time.time())}")
    temp_path = path.with_suffix(".tmp")

    # Backup original
    shutil.copy2(path, backup_path)

    try:
        # Write to temp
        temp_path.write_bytes(content)
        # Atomic rename
        temp_path.replace(path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return backup_path
```

---

### RQ-4: Conflict Detection

**Decision**: First-Write-Wins with Warning

**Scenario**: Two rules want to fix same field

**Resolution**:
1. Detect overlapping patches (same row + field)
2. Apply first patch (by rule priority)
3. Emit warning for skipped patch
4. Show both options in dry-run

```python
class ConflictDetector:
    def detect(self, patches: list[Patch]) -> tuple[list[Patch], list[Conflict]]:
        by_location = defaultdict(list)
        for p in patches:
            by_location[(p.row_no, p.field)].append(p)

        conflicts = []
        resolved = []
        for loc, loc_patches in by_location.items():
            if len(loc_patches) > 1:
                conflicts.append(Conflict(
                    location=loc,
                    patches=loc_patches,
                    winner=loc_patches[0]
                ))
                resolved.append(loc_patches[0])
            else:
                resolved.append(loc_patches[0])

        return resolved, conflicts
```

---

### RQ-5: Audit Log Format

**Decision**: JSON with full traceability

```json
{
  "run_id": "abc123",
  "timestamp": "2025-01-15T10:30:00Z",
  "versions": {
    "engine": "1.2.3",
    "ruleset": "1.0.0",
    "profile": "de.skr03.default@1.0.0"
  },
  "file": {
    "path": "/path/to/file.csv",
    "checksum_before": "sha256:...",
    "checksum_after": "sha256:...",
    "backup_path": "/path/to/file.csv.bak.1234567890"
  },
  "patches": [
    {
      "row_no": 42,
      "field": "belegfeld1",
      "operation": "sanitize_chars",
      "old_value": "RE-2025.001",
      "new_value": "RE-2025001",
      "rule_code": "DVL-FIELD-011"
    }
  ],
  "summary": {
    "patches_applied": 5,
    "patches_skipped": 0,
    "conflicts": 0
  }
}
```

---

### RQ-6: Rollback Implementation

**Decision**: Checksum verification before restore

```python
def rollback(run_id: str):
    audit = load_audit(run_id)

    # Verify current file matches "after" state
    current_checksum = sha256_file(audit.file.path)
    if current_checksum != audit.file.checksum_after:
        raise RollbackError("File was modified since fix was applied")

    # Verify backup exists and matches
    if not audit.file.backup_path.exists():
        raise RollbackError("Backup file not found")

    backup_checksum = sha256_file(audit.file.backup_path)
    if backup_checksum != audit.file.checksum_before:
        raise RollbackError("Backup file corrupted")

    # Restore
    shutil.copy2(audit.file.backup_path, audit.file.path)

    # Log rollback
    log_rollback(run_id)
```

---

### RQ-7: Risk Level Policy

**Decision**: Configurable acceptance thresholds

| Flag | Effect |
|------|--------|
| `--accept-risk low` | Apply low-risk fixes automatically |
| `--accept-risk medium` | Apply low+medium risk |
| `--accept-risk high` | Apply all (with warning) |
| `--yes` | Skip interactive prompts |
| Default | Interactive prompt for medium+high |

```python
def should_apply(patch: Patch, accept_risk: RiskLevel, interactive: bool) -> bool:
    if patch.risk <= accept_risk:
        return True
    if patch.requires_approval:
        if interactive:
            return prompt_user(patch)
        else:
            return False
    return False
```

---

## Dependencies

```toml
[project]
dependencies = [
    "pydantic>=2.0",
]
```

No additional dependencies needed - uses standard library for file operations.
