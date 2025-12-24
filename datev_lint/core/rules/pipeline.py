"""
Execution Pipeline.

Orchestrates stage-based rule execution.
"""

from __future__ import annotations

import time
from collections import Counter
from typing import TYPE_CHECKING, Any

import datev_lint
from datev_lint.core.parser import BookingRow, ParserError

from .constraints import ConstraintRegistry
from .models import (
    Finding,
    FixCandidate,
    Location,
    Profile,
    RiskLevel,
    Rule,
    Severity,
    Stage,
    ValidationSummary,
)
from .registry import RuleRegistry, get_registry

if TYPE_CHECKING:
    from datev_lint.core.parser import ParseResult


class PipelineResult:
    """Result of pipeline execution."""

    def __init__(
        self,
        findings: list[Finding],
        aborted_at_stage: Stage | None = None,
        engine_version: str = "",
        profile_version: str = "",
        stats: dict[str, int] | None = None,
        file: str | None = None,
    ) -> None:
        self.findings = findings
        self.aborted_at_stage = aborted_at_stage
        self.engine_version = engine_version or datev_lint.__version__
        self.profile_version = profile_version
        self.stats = stats or {}
        self.file = file

    @property
    def has_fatal(self) -> bool:
        """Check if any fatal findings."""
        return any(f.severity == Severity.FATAL for f in self.findings)

    @property
    def has_errors(self) -> bool:
        """Check if any error or fatal findings."""
        return any(f.severity in (Severity.FATAL, Severity.ERROR) for f in self.findings)

    def get_summary(self, file: str, encoding: str, row_count: int) -> ValidationSummary:
        """Create a validation summary."""
        severity_counts = Counter(f.severity for f in self.findings)
        code_counts = Counter(f.code for f in self.findings)

        return ValidationSummary(
            file=file,
            encoding=encoding,
            row_count=row_count,
            engine_version=self.engine_version,
            profile_id=self.stats.get("profile_id", "default"),
            profile_version=self.profile_version,
            fatal_count=severity_counts.get(Severity.FATAL, 0),
            error_count=severity_counts.get(Severity.ERROR, 0),
            warn_count=severity_counts.get(Severity.WARN, 0),
            info_count=severity_counts.get(Severity.INFO, 0),
            hint_count=severity_counts.get(Severity.HINT, 0),
            top_codes=code_counts.most_common(10),
            duration_ms=self.stats.get("duration_ms", 0),
        )


class ExecutionPipeline:
    """
    Orchestrates stage-based rule execution.

    CRITICAL: Aborts on FATAL in parse/header stages.
    """

    # Stages where FATAL findings abort execution
    FATAL_STAGES = {Stage.PARSE, Stage.HEADER}

    def __init__(
        self,
        registry: RuleRegistry | None = None,
        profile: Profile | None = None,
    ) -> None:
        self.registry = registry or get_registry()
        self.profile = profile
        self._rules_by_stage: dict[Stage, list[Rule]] = {}

    def run(self, parse_result: "ParseResult") -> PipelineResult:
        """Run all stages, collecting findings."""
        start_time = time.perf_counter()

        findings: list[Finding] = []
        stats: dict[str, int] = {
            "rows_checked": 0,
            "rules_run": 0,
        }

        # Get profile-filtered rules
        if self.profile:
            rules = self.registry.get_rules_for_profile(self.profile)
            stats["profile_id"] = self.profile.id
        else:
            rules = list(self.registry.rules.values())
            stats["profile_id"] = "default"

        # Group rules by stage
        self._rules_by_stage = {}
        for rule in rules:
            if rule.stage not in self._rules_by_stage:
                self._rules_by_stage[rule.stage] = []
            self._rules_by_stage[rule.stage].append(rule)

        # Include parser errors as findings
        for error in parse_result.header_errors:
            findings.append(
                Finding(
                    code=error.code,
                    rule_version="1.0.0",
                    engine_version=datev_lint.__version__,
                    severity=Severity(error.severity.value),
                    title=error.title,
                    message=error.message,
                    location=Location(
                        file=error.location.file,
                        row_no=error.location.line_no,
                        column=error.location.column,
                        field=error.location.field,
                    ),
                    context=error.context,
                )
            )

        # Run stages in order
        for stage in Stage:
            stage_findings = self._run_stage(stage, parse_result)
            findings.extend(stage_findings)
            stats["rules_run"] += len(self._rules_by_stage.get(stage, []))

            # Check for fatal abort
            if stage in self.FATAL_STAGES:
                if any(f.severity == Severity.FATAL for f in stage_findings):
                    end_time = time.perf_counter()
                    stats["duration_ms"] = int((end_time - start_time) * 1000)
                    return PipelineResult(
                        findings=findings,
                        aborted_at_stage=stage,
                        profile_version=self.profile.version if self.profile else "1.0.0",
                        stats=stats,
                    )

        end_time = time.perf_counter()
        stats["duration_ms"] = int((end_time - start_time) * 1000)

        return PipelineResult(
            findings=findings,
            profile_version=self.profile.version if self.profile else "1.0.0",
            stats=stats,
        )

    def _run_stage(self, stage: Stage, parse_result: "ParseResult") -> list[Finding]:
        """Run all rules for a stage."""
        rules = self._rules_by_stage.get(stage, [])
        if not rules:
            return []

        findings: list[Finding] = []
        filename = str(parse_result.file_path)

        if stage == Stage.HEADER:
            # Run header rules
            for rule in rules:
                stage_findings = self._run_header_rule(rule, parse_result, filename)
                findings.extend(stage_findings)

        elif stage in (Stage.SCHEMA, Stage.ROW_SEMANTIC):
            # Run row rules
            row_no = 0
            for item in parse_result.rows:
                if isinstance(item, ParserError):
                    continue

                row_no += 1
                for rule in rules:
                    row_findings = self._run_row_rule(rule, item, filename)
                    findings.extend(row_findings)

        elif stage == Stage.CROSS_ROW:
            # Cross-row rules need to collect data first
            # This is handled by specialized rules
            for rule in rules:
                cross_findings = self._run_cross_row_rule(rule, parse_result, filename)
                findings.extend(cross_findings)

        return findings

    def _run_header_rule(
        self,
        rule: Rule,
        parse_result: "ParseResult",
        filename: str,
    ) -> list[Finding]:
        """Run a single header rule."""
        findings: list[Finding] = []
        header = parse_result.header

        # Get the field to validate
        field_name = rule.selector.get("field")
        if not field_name:
            return findings

        # Get field value from header
        value = getattr(header, field_name, None)
        if value is None:
            value = ""
        else:
            value = str(value)

        # Check constraint
        is_valid = ConstraintRegistry.check(value, rule.constraint)

        if not is_valid:
            message = ConstraintRegistry.get_message(value, rule.constraint, "de")
            findings.append(
                Finding(
                    code=rule.id,
                    rule_version=rule.version,
                    engine_version=datev_lint.__version__,
                    severity=rule.severity,
                    title=rule.title,
                    message=rule.get_message("de") or message,
                    location=Location(file=filename, row_no=1, field=field_name),
                    context={"raw_value": value},
                )
            )

        return findings

    def _run_row_rule(
        self,
        rule: Rule,
        row: BookingRow,
        filename: str,
    ) -> list[Finding]:
        """Run a single row rule."""
        findings: list[Finding] = []

        # Get the field to validate
        field_name = rule.selector.get("field")
        if not field_name:
            return findings

        # Get field value
        value = row.get_raw(field_name)
        if value is None:
            # Check if required
            if rule.constraint.type == "required":
                findings.append(
                    self._create_finding(rule, "", row.row_no, field_name, filename)
                )
            return findings

        # Check constraint
        is_valid = ConstraintRegistry.check(value, rule.constraint)

        if not is_valid:
            finding = self._create_finding(rule, value, row.row_no, field_name, filename)

            # Add fix candidates if available
            if rule.fix:
                fix_candidates = self._generate_fix_candidates(rule, value, field_name)
                finding = Finding(
                    code=finding.code,
                    rule_version=finding.rule_version,
                    engine_version=finding.engine_version,
                    severity=finding.severity,
                    title=finding.title,
                    message=finding.message,
                    location=finding.location,
                    context=finding.context,
                    fix_candidates=fix_candidates,
                    docs_url=finding.docs_url,
                )

            findings.append(finding)

        return findings

    def _run_cross_row_rule(
        self,
        rule: Rule,
        parse_result: "ParseResult",
        filename: str,
    ) -> list[Finding]:
        """Run a cross-row rule (e.g., duplicate detection)."""
        # Cross-row rules are typically implemented as Python plugins
        # This is a placeholder for the cross-row execution
        return []

    def _create_finding(
        self,
        rule: Rule,
        value: str,
        row_no: int,
        field_name: str,
        filename: str,
    ) -> Finding:
        """Create a finding from a rule violation."""
        message = ConstraintRegistry.get_message(value, rule.constraint, "de")

        return Finding(
            code=rule.id,
            rule_version=rule.version,
            engine_version=datev_lint.__version__,
            severity=rule.severity,
            title=rule.title,
            message=rule.get_message("de") or message,
            location=Location(file=filename, row_no=row_no, field=field_name),
            context={"raw_value": value},
            docs_url=rule.docs_url,
        )

    def _generate_fix_candidates(
        self,
        rule: Rule,
        value: str,
        field_name: str,
    ) -> list[FixCandidate]:
        """Generate fix candidates for a rule violation."""
        candidates: list[FixCandidate] = []

        if not rule.fix:
            return candidates

        for step in rule.fix.steps:
            new_value = value

            if step.operation == "upper":
                new_value = value.upper()
            elif step.operation == "truncate":
                max_len = step.params.get("max_length", rule.constraint.value or 36)
                new_value = value[:max_len]
            elif step.operation == "sanitize_chars":
                # Remove invalid characters based on pattern
                import re

                pattern = step.params.get("pattern", r"[^A-Z0-9_$&%*+\-/]")
                new_value = re.sub(pattern, "", value.upper())

            if new_value != value:
                candidates.append(
                    FixCandidate(
                        operation=step.operation,
                        field=field_name,
                        old_value=value,
                        new_value=new_value,
                        risk=rule.fix.risk,
                        requires_approval=rule.fix.requires_approval,
                    )
                )

        return candidates
