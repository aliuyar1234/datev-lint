# Research: CLI & Output Adapters

**Feature**: 004-cli-outputs
**Date**: 2025-12-24
**Status**: Complete

## Research Questions

### RQ-1: CLI Framework

**Decision**: Typer + Rich

**Rationale**:
- Typer: Modern, type-hint based CLI
- Rich: Beautiful terminal output
- Both maintained, widely used

**Alternatives Considered**:
| Library | Pro | Contra |
|---------|-----|--------|
| `click` | Mature, flexible | More verbose |
| `argparse` | Standard library | No colors, verbose |
| `fire` | Auto-generation | Less control |

**Entry Point**:
```python
# pyproject.toml
[project.scripts]
datev-lint = "datev_lint.cli.main:app"
```

---

### RQ-2: Output Adapter Pattern

**Decision**: Strategy Pattern with Protocol

```python
from typing import Protocol

class OutputAdapter(Protocol):
    def format_findings(self, findings: list[Finding]) -> str: ...
    def format_summary(self, summary: ValidationSummary) -> str: ...
    def write(self, content: str, destination: Path | None) -> None: ...

class TerminalAdapter:
    def __init__(self, console: Console):
        self.console = console

    def format_findings(self, findings):
        # Rich formatting with colors
        pass

class JsonAdapter:
    def format_findings(self, findings):
        return json.dumps([f.model_dump() for f in findings], indent=2)

class SarifAdapter:
    def format_findings(self, findings):
        # SARIF 2.1.0 format
        pass
```

---

### RQ-3: SARIF 2.1.0 Structure

**Decision**: Full SARIF compliance for GitHub integration

```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "datev-lint",
          "version": "1.0.0",
          "informationUri": "https://datev-lint.dev",
          "rules": [
            {
              "id": "DVL-FIELD-011",
              "name": "InvalidBelegfeld1Charset",
              "shortDescription": {
                "text": "Belegfeld 1 contains invalid characters"
              },
              "defaultConfiguration": {
                "level": "error"
              }
            }
          ]
        }
      },
      "results": [
        {
          "ruleId": "DVL-FIELD-011",
          "level": "error",
          "message": {
            "text": "Belegfeld 1 darf nur A-Z, 0-9 und _$&%*+-/ enthalten."
          },
          "locations": [
            {
              "physicalLocation": {
                "artifactLocation": {
                  "uri": "EXTF_Buchungsstapel.csv"
                },
                "region": {
                  "startLine": 42
                }
              }
            }
          ]
        }
      ]
    }
  ]
}
```

---

### RQ-4: Exporter Fingerprinting

**Decision**: Signal-based detection with confidence scoring

**Signals**:
| Signal | Weight | Example |
|--------|--------|---------|
| Header field patterns | 0.4 | sevDesk: field 17 = "0" |
| Column order | 0.3 | Lexware: different order |
| Default values | 0.2 | Sage: 4-digit BU |
| Filename pattern | 0.1 | `EXTF_sevDesk_*.csv` |

**Implementation**:
```python
class ExporterDetector:
    def detect(self, parse_result: ParseResult) -> ExporterFingerprint:
        scores = defaultdict(float)
        signals = []

        for detector in self.detectors:
            result = detector.check(parse_result)
            if result:
                scores[result.exporter_id] += result.weight
                signals.append(result.signal_name)

        if not scores:
            return ExporterFingerprint(exporter_id="unknown", confidence=0)

        best = max(scores.items(), key=lambda x: x[1])
        return ExporterFingerprint(
            exporter_id=best[0],
            confidence=min(best[1], 1.0),
            detected_by=signals,
            suggested_profile=self.get_profile(best[0])
        )
```

---

### RQ-5: Exit Code Strategy

**Decision**: Severity-based exit codes

| Exit Code | Meaning | When |
|-----------|---------|------|
| 0 | Success | No ERROR/FATAL findings |
| 1 | Error | At least one ERROR (or WARN with --fail-on warn) |
| 2 | Fatal | Parsing/format error |

```python
def get_exit_code(findings: list[Finding], fail_on: Severity) -> int:
    max_severity = max((f.severity for f in findings), default=Severity.INFO)

    if max_severity == Severity.FATAL:
        return 2
    if max_severity >= fail_on:
        return 1
    return 0
```

---

### RQ-6: TTY Detection

**Decision**: Automatic color disable for pipes

```python
from rich.console import Console

def create_console(force_terminal: bool | None = None) -> Console:
    if force_terminal is not None:
        return Console(force_terminal=force_terminal)

    # Auto-detect: colors if TTY, plain if pipe
    return Console()

# Usage
console = create_console()
if not console.is_terminal:
    # Simplified output for pipes
    pass
```

---

### RQ-7: PDF Report Generation (Pro)

**Decision**: Jinja2 + WeasyPrint

**Flow**:
1. Jinja2 template renders HTML
2. WeasyPrint converts to PDF
3. CSS for styling

```python
from jinja2 import Environment, PackageLoader
from weasyprint import HTML

def generate_pdf(findings: list[Finding], output: Path):
    env = Environment(loader=PackageLoader("datev_lint", "templates"))
    template = env.get_template("report.html.j2")

    html_content = template.render(
        findings=findings,
        summary=compute_summary(findings),
        generated_at=datetime.now()
    )

    HTML(string=html_content).write_pdf(output)
```

---

## CLI Commands Summary

```bash
# Validate
datev-lint validate file.csv
datev-lint validate file.csv --profile de.skr03.default
datev-lint validate file.csv --format json --out findings.json
datev-lint validate file.csv --format sarif
datev-lint validate file.csv --fail-on warn

# Fix
datev-lint fix file.csv --dry-run
datev-lint fix file.csv --apply  # Pro
datev-lint fix file.csv --write-mode canonical

# Report
datev-lint report file.csv --format pdf --out report.pdf  # Pro

# Utilities
datev-lint profiles list
datev-lint rules list --profile de.skr03.default
datev-lint explain DVL-FIELD-011
datev-lint fingerprint file.csv

# Rollback
datev-lint rollback --run-id abc123  # Pro
```

---

## Dependencies

```toml
[project]
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0",
]

[project.optional-dependencies]
pro = [
    "jinja2>=3.0",
    "weasyprint>=60.0",
]
```
