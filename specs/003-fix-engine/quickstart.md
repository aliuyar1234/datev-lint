# Quickstart: Fix Engine

**Feature**: 003-fix-engine
**Date**: 2025-12-24

## Basic Usage

### Dry-Run (Preview Fixes)

```python
from datev_lint.core.parser import parse_file
from datev_lint.core.rules import validate
from datev_lint.core.fix import plan_fixes, preview_diff

# Parse and validate
result = parse_file("EXTF_Buchungsstapel.csv")
findings = validate(result)

# Generate fix plan
plan = plan_fixes(findings)

# Preview changes
print(f"Patches to apply: {plan.total_patches}")
print(f"By risk: {plan.by_risk}")

# Show diff
diff = preview_diff(result, plan)
print(diff)
```

### Apply Fixes (Pro)

```python
from datev_lint.core.fix import apply_fixes, WriteMode

# Apply with preserve mode (minimal diffs)
write_result = apply_fixes(
    result,
    plan,
    write_mode=WriteMode.PRESERVE
)

print(f"Backup created: {write_result.backup_path}")
print(f"Checksum: {write_result.checksum_after}")
```

## Working with Patches

### Inspect Patch Plan

```python
plan = plan_fixes(findings)

for patch in plan.patches:
    print(f"Row {patch.row_no}, Field: {patch.field}")
    print(f"  {patch.old_value!r} -> {patch.new_value!r}")
    print(f"  Operation: {patch.operation}")
    print(f"  Risk: {patch.risk.value}")
    print(f"  Rule: {patch.rule_code}")
```

### Filter by Risk Level

```python
from datev_lint.core.fix import RiskLevel

# Only low-risk patches
low_risk = [p for p in plan.patches if p.risk == RiskLevel.LOW]

# Patches requiring approval
needs_approval = [p for p in plan.patches if p.requires_approval]
```

### Handle Conflicts

```python
if plan.conflicts:
    print(f"Found {len(plan.conflicts)} conflicts:")
    for conflict in plan.conflicts:
        print(f"  Row {conflict.row_no}, Field: {conflict.field}")
        print(f"  Winner: {conflict.winner.rule_code}")
        for p in conflict.patches:
            print(f"    - {p.rule_code}: {p.new_value}")
```

## Writer Modes

### Preserve Mode (Default)

```python
from datev_lint.core.fix import apply_fixes, WriteMode

# Minimal changes, preserves original formatting
result = apply_fixes(
    parse_result,
    plan,
    write_mode=WriteMode.PRESERVE
)
```

### Canonical Mode

```python
# Standardized output
result = apply_fixes(
    parse_result,
    plan,
    write_mode=WriteMode.CANONICAL
)

# Output will have:
# - Consistent quoting
# - CRLF line endings
# - Standard encoding
```

## Backup & Rollback

### Check Backup

```python
result = apply_fixes(parse_result, plan)

# Backup is automatically created
print(f"Backup at: {result.backup_path}")
print(f"Original checksum: {result.checksum_before}")
print(f"New checksum: {result.checksum_after}")
```

### Rollback Changes

```python
from datev_lint.core.fix import rollback

# Rollback using run_id from audit log
rollback_result = rollback(run_id="abc123")

if rollback_result.success:
    print("Rollback successful!")
    print(f"Restored: {rollback_result.restored_path}")
else:
    print(f"Rollback failed: {rollback_result.error}")
```

## Audit Log

### View Audit Entry

```python
from datev_lint.core.fix import get_audit_entry

entry = get_audit_entry("abc123")

print(f"Timestamp: {entry.timestamp}")
print(f"Engine Version: {entry.versions.engine}")
print(f"Profile: {entry.versions.profile}")
print(f"Patches Applied: {entry.patches_applied}")
print(f"File Checksum Before: {entry.file.checksum_before}")
print(f"File Checksum After: {entry.file.checksum_after}")
```

### List Recent Fixes

```python
from datev_lint.core.fix import list_audit_entries

entries = list_audit_entries(limit=10)

for entry in entries:
    print(f"{entry.run_id}: {entry.timestamp} - {entry.patches_applied} patches")
```

## Risk Management

### Accept Risk Level

```python
from datev_lint.core.fix import apply_fixes, RiskLevel

# Auto-apply low and medium risk
result = apply_fixes(
    parse_result,
    plan,
    accept_risk=RiskLevel.MEDIUM
)

# Remaining high-risk patches are skipped
```

### Interactive Approval

```python
from datev_lint.core.fix import apply_fixes_interactive

# Prompts for each patch requiring approval
result = apply_fixes_interactive(parse_result, plan)
```

## Re-Validation

### Verify Fixes

```python
from datev_lint.core.parser import parse_file
from datev_lint.core.rules import validate

# Re-parse fixed file
fixed_result = parse_file("EXTF_Buchungsstapel.csv")

# Re-validate
new_findings = validate(fixed_result)

# Check if issues were fixed
original_codes = {f.code for f in findings}
remaining_codes = {f.code for f in new_findings}
fixed_codes = original_codes - remaining_codes

print(f"Fixed: {len(fixed_codes)} issue types")
print(f"Remaining: {len(remaining_codes)} issue types")
```

## Error Handling

```python
from datev_lint.core.fix import (
    apply_fixes,
    FixError,
    WritePermissionError,
    BackupError
)

try:
    result = apply_fixes(parse_result, plan)
except WritePermissionError as e:
    print(f"Cannot write to file: {e}")
except BackupError as e:
    print(f"Backup failed: {e}")
except FixError as e:
    print(f"Fix failed: {e}")
```
