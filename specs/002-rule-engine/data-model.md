# Data Model: Rule Engine

**Feature**: 002-rule-engine
**Date**: 2025-12-24

## Entity Overview

```
┌─────────────────┐     ┌─────────────────┐
│  RuleRegistry   │────▶│  Rule           │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │                       │ produces
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  Profile        │     │  Finding        │
└─────────────────┘     └─────────────────┘
         │
         │ configures
         ▼
┌─────────────────┐
│ExecutionPipeline│
└─────────────────┘
```

## Core Entities

### Stage

```python
from enum import Enum

class Stage(Enum):
    """Execution stages in order."""
    PARSE = "parse"
    HEADER = "header"
    SCHEMA = "schema"
    ROW_SEMANTIC = "row_semantic"
    CROSS_ROW = "cross_row"
    POLICY = "policy"
```

### Severity

```python
from enum import Enum

class Severity(Enum):
    """Finding severity levels."""
    FATAL = "fatal"    # Cannot continue
    ERROR = "error"    # Likely import failure
    WARN = "warn"      # Risky
    INFO = "info"      # Informational
    HINT = "hint"      # Best practice
```

### Constraint

```python
from pydantic import BaseModel
from typing import Any

class Constraint(BaseModel, frozen=True):
    """Rule constraint definition."""
    type: str  # "regex", "max_length", "enum", etc.
    params: dict[str, Any] = {}

    # Specific constraint types
    pattern: str | None = None  # For regex
    value: int | None = None  # For max_length, min_length
    values: list[str] | None = None  # For enum
```

### FixStrategy

```python
from pydantic import BaseModel
from typing import Any

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class FixStrategy(BaseModel, frozen=True):
    """How to fix a rule violation."""
    type: str  # "sanitize", "truncate", "upper", etc.
    steps: list[dict[str, Any]] = []
    risk: RiskLevel = RiskLevel.MEDIUM
    requires_approval: bool = False
```

### Rule

```python
from pydantic import BaseModel
from typing import Optional

class Rule(BaseModel, frozen=True):
    """
    Rule definition (from YAML or Python).

    CRITICAL: version is required for audit trail.
    """
    id: str  # "DVL-FIELD-011"
    version: str  # "1.0.0"
    title: str
    stage: Stage
    severity: Severity
    applies_to: str  # "row", "header", "file"

    # Selector
    selector: dict[str, str] = {}  # {"field": "belegfeld1"}

    # Constraint
    constraint: Constraint

    # Messages
    message: dict[str, str]  # {"de": "...", "en": "..."}
    docs_url: Optional[str] = None

    # Fix
    fix: Optional[FixStrategy] = None

    def check(self, value: str, context: dict) -> bool:
        """Check if value violates this rule."""
        ...
```

### Finding

```python
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime

class Location(BaseModel, frozen=True):
    """Where a finding occurred."""
    file: Optional[str] = None
    row_no: Optional[int] = None
    column: Optional[int] = None
    field: Optional[str] = None

class FixCandidate(BaseModel, frozen=True):
    """Proposed fix for a finding."""
    operation: str
    new_value: str
    risk: RiskLevel
    requires_approval: bool

class Finding(BaseModel, frozen=True):
    """
    Result of rule validation.

    CRITICAL: rule_version and engine_version required for audit.
    """
    code: str  # "DVL-FIELD-011"
    rule_version: str  # "1.0.0"
    engine_version: str  # From package

    severity: Severity
    title: str
    message: str

    location: Location
    context: dict[str, Any] = {}

    fix_candidates: list[FixCandidate] = []
    related: list[Location] = []  # For cross-row findings

    docs_url: Optional[str] = None
```

### Profile

```python
from pydantic import BaseModel
from typing import Optional, Any

class ProfileOverrides(BaseModel, frozen=True):
    """Overrides for rules in this profile."""
    severity: dict[str, str] = {}  # {"DVL-FIELD-011": "warning"}
    params: dict[str, dict[str, Any]] = {}  # {"DVL-PERIOD-001": {"max_days": 0}}

class Profile(BaseModel, frozen=True):
    """
    Rule profile configuration.

    Supports inheritance via 'base' field.
    """
    id: str  # "de.skr03.default"
    version: str  # "1.0.0"
    label: str  # "Deutschland SKR03 – Standard"
    base: Optional[str] = None  # Parent profile ID

    # Rule selection
    enable: list[str] = ["*"]  # Glob patterns
    disable: list[str] = []

    # Overrides
    overrides: ProfileOverrides = ProfileOverrides()
```

### RuleRegistry

```python
from pydantic import BaseModel

class RuleRegistry(BaseModel):
    """
    Central registry for all rules.

    Loads rules from:
    1. Built-in YAML files
    2. Python plugin entry points
    3. Custom rule directories
    """
    rules: dict[str, Rule] = {}
    profiles: dict[str, Profile] = {}

    def get_rule(self, rule_id: str) -> Rule | None:
        return self.rules.get(rule_id)

    def get_profile(self, profile_id: str) -> Profile | None:
        return self.profiles.get(profile_id)

    def get_rules_for_profile(self, profile: Profile) -> list[Rule]:
        """Get rules enabled by profile, with overrides applied."""
        ...

    def load_builtin(self):
        """Load built-in rules from package."""
        ...

    def load_plugins(self):
        """Load rules from entry points."""
        ...
```

### ExecutionPipeline

```python
from pydantic import BaseModel
from typing import Iterator

class PipelineResult(BaseModel):
    """Result of pipeline execution."""
    findings: list[Finding]
    aborted_at_stage: Stage | None = None
    engine_version: str
    profile_version: str
    stats: dict[str, int]  # {"rows_checked": 1000, "rules_run": 30}

class ExecutionPipeline(BaseModel):
    """
    Orchestrates stage-based rule execution.

    CRITICAL: Aborts on FATAL in parse/header stages.
    """
    registry: RuleRegistry
    profile: Profile

    FATAL_STAGES = {Stage.PARSE, Stage.HEADER}

    def run(self, parse_result: "ParseResult") -> PipelineResult:
        """Run all stages, collecting findings."""
        findings = []

        for stage in Stage:
            stage_findings = self._run_stage(stage, parse_result)
            findings.extend(stage_findings)

            if stage in self.FATAL_STAGES:
                if any(f.severity == Severity.FATAL for f in stage_findings):
                    return PipelineResult(
                        findings=findings,
                        aborted_at_stage=stage,
                        ...
                    )

        return PipelineResult(findings=findings, ...)

    def _run_stage(self, stage: Stage, parse_result) -> list[Finding]:
        """Run all rules for a stage."""
        ...
```

## Validation Summary

```python
from pydantic import BaseModel

class ValidationSummary(BaseModel):
    """Summary of validation run."""
    file: str
    encoding: str
    row_count: int

    # Versions
    engine_version: str
    profile_id: str
    profile_version: str

    # Counts by severity
    fatal_count: int = 0
    error_count: int = 0
    warn_count: int = 0
    info_count: int = 0

    # Top issues
    top_codes: list[tuple[str, int]]  # [("DVL-FIELD-011", 50), ...]

    # Timing
    duration_ms: int
```
