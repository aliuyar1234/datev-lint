# Implementation Plan: Fix Engine

**Branch**: `003-fix-engine` | **Date**: 2025-12-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-fix-engine/spec.md`
**Depends on**: 001-parser-core, 002-rule-engine

## Summary

Implementierung der Fix Engine für datev-lint. Die Engine generiert Patches aus Findings und wendet sie auf DATEV-Dateien an. Kernfunktionen:

1. **Patch-Plan Generation** aus Findings mit Fix-Candidates
2. **Dry-Run Mode** mit Diff-Preview (Free)
3. **Apply Mode** mit atomischem Write (Pro)
4. **Writer-Modi**: preserve (minimal diffs) und canonical (standardisiert)
5. **Backup & Rollback** Mechanismus
6. **Audit Log** mit Versionen und Checksums

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `pydantic` - Patch/AuditEntry Models
- `difflib` - Unified Diff Generation
- Parser Core + Rule Engine

**Storage**: Backup files (.bak.{timestamp}), Audit logs (JSON)
**Testing**: pytest with before/after file comparisons
**Target Platform**: Windows, Linux, macOS (CLI)
**Project Type**: Single project (Library-first)
**Performance Goals**:
- Dry-Run 50k Zeilen + 100 Fixes ≤ 2s
- Apply + Backup 50k Zeilen ≤ 5s
- Preserve Mode: ≤ 5% Diff-Zeilen

**Constraints**:
- Atomic writes (temp + rename)
- Backup before every apply
- Re-validation after apply

**Scale/Scope**: 10 patch operations, 2 writer modes

## Constitution Check

| Principle | Requirement | Status |
|-----------|-------------|--------|
| **I. Library-First** | Engine in `datev_lint/core/fix/` | ✅ Planned |
| **II. Parser Robustness** | Uses Parser for re-validation | ✅ Dependency |
| **III. Type Safety** | Patch models typed | ✅ Planned |
| **IV. Golden File Testing** | Before/after file tests | ✅ Planned |
| **V. Performance Gates** | Apply ≤ 5s for 50k rows | ✅ Benchmarks |
| **VI. Audit & Versioning** | Audit log with all versions | ✅ Core Feature |
| **VII. Privacy** | No data transmission | ✅ N/A |

**Gate Status**: ✅ PASSED

## Project Structure

### Source Code

```text
datev_lint/
├── core/
│   ├── parser/              # From 001-parser-core
│   ├── rules/               # From 002-rule-engine
│   └── fix/
│       ├── __init__.py      # Public API: fix_file(), rollback()
│       ├── models.py        # Patch, PatchPlan, AuditEntry models
│       ├── planner.py       # Generate PatchPlan from Findings
│       ├── operations.py    # Patch operation implementations
│       ├── conflicts.py     # Conflict detection
│       ├── writer.py        # File writer (preserve/canonical modes)
│       ├── backup.py        # Backup creation and restore
│       ├── audit.py         # Audit log management
│       └── risk.py          # Risk level definitions

audit/                       # Audit log storage
└── {run_id}.json

tests/
├── fixtures/
│   └── fix/
│       ├── before_belegfeld_fix.csv
│       ├── after_belegfeld_fix.csv
│       ├── before_decimal_fix.csv
│       └── after_decimal_fix.csv
├── unit/
│   ├── test_planner.py
│   ├── test_operations.py
│   ├── test_writer.py
│   └── test_conflicts.py
├── integration/
│   └── test_fix_e2e.py
└── benchmark/
    └── test_fix_performance.py
```

## Complexity Tracking

> No Constitution violations - no complexity justification needed.
