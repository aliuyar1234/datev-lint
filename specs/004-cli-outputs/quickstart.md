# Quickstart: CLI & Output Adapters

**Feature**: 004-cli-outputs
**Date**: 2025-12-24

## Installation

```bash
pip install datev-lint
```

## Basic Commands

### Validate a File

```bash
# Basic validation with terminal output
datev-lint validate EXTF_Buchungsstapel.csv

# With specific profile
datev-lint validate EXTF_Buchungsstapel.csv --profile de.skr03.default

# Auto-detect exporter and use suggested profile
datev-lint validate EXTF_Buchungsstapel.csv --auto-profile
```

### Output Formats

```bash
# JSON output
datev-lint validate file.csv --format json

# JSON to file
datev-lint validate file.csv --format json --out findings.json

# SARIF for GitHub Code Scanning
datev-lint validate file.csv --format sarif --out results.sarif
```

### Exit Codes for CI

```bash
# Default: exit 1 on ERROR, exit 2 on FATAL
datev-lint validate file.csv

# Fail on warnings too
datev-lint validate file.csv --fail-on warn

# Check exit code
datev-lint validate file.csv && echo "OK" || echo "FAILED"
```

## Fix Command

```bash
# Preview fixes (dry-run)
datev-lint fix file.csv --dry-run

# Apply fixes (Pro)
datev-lint fix file.csv --apply

# Canonical output mode
datev-lint fix file.csv --apply --write-mode canonical

# Accept medium-risk fixes without prompt
datev-lint fix file.csv --apply --accept-risk medium

# Skip all prompts
datev-lint fix file.csv --apply --yes
```

## Reports (Pro)

```bash
# Generate PDF report
datev-lint report file.csv --format pdf --out report.pdf

# Generate HTML report
datev-lint report file.csv --format html --out report.html
```

## Utility Commands

### List Profiles

```bash
datev-lint profiles list

# Output:
# de.skr03.default     Deutschland SKR03 – Standard
# de.skr04.default     Deutschland SKR04 – Standard
# de.datev700.base     DATEV 700 Basis
```

### List Rules

```bash
# All rules
datev-lint rules list

# Rules for specific profile
datev-lint rules list --profile de.skr03.default

# Filter by stage
datev-lint rules list --stage schema
```

### Explain a Rule

```bash
datev-lint explain DVL-FIELD-011

# Output:
# DVL-FIELD-011: Belegfeld 1 enthält unzulässige Zeichen
#
# Stage: schema
# Severity: error
#
# Beschreibung:
#   Belegfeld 1 darf nur A-Z, 0-9 und _$&%*+-/ enthalten (max 36 Zeichen).
#
# Beispiel:
#   ❌ "RE-2025.001" (Punkt nicht erlaubt)
#   ✅ "RE-2025001"
#
# Fix:
#   Entferne ungültige Zeichen und konvertiere zu Großbuchstaben.
```

### Fingerprint Exporter

```bash
datev-lint fingerprint file.csv

# Output:
# Exporter erkannt: sevDesk (87%)
#
# Erkannte Signale:
#   ✓ Header Feld 17 = "0"
#   ✓ Standard Spaltenreihenfolge
#
# Empfohlenes Profil: de.skr03.sevdesk.v2
```

### Rollback (Pro)

```bash
datev-lint rollback --run-id abc123
```

## Help

```bash
# General help
datev-lint --help

# Command-specific help
datev-lint validate --help
datev-lint fix --help
```

## CI/CD Integration

### GitHub Actions

```yaml
name: DATEV Lint
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install datev-lint
        run: pip install datev-lint

      - name: Validate DATEV exports
        run: datev-lint validate exports/*.csv --format sarif --out results.sarif

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: results.sarif
```

### GitLab CI

```yaml
datev-lint:
  image: python:3.11
  script:
    - pip install datev-lint
    - datev-lint validate exports/*.csv --format json --out findings.json
  artifacts:
    reports:
      codequality: findings.json
```

## Programmatic CLI Usage

```python
from typer.testing import CliRunner
from datev_lint.cli.main import app

runner = CliRunner()

# Run validate command
result = runner.invoke(app, ["validate", "file.csv", "--format", "json"])
print(result.output)
print(f"Exit code: {result.exit_code}")
```

## Output Examples

### Terminal Output

```
EXTF_Buchungsstapel.csv

  ERROR  DVL-FIELD-011  Line 42: Belegfeld 1 enthält unzulässige Zeichen
         Raw: "RE-2025.001"
         Fix: "RE-2025001" (risk: medium)

  ERROR  DVL-FIELD-002  Line 105: Konto zu lang
         Raw: "1234567890"
         Expected: max 9 digits

  WARN   DVL-DATE-AMBIG-001  Line 200: Datum mehrdeutig
         TTMM "0101" könnte 01.01.2024 oder 01.01.2025 sein

Summary: 2 errors, 1 warning, 0 info
```

### JSON Output

```json
[
  {
    "code": "DVL-FIELD-011",
    "rule_version": "1.0.0",
    "severity": "error",
    "title": "Belegfeld 1 enthält unzulässige Zeichen",
    "message": "Belegfeld 1 darf nur A-Z, 0-9 und _$&%*+-/ enthalten.",
    "location": {
      "file": "EXTF_Buchungsstapel.csv",
      "row_no": 42,
      "field": "belegfeld1"
    },
    "context": {
      "raw_value": "RE-2025.001"
    },
    "fix_candidates": [
      {
        "operation": "sanitize_chars",
        "new_value": "RE-2025001",
        "risk": "medium"
      }
    ]
  }
]
```
