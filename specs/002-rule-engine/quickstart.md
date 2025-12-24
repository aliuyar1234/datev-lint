# Quickstart: Rule Engine

**Feature**: 002-rule-engine
**Date**: 2025-12-24

## Basic Usage

### Validate a File

```python
from datev_lint.core.parser import parse_file
from datev_lint.core.rules import validate

# Parse first
result = parse_file("EXTF_Buchungsstapel.csv")

# Validate with default profile
findings = validate(result)

# Print findings
for f in findings:
    print(f"{f.severity.value}: {f.code} - {f.message}")
```

### Use a Specific Profile

```python
from datev_lint.core.rules import validate, get_profile

# Load SKR03 profile
profile = get_profile("de.skr03.default")

# Validate with profile
findings = validate(result, profile=profile)
```

### Check Findings by Severity

```python
from datev_lint.core.rules import validate, Severity

findings = validate(result)

# Filter by severity
errors = [f for f in findings if f.severity == Severity.ERROR]
warnings = [f for f in findings if f.severity == Severity.WARN]
fatal = [f for f in findings if f.severity == Severity.FATAL]

print(f"FATAL: {len(fatal)}, ERRORS: {len(errors)}, WARNINGS: {len(warnings)}")
```

## Working with Profiles

### List Available Profiles

```python
from datev_lint.core.rules import get_registry

registry = get_registry()

for profile_id, profile in registry.profiles.items():
    print(f"{profile_id}: {profile.label}")
```

### Create Custom Profile

```yaml
# my_company.yaml
profile:
  id: "my.company.default"
  version: "1.0.0"
  label: "My Company Standard"
  base: "de.skr03.default"

  overrides:
    severity:
      DVL-FIELD-011: "warning"  # Downgrade to warning

rules:
  enable:
    - "DVL-*"
  disable:
    - "DVL-CROSS-003"  # Disable sum check
```

```python
from datev_lint.core.rules import load_profile

profile = load_profile("path/to/my_company.yaml")
findings = validate(result, profile=profile)
```

## Working with Rules

### List Available Rules

```python
from datev_lint.core.rules import get_registry

registry = get_registry()

for rule_id, rule in registry.rules.items():
    print(f"{rule_id} ({rule.stage.value}): {rule.title}")
```

### Get Rule Details

```python
from datev_lint.core.rules import get_rule

rule = get_rule("DVL-FIELD-011")
if rule:
    print(f"ID: {rule.id}")
    print(f"Version: {rule.version}")
    print(f"Stage: {rule.stage.value}")
    print(f"Severity: {rule.severity.value}")
    print(f"Message: {rule.message['de']}")
```

## Custom Python Rules

### Create a Custom Rule

```python
from datev_lint.core.rules import Rule, Finding, Severity, Stage

class MyCustomRule(Rule):
    id = "MY-CUSTOM-001"
    version = "1.0.0"
    stage = Stage.ROW_SEMANTIC
    severity = Severity.WARN
    title = "Custom validation rule"

    def run(self, ctx, row):
        # Access row data
        konto = row.fields_raw.get("konto")

        # Your validation logic
        if konto and konto.startswith("9"):
            yield Finding(
                code=self.id,
                rule_version=self.version,
                severity=self.severity,
                title=self.title,
                message="Konten mit 9xxx sind nicht erlaubt",
                location={"row_no": row.row_no, "field": "konto"},
                context={"raw_value": konto}
            )
```

### Register Custom Rule

```python
from datev_lint.core.rules import get_registry

registry = get_registry()
registry.register_rule(MyCustomRule())
```

## Cross-Row Validation

### Detect Duplicates

```python
from datev_lint.core.rules import validate

findings = validate(result)

# Cross-row findings have 'related' locations
for f in findings:
    if f.related:
        print(f"Duplicate at row {f.location.row_no}")
        print(f"First occurrence: row {f.related[0]['row_no']}")
```

## Performance Considerations

### Validate Large Files

```python
from datev_lint.core.parser import parse_file
from datev_lint.core.rules import validate

# Streaming parsing + validation
result = parse_file("large_file_1m_rows.csv")
findings = validate(result)  # Streaming, memory efficient

# Get summary without materializing all findings
from datev_lint.core.rules import get_summary

summary = get_summary(findings)
print(f"Total findings: {summary.total}")
print(f"Errors: {summary.error_count}")
```

## Finding Details

### Access Finding Information

```python
finding = findings[0]

# Basic info
print(f"Code: {finding.code}")
print(f"Rule Version: {finding.rule_version}")
print(f"Engine Version: {finding.engine_version}")
print(f"Severity: {finding.severity.value}")
print(f"Title: {finding.title}")
print(f"Message: {finding.message}")

# Location
print(f"Row: {finding.location.row_no}")
print(f"Field: {finding.location.field}")

# Context
print(f"Raw Value: {finding.context.get('raw_value')}")
print(f"Expected: {finding.context.get('expected')}")

# Fix candidates
for fix in finding.fix_candidates:
    print(f"Fix: {fix.operation} -> {fix.new_value} (risk: {fix.risk})")
```
