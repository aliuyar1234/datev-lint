<!--
SYNC IMPACT REPORT
==================
Version change: (new) → 1.0.0
Modified principles: N/A (initial creation)
Added sections:
  - 7 Core Principles (Library-First, Parser Robustness, Type Safety,
    Golden File Testing, Performance Gates, Audit & Versioning, Privacy by Design)
  - DATEV-Specific Constraints
  - Development Workflow & Quality Gates
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ (compatible, Constitution Check section exists)
  - .specify/templates/spec-template.md ✅ (compatible, requirements align)
  - .specify/templates/tasks-template.md ✅ (compatible, test-first approach supported)
Follow-up TODOs: None
-->

# datev-lint Constitution

**Preflight validation for DATEV exports**

This constitution defines the non-negotiable principles governing the development of datev-lint. All code, design decisions, and architectural choices MUST comply with these principles.

## Core Principles

### I. Library-First Design

The core library (`datev_lint/core`) MUST be independently usable without CLI or SaaS dependencies.

- Every feature starts as a library component before being exposed via CLI
- Libraries MUST be self-contained and independently testable
- CLI and SaaS are "shells" around the same core - no business logic in shells
- OEM/Enterprise integrations consume the library directly, not CLI wrappers

**Rationale**: Enables OEM licensing, ERP integrations, and ensures clean separation of concerns.

### II. Parser Robustness

The parser is the critical path. It MUST handle real-world DATEV exports, not just spec-compliant files.

- **Streaming-capable**: Process files up to 1M rows without OOM
- **CSV edge cases**: Quoted fields, doubled quotes, embedded CR/LF in quotes
- **Encoding detection**: UTF-8 BOM, UTF-8, Windows-1252 (ANSI) with graceful fallback
- **Header semantics**: Line 1 = metadata header, Line 2 = column headers, Line 3+ = data
- **Roundtrip preservation**: `--fix` MUST produce minimal diffs (preserve mode default)

**Rationale**: Parser failures block everything. Real exports from sevDesk, Lexware, Sage vary from DATEV spec.

### III. Type Safety for Identifiers

Account numbers and IDs are **identifiers**, not numeric values. They MUST be stored as strings.

- `Konto`, `Gegenkonto`: String type, validated with `is_digits()` + length check
- `Beraternummer`, `Mandantennummer`: String type, never converted to int
- Leading zeros MUST be preserved: "0001234" stays "0001234"
- Numeric derived fields (e.g., for sorting) are optional and NEVER used for writeback

**Rationale**: `int("0001234")` loses leading zeros, causing DATEV import failures.

### IV. Golden File Testing

Golden files are the source of truth for parser and rule validation. Sample files are the critical path.

- **Minimum**: 10 real (redacted) files from 2+ exporters before MVP
- Golden fixtures for: valid files, encoding errors, broken quotes, edge cases
- Golden outputs: JSON findings snapshot, fixed file snapshot
- Parser changes require golden file regression tests
- TTMM date algorithm MUST have dedicated test cases for all confidence levels

**Rationale**: Building "against the spec" without real exports produces a tool that fails in production.

### V. Performance Gates

Performance is a feature. Regressions MUST fail the build.

| Metric | MVP Target | Gate |
|--------|------------|------|
| Validate 50k rows | ≤ 2s | CI fail if > 2.2s |
| Validate 1M rows | ≤ 60s | CI fail if > 66s |
| Memory peak 1M rows | ≤ 1.2 GB | CI fail if > 1.32 GB |
| Parse throughput | ≥ 50k rows/s | CI fail if regression > 10% |

- Performance test fixtures: 10k, 50k, 100k, 1M rows
- Baseline hardware: 8 cores, 16 GB RAM, SSD

**Rationale**: Accounting files can be large. Slow validation blocks user workflows.

### VI. Audit & Versioning

Every validation run MUST be reproducible. All rules, profiles, and findings include version metadata.

- Rules have SemVer versions: `version: "1.0.0"`
- Profiles have SemVer versions
- Findings include `rule_version` and `engine_version`
- Audit logs capture: engine version, ruleset version, profile version, plugin versions
- Fix operations log: file checksum before/after, patch list, all versions

**Rationale**: Steuerberater and auditors need proof that validation was consistent across time.

### VII. Privacy by Design

No booking data leaves the user's machine without explicit consent. DACH privacy standards apply.

- Telemetry is **opt-in** at first run (prompt required)
- Environment variable `DATEV_LINT_TELEMETRY=0` disables all telemetry
- Collected (if opted in): file size bucket, profile ID, finding counts (aggregated), runtime, version
- **NEVER collected**: Buchungstexte, Kontonummern, Belegnummern, raw data, IP addresses
- Privacy documentation MUST exist at `/docs/telemetry.md`

**Rationale**: German/Austrian accounting data is highly sensitive. Trust is the product.

## DATEV-Specific Constraints

These constraints derive from DATEV format specifications and real-world compatibility requirements.

| Constraint | Specification | Enforcement |
|------------|---------------|-------------|
| Max batch size | 99,999 Buchungssätze | ERROR if exceeded, Pro fix: auto-split |
| Belegfeld 1 charset | `^[A-Z0-9_$&%*+\-/]{0,36}$` | ASCII-only, no Unicode \w |
| TTMM date format | Day+Month without year | Deterministic year derivation algorithm |
| Decimal separator | Comma (`,`) not dot | `1234,56` format |
| Field delimiter | Semicolon (`;`) | Not comma |
| Line ending | CR terminates records | LF allowed inside quoted fields |
| Encoding default | Windows-1252 (ANSI) | UTF-8 with BOM also accepted |

## Development Workflow & Quality Gates

### Test-First Discipline

- Golden file tests MUST exist before parser changes
- Rule tests MUST fail before implementation (red-green-refactor)
- Integration tests cover: validate → fix dry-run → fix apply → revalidate

### Code Review Gates

All PRs MUST verify:

1. Constitution compliance (this document)
2. No `int()` conversion of account numbers or IDs
3. Performance regression check passes
4. Golden file tests pass
5. Rule version incremented if rule logic changes

### Release Checklist

- [ ] All golden file tests pass
- [ ] Performance benchmarks within gates
- [ ] Changelog updated with version bump rationale
- [ ] Telemetry documentation current
- [ ] Haftungs-Disclaimer present in distribution

## Governance

This constitution supersedes all other development practices for datev-lint.

### Amendment Process

1. Propose amendment via PR to this file
2. Document rationale and impact assessment
3. Update dependent templates if principles change
4. Increment constitution version per SemVer:
   - MAJOR: Principle removal or redefinition
   - MINOR: New principle or material expansion
   - PATCH: Clarifications, wording fixes

### Compliance

- All code reviews MUST verify constitution compliance
- Complexity beyond these principles requires explicit justification in PR
- Violations block merge

### Reference Documents

- Product Specification: `/docs/datev-lint-spec-v2.1.md`
- Telemetry Policy: `/docs/telemetry.md` (TODO: create)
- Field Dictionary: Single source of truth for field definitions

**Version**: 1.0.0 | **Ratified**: 2025-12-24 | **Last Amended**: 2025-12-24
