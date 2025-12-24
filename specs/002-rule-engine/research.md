# Research: Rule Engine

**Feature**: 002-rule-engine
**Date**: 2025-12-24
**Status**: Complete

## Research Questions

### RQ-1: Rule Definition Format

**Decision**: YAML DSL + Python Plugin API

**Rationale**:
- 80% der Regeln sind einfache Feld-Checks → YAML reicht
- Komplexe Logik (Cross-Row, Custom) → Python nötig
- YAML ist lesbar und versionierbar

**YAML Rule Structure**:
```yaml
rules:
  - id: "DVL-FIELD-011"
    version: "1.0.0"
    title: "Belegfeld 1 enthält unzulässige Zeichen"
    stage: "schema"
    severity: "error"
    applies_to: "row"
    selector:
      field: "belegfeld1"
    constraint:
      type: "regex"
      pattern: '^[A-Z0-9_$&%*+\-/]{0,36}$'
    message:
      de: "Belegfeld 1 darf nur A-Z, 0-9 und _$&%*+-/ enthalten."
    fix:
      type: "sanitize"
      risk: "medium"
```

---

### RQ-2: Execution Pipeline Stages

**Decision**: 6 Stages mit Early Abort

| Stage | Purpose | Abort on FATAL? |
|-------|---------|-----------------|
| `parse` | Encoding, CSV | ✅ Yes |
| `header` | EXTF, Version | ✅ Yes |
| `schema` | Field types, required | ❌ No |
| `row_semantic` | Soll/Haben logic | ❌ No |
| `cross_row` | Duplicates, sums | ❌ No |
| `policy` | Custom/mandant rules | ❌ No |

**Implementation**:
```python
class ExecutionPipeline:
    STAGES = ["parse", "header", "schema", "row_semantic", "cross_row", "policy"]
    FATAL_STAGES = {"parse", "header"}

    def run(self, parse_result, profile):
        findings = []
        for stage in self.STAGES:
            stage_findings = self._run_stage(stage, parse_result, profile)
            findings.extend(stage_findings)

            if stage in self.FATAL_STAGES:
                if any(f.severity == Severity.FATAL for f in stage_findings):
                    break  # Early abort
        return findings
```

---

### RQ-3: Profile System Design

**Decision**: YAML Profiles mit Vererbung

**Features**:
- `base`: Profile von dem geerbt wird
- `enable`/`disable`: Glob patterns für Rules
- `overrides`: Severity/Parameter Overrides

**Profile Structure**:
```yaml
profile:
  id: "de.skr03.default"
  version: "1.0.0"
  label: "Deutschland SKR03 – Standard"
  base: "de.datev700.bookingbatch"

  overrides:
    severity:
      DVL-FIELD-011: "warning"  # Downgrade to warning
    params:
      DVL-PERIOD-001:
        max_future_days: 0

rules:
  enable:
    - "DVL-*"
  disable:
    - "DVL-AT-*"  # No Austrian rules
```

**Loading Order**:
1. Load base profile (recursive)
2. Merge enable/disable patterns
3. Apply overrides

---

### RQ-4: Cross-Row Performance

**Decision**: Bloom Filter + Streaming

**Problem**: Duplicate detection for 1M rows

**Solution**:
```python
from pybloom_live import BloomFilter

class DuplicateDetector:
    def __init__(self, expected_items=1_000_000, error_rate=0.001):
        self.bloom = BloomFilter(capacity=expected_items, error_rate=error_rate)
        self.seen = {}  # For confirmed duplicates

    def check(self, value, row_no):
        if value in self.bloom:
            # Possible duplicate, verify
            if value in self.seen:
                return Finding(related=[{"row_no": self.seen[value]}])
        self.bloom.add(value)
        self.seen[value] = row_no
        return None
```

**Performance**: O(1) check, ~10MB for 1M items

---

### RQ-5: Finding Model

**Decision**: Pydantic with Rule Version

```python
class Finding(BaseModel, frozen=True):
    code: str  # "DVL-FIELD-011"
    rule_version: str  # "1.0.0"
    engine_version: str  # From package version
    severity: Severity
    title: str
    message: str
    location: Location
    context: dict[str, Any]
    fix_candidates: list[FixCandidate]
    related: list[Location]  # For cross-row
```

---

### RQ-6: Constraint Types

**Decision**: Extensible Constraint System

| Type | Parameters | Example |
|------|------------|---------|
| `regex` | pattern | `^[A-Z0-9]+$` |
| `max_length` | value | 36 |
| `min_length` | value | 1 |
| `enum` | values | `["S", "H"]` |
| `required` | - | Field must exist |
| `digits_only` | - | Only 0-9 |
| `range` | min, max | For amounts |

**Implementation**:
```python
class ConstraintRegistry:
    _constraints = {}

    @classmethod
    def register(cls, name):
        def decorator(constraint_cls):
            cls._constraints[name] = constraint_cls
            return constraint_cls
        return decorator

@ConstraintRegistry.register("regex")
class RegexConstraint:
    def __init__(self, pattern: str):
        self.pattern = re.compile(pattern)

    def check(self, value: str) -> bool:
        return bool(self.pattern.match(value))
```

---

## Baseline Rules (30 MVP)

### Parse/Header (5)
- DVL-ENC-001: Encoding unknown
- DVL-CSV-001: Malformed CSV
- DVL-HDR-001: Missing EXTF
- DVL-HDR-002: Invalid version
- DVL-HDR-003: Wrong category

### Schema (10)
- DVL-FIELD-001: Required field missing
- DVL-FIELD-002: Konto length invalid
- DVL-FIELD-003: Betrag format invalid
- DVL-FIELD-004: SH-Kennz invalid
- DVL-FIELD-005: BU-Schlüssel format
- DVL-FIELD-006: Gegenkonto length
- DVL-FIELD-007: Buchungstext too long
- DVL-FIELD-008: Kostenstelle format
- DVL-FIELD-009: Kostenträger format
- DVL-FIELD-011: Belegfeld1 charset

### Date (5)
- DVL-DATE-001: Invalid TTMM
- DVL-DATE-AMBIG-001: Ambiguous year
- DVL-DATE-RANGE-001: Out of period
- DVL-DATE-NOCTX-001: No context
- DVL-HDR-PRD-001: Period mismatch

### Semantic (5)
- DVL-ROW-001: SH inconsistent
- DVL-ROW-002: Zero amount
- DVL-ROW-003: Self-booking (Konto=Gegenkonto)
- DVL-ROW-004: Negative amount
- DVL-ROW-005: Missing BU for USt

### Cross-Row (5)
- DVL-CROSS-001: Duplicate Belegfeld1
- DVL-CROSS-002: Row count > 99,999
- DVL-CROSS-003: Sum mismatch (optional)
- DVL-CROSS-004: Sequence gaps
- DVL-CROSS-005: Period consistency

---

## Dependencies

```toml
[project]
dependencies = [
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "pybloom-live>=4.0",  # Bloom filter for duplicates
]
```
