"""
Rule and Profile loader.

Loads rules from YAML files and Python plugins.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from .models import (
    Constraint,
    FixStep,
    FixStrategy,
    Profile,
    ProfileOverrides,
    RiskLevel,
    Rule,
    Severity,
    Stage,
)

if TYPE_CHECKING:
    from pathlib import Path


def load_rules_from_yaml(path: Path) -> list[Rule]:
    """
    Load rules from a YAML file.

    YAML format:
    ```yaml
    rules:
      DVL-FIELD-001:
        version: "1.0.0"
        title: "Required field missing"
        stage: schema
        severity: error
        applies_to: row
        selector:
          field: konto
        constraint:
          type: required
        message:
          de: "Pflichtfeld fehlt"
          en: "Required field missing"
    ```
    """
    if not path.exists():
        return []

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    rules_data = data.get("rules", {})
    rules: list[Rule] = []

    for rule_id, rule_data in rules_data.items():
        try:
            rule = _parse_rule(rule_id, rule_data)
            rules.append(rule)
        except Exception as e:
            # Log error but continue loading other rules
            print(f"Warning: Failed to load rule {rule_id}: {e}")

    return rules


def _parse_rule(rule_id: str, data: dict[str, Any]) -> Rule:
    """Parse a single rule from YAML data."""
    # Parse stage
    stage_str = data.get("stage", "row_semantic")
    stage = Stage(stage_str) if isinstance(stage_str, str) else Stage.ROW_SEMANTIC

    # Parse severity
    severity_str = data.get("severity", "error")
    severity = Severity(severity_str) if isinstance(severity_str, str) else Severity.ERROR

    # Parse constraint
    constraint_data = data.get("constraint", {})
    constraint = Constraint(
        type=constraint_data.get("type", "regex"),
        pattern=constraint_data.get("pattern"),
        value=constraint_data.get("value"),
        values=constraint_data.get("values"),
        field=constraint_data.get("field"),
        params=constraint_data.get("params", {}),
    )

    # Parse fix strategy if present
    fix = None
    if "fix" in data:
        fix_data = data["fix"]
        steps = []
        for step_data in fix_data.get("steps", []):
            steps.append(
                FixStep(
                    operation=step_data.get("operation", ""),
                    params=step_data.get("params", {}),
                )
            )
        fix = FixStrategy(
            type=fix_data.get("type", ""),
            steps=steps,
            risk=RiskLevel(fix_data.get("risk", "medium")),
            requires_approval=fix_data.get("requires_approval", False),
        )

    return Rule(
        id=rule_id,
        version=data.get("version", "1.0.0"),
        title=data.get("title", rule_id),
        stage=stage,
        severity=severity,
        applies_to=data.get("applies_to", "row"),
        selector=data.get("selector", {}),
        constraint=constraint,
        message=data.get("message", {}),
        docs_url=data.get("docs_url"),
        fix=fix,
        tags=data.get("tags", []),
        deprecated=data.get("deprecated", False),
    )


def load_profile_from_yaml(path: Path) -> Profile | None:
    """
    Load a profile from a YAML file.

    YAML format:
    ```yaml
    id: de.skr03.default
    version: "1.0.0"
    label: "Deutschland SKR03 – Standard"
    base: de.datev700.bookingbatch

    enable:
      - "*"

    disable:
      - "DVL-HINT-*"

    overrides:
      severity:
        DVL-FIELD-011: warn
      params:
        DVL-PERIOD-001:
          max_days: 0
    ```
    """
    if not path.exists():
        return None

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not data.get("id"):
        return None

    # Parse overrides
    overrides_data = data.get("overrides", {})
    overrides = ProfileOverrides(
        severity=overrides_data.get("severity", {}),
        params=overrides_data.get("params", {}),
        disabled=overrides_data.get("disabled", []),
    )

    return Profile(
        id=data["id"],
        version=data.get("version", "1.0.0"),
        label=data.get("label", data["id"]),
        base=data.get("base"),
        enable=data.get("enable", ["*"]),
        disable=data.get("disable", []),
        overrides=overrides,
    )


def load_profiles_from_directory(directory: Path) -> list[Profile]:
    """Load all profiles from a directory."""
    profiles: list[Profile] = []

    if not directory.exists():
        return profiles

    for yaml_file in directory.glob("*.yaml"):
        profile = load_profile_from_yaml(yaml_file)
        if profile:
            profiles.append(profile)

    for yml_file in directory.glob("*.yml"):
        profile = load_profile_from_yaml(yml_file)
        if profile:
            profiles.append(profile)

    return profiles


def load_rules_from_directory(directory: Path) -> list[Rule]:
    """Load all rules from YAML files in a directory."""
    all_rules: list[Rule] = []

    if not directory.exists():
        return all_rules

    for yaml_file in directory.glob("*.yaml"):
        rules = load_rules_from_yaml(yaml_file)
        all_rules.extend(rules)

    for yml_file in directory.glob("*.yml"):
        rules = load_rules_from_yaml(yml_file)
        all_rules.extend(rules)

    return all_rules
