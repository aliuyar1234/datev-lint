# Implementation Plan: CLI & Output Adapters

**Branch**: `004-cli-outputs` | **Date**: 2025-12-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-cli-outputs/spec.md`
**Depends on**: 001-parser-core, 002-rule-engine, 003-fix-engine

## Summary

Implementierung des CLI-Interface und der Output-Adapter für datev-lint. Das CLI ist der Haupteinstiegspunkt für Nutzer. Kernfunktionen:

1. **validate Command** mit farbiger Terminal-Ausgabe
2. **fix Command** mit dry-run und apply
3. **Output-Formate**: Terminal (Rich), JSON, SARIF
4. **Profile Selection** via --profile
5. **Exporter Fingerprinting** für Auto-Profile
6. **Exit Codes** für CI/CD Integration

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `typer` - CLI Framework
- `rich` - Terminal Formatting
- `jinja2` - Report Templates (Pro)
- `weasyprint` - PDF Generation (Pro)
- Core Libraries (parser, rules, fix)

**Storage**: N/A (stdout/files)
**Testing**: pytest with CLI runner
**Target Platform**: Windows, Linux, macOS (CLI)
**Project Type**: Single project (CLI shell around core)
**Performance Goals**:
- Terminal output 1000 Findings ≤ 1s
- JSON output schema-valid
- SARIF 2.1.0 compliant

**Constraints**:
- Exit codes: 0=ok, 1=error, 2=fatal
- TTY detection for colors
- Streaming for large outputs

**Scale/Scope**: 8 commands, 5 output formats

## Constitution Check

| Principle | Requirement | Status |
|-----------|-------------|--------|
| **I. Library-First** | CLI is shell, logic in core | ✅ Planned |
| **II. Parser Robustness** | Uses Parser Core | ✅ Dependency |
| **III. Type Safety** | Typed CLI context | ✅ Planned |
| **IV. Golden File Testing** | Output snapshot tests | ✅ Planned |
| **V. Performance Gates** | 1000 findings ≤ 1s | ✅ Benchmarks |
| **VI. Audit & Versioning** | Version in --version | ✅ Planned |
| **VII. Privacy** | No data in CLI | ✅ N/A |

**Gate Status**: ✅ PASSED

## Project Structure

### Source Code

```text
datev_lint/
├── core/                    # From 001-003
├── cli/
│   ├── __init__.py
│   ├── main.py              # Typer app, entry point
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── validate.py      # validate command
│   │   ├── fix.py           # fix command
│   │   ├── report.py        # report command (Pro)
│   │   ├── profiles.py      # profiles list
│   │   ├── rules.py         # rules list
│   │   ├── explain.py       # explain <code>
│   │   ├── fingerprint.py   # fingerprint command
│   │   └── rollback.py      # rollback command (Pro)
│   ├── output/
│   │   ├── __init__.py
│   │   ├── base.py          # OutputAdapter interface
│   │   ├── terminal.py      # Rich terminal output
│   │   ├── json.py          # JSON output
│   │   ├── sarif.py         # SARIF 2.1.0 output
│   │   ├── junit.py         # JUnit XML (Pro)
│   │   └── pdf.py           # PDF/HTML reports (Pro)
│   ├── fingerprint/
│   │   ├── __init__.py
│   │   ├── detector.py      # Exporter detection
│   │   └── signals.py       # Detection signals
│   └── context.py           # CLI context (args, config, profile)

tests/
├── fixtures/
│   └── cli/
│       ├── expected_terminal.txt
│       ├── expected_json.json
│       └── expected_sarif.json
├── unit/
│   ├── test_terminal_output.py
│   ├── test_json_output.py
│   ├── test_sarif_output.py
│   └── test_fingerprint.py
├── integration/
│   └── test_cli_e2e.py
└── benchmark/
    └── test_cli_performance.py
```

## Complexity Tracking

> No Constitution violations - no complexity justification needed.
