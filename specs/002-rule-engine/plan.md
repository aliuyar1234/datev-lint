# Implementation Plan: Rule Engine

**Branch**: `002-rule-engine` | **Date**: 2025-12-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-rule-engine/spec.md`
**Depends on**: 001-parser-core

## Summary

Implementierung der Rule Engine für datev-lint. Die Engine validiert geparste DATEV-Dateien gegen definierte Regeln und erzeugt strukturierte Findings. Kernfunktionen:

1. **Stage-basierte Pipeline** (parse → header → schema → semantic → cross-row → policy)
2. **YAML DSL für 80% der Regeln** (einfache Feld-Validierungen)
3. **Python Plugin API für komplexe Regeln** (Cross-Row, Custom Logic)
4. **Profile-System mit Vererbung** (SKR03, SKR04, AT)
5. **30 Baseline-Regeln** für MVP
6. **Rule Versioning für Audit**

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `pydantic` - Rule/Finding Models
- `pyyaml` - YAML Rule Loading
- `fnmatch` - Rule Enable/Disable Patterns
- Parser Core (001-parser-core)

**Storage**: YAML files for rules/profiles
**Testing**: pytest with golden file fixtures
**Target Platform**: Windows, Linux, macOS (CLI)
**Project Type**: Single project (Library-first)
**Performance Goals**:
- 20k Zeilen/s Validate-Throughput (row-level)
- Cross-Row 1M Zeilen ≤ 30s
- Profile Loading ≤ 100ms

**Constraints**:
- All Findings must include rule_version
- FATAL in parse/header stages aborts pipeline
- Bloom Filter for duplicate detection

**Scale/Scope**: 30+ rules, 5+ profiles

## Constitution Check

| Principle | Requirement | Status |
|-----------|-------------|--------|
| **I. Library-First** | Engine in `datev_lint/core/rules/` | ✅ Planned |
| **II. Parser Robustness** | Uses Parser Core output | ✅ Dependency |
| **III. Type Safety** | Findings use typed models | ✅ Planned |
| **IV. Golden File Testing** | Rule tests with golden files | ✅ Planned |
| **V. Performance Gates** | 20k rows/s throughput | ✅ Benchmarks |
| **VI. Audit & Versioning** | rule_version in all Findings | ✅ Core Feature |
| **VII. Privacy** | No data transmission | ✅ N/A |

**Gate Status**: ✅ PASSED

## Project Structure

### Source Code

```text
datev_lint/
├── core/
│   ├── parser/              # From 001-parser-core
│   └── rules/
│       ├── __init__.py      # Public API: validate()
│       ├── models.py        # Rule, Finding, Profile models
│       ├── registry.py      # RuleRegistry - loads all rules
│       ├── pipeline.py      # ExecutionPipeline - stage orchestration
│       ├── loader.py        # YAML rule/profile loader
│       ├── constraints.py   # Constraint implementations (regex, max_length, etc.)
│       ├── base.py          # Base Rule class for Python plugins
│       └── builtin/
│           ├── __init__.py
│           ├── encoding.py  # DVL-ENC-* rules
│           ├── header.py    # DVL-HDR-* rules
│           ├── fields.py    # DVL-FIELD-* rules
│           ├── dates.py     # DVL-DATE-* rules
│           ├── rows.py      # DVL-ROW-* rules
│           └── cross.py     # DVL-CROSS-* rules

datev_lint/
└── rules/                   # YAML rule definitions
    ├── base.yaml            # Base ruleset
    └── profiles/
        ├── de.skr03.default.yaml
        ├── de.skr04.default.yaml
        └── de.datev700.bookingbatch.yaml

tests/
├── fixtures/
│   └── rules/
│       ├── valid_no_errors.csv
│       ├── missing_konto.csv
│       ├── invalid_belegfeld.csv
│       └── duplicate_belegfeld1.csv
├── unit/
│   ├── test_constraints.py
│   ├── test_loader.py
│   ├── test_pipeline.py
│   └── test_registry.py
├── integration/
│   └── test_validate_e2e.py
└── benchmark/
    └── test_rule_performance.py
```

## Complexity Tracking

> No Constitution violations - no complexity justification needed.
