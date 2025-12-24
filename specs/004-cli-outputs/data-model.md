# Data Model: CLI & Output Adapters

**Feature**: 004-cli-outputs
**Date**: 2025-12-24

## Entity Overview

```
┌─────────────────┐
│  CLI App        │
└────────┬────────┘
         │
         │ uses
         ▼
┌─────────────────┐     ┌─────────────────┐
│  CliContext     │────▶│  OutputAdapter  │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
           ┌──────────┐  ┌──────────┐  ┌──────────┐
           │ Terminal │  │   JSON   │  │  SARIF   │
           └──────────┘  └──────────┘  └──────────┘
```

## Core Entities

### OutputFormat

```python
from enum import Enum

class OutputFormat(Enum):
    """Available output formats."""
    TERMINAL = "terminal"
    JSON = "json"
    SARIF = "sarif"
    JUNIT = "junit"  # Pro
    PDF = "pdf"      # Pro
    HTML = "html"    # Pro
```

### ExitCode

```python
from enum import Enum

class ExitCode(Enum):
    """CLI exit codes."""
    OK = 0       # No errors
    ERROR = 1    # At least one ERROR finding
    FATAL = 2    # Parsing/format failure
```

### CliContext

```python
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

class CliContext(BaseModel):
    """
    CLI execution context.

    Holds all parsed arguments and resolved configuration.
    """
    # Input
    input_file: Path
    profile_id: Optional[str] = None

    # Output
    output_format: OutputFormat = OutputFormat.TERMINAL
    output_file: Optional[Path] = None

    # Behavior
    fail_on: "Severity" = Severity.ERROR
    verbose: bool = False
    quiet: bool = False
    color: Optional[bool] = None  # None = auto-detect

    # Fix options
    dry_run: bool = True
    write_mode: "WriteMode" = WriteMode.PRESERVE
    accept_risk: "RiskLevel" = RiskLevel.LOW
    yes: bool = False  # Skip prompts

    # Resolved
    resolved_profile: Optional["Profile"] = None
    license: Optional["License"] = None
```

### OutputAdapter (Protocol)

```python
from typing import Protocol
from pathlib import Path

class OutputAdapter(Protocol):
    """Interface for output format implementations."""

    def format_findings(self, findings: list["Finding"]) -> str:
        """Format findings for output."""
        ...

    def format_summary(self, summary: "ValidationSummary") -> str:
        """Format validation summary."""
        ...

    def format_patch_plan(self, plan: "PatchPlan") -> str:
        """Format fix patch plan."""
        ...

    def write(self, content: str, destination: Path | None) -> None:
        """Write formatted content to destination."""
        ...
```

### TerminalOutput

```python
from rich.console import Console
from rich.table import Table

class TerminalOutput:
    """Rich terminal output adapter."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def format_findings(self, findings: list["Finding"]) -> None:
        """Print findings with colors."""
        for finding in findings:
            severity_style = {
                Severity.FATAL: "bold red",
                Severity.ERROR: "red",
                Severity.WARN: "yellow",
                Severity.INFO: "blue",
            }.get(finding.severity, "white")

            self.console.print(
                f"[{severity_style}]{finding.severity.value.upper()}[/] "
                f"[dim]{finding.code}[/] "
                f"Line {finding.location.row_no}: {finding.message}"
            )
```

### JsonOutput

```python
import json

class JsonOutput:
    """JSON output adapter."""

    def format_findings(self, findings: list["Finding"]) -> str:
        return json.dumps(
            [f.model_dump() for f in findings],
            indent=2,
            ensure_ascii=False
        )

    def format_summary(self, summary: "ValidationSummary") -> str:
        return summary.model_dump_json(indent=2)
```

### SarifOutput

```python
class SarifOutput:
    """SARIF 2.1.0 output adapter."""

    SARIF_VERSION = "2.1.0"
    SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"

    def format_findings(self, findings: list["Finding"]) -> str:
        sarif = {
            "$schema": self.SCHEMA,
            "version": self.SARIF_VERSION,
            "runs": [
                {
                    "tool": self._build_tool_info(findings),
                    "results": [self._build_result(f) for f in findings]
                }
            ]
        }
        return json.dumps(sarif, indent=2)

    def _build_tool_info(self, findings):
        rules = {}
        for f in findings:
            if f.code not in rules:
                rules[f.code] = {
                    "id": f.code,
                    "name": f.code.replace("-", ""),
                    "shortDescription": {"text": f.title}
                }
        return {
            "driver": {
                "name": "datev-lint",
                "version": get_version(),
                "rules": list(rules.values())
            }
        }

    def _build_result(self, finding: "Finding") -> dict:
        return {
            "ruleId": finding.code,
            "level": self._severity_to_level(finding.severity),
            "message": {"text": finding.message},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": finding.location.file},
                    "region": {"startLine": finding.location.row_no}
                }
            }]
        }
```

### ExporterFingerprint

```python
from pydantic import BaseModel

class ExporterFingerprint(BaseModel, frozen=True):
    """Result of exporter detection."""
    exporter_id: str  # "sevdesk", "lexware", "unknown"
    confidence: float  # 0.0 - 1.0
    detected_by: list[str]  # Signals that matched
    suggested_profile: str | None  # Profile to use
```

### DetectionSignal

```python
from pydantic import BaseModel

class DetectionSignal(BaseModel, frozen=True):
    """Signal used for exporter detection."""
    name: str
    exporter_id: str
    weight: float  # 0.0 - 1.0
    description: str

    def check(self, parse_result: "ParseResult") -> bool:
        """Check if signal matches."""
        ...
```

## Command Models

### ValidateOptions

```python
from pydantic import BaseModel

class ValidateOptions(BaseModel):
    """Options for validate command."""
    file: Path
    profile: str | None = None
    auto_profile: bool = False
    format: OutputFormat = OutputFormat.TERMINAL
    out: Path | None = None
    fail_on: Severity = Severity.ERROR
```

### FixOptions

```python
from pydantic import BaseModel

class FixOptions(BaseModel):
    """Options for fix command."""
    file: Path
    profile: str | None = None
    dry_run: bool = True
    write_mode: WriteMode = WriteMode.PRESERVE
    accept_risk: RiskLevel = RiskLevel.LOW
    yes: bool = False
```

### ReportOptions

```python
from pydantic import BaseModel

class ReportOptions(BaseModel):
    """Options for report command (Pro)."""
    file: Path
    profile: str | None = None
    format: str = "pdf"  # pdf or html
    out: Path
    template: str | None = None
```
