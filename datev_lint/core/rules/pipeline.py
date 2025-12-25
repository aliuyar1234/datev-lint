"""
Execution Pipeline.

Orchestrates stage-based rule execution.
"""

from __future__ import annotations

import time
from collections import Counter
from typing import TYPE_CHECKING, ClassVar

import datev_lint
from datev_lint.core.parser import BookingRow, ParserError

from .constraints import ConstraintRegistry
from .models import (
    Finding,
    FixCandidate,
    Location,
    Profile,
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
        encoding: str | None = None,
        row_count: int | None = None,
        profile_id: str = "default",
    ) -> None:
        self.findings = findings
        self.aborted_at_stage = aborted_at_stage
        self.engine_version = engine_version or datev_lint.__version__
        self.profile_version = profile_version
        self.stats = stats or {}
        self.file = file
        self.encoding = encoding
        self.row_count = row_count
        self.profile_id = profile_id

    @property
    def has_fatal(self) -> bool:
        """Check if any fatal findings."""
        return any(f.severity == Severity.FATAL for f in self.findings)

    @property
    def has_errors(self) -> bool:
        """Check if any error or fatal findings."""
        return any(f.severity in (Severity.FATAL, Severity.ERROR) for f in self.findings)

    def get_summary(
        self,
        file: str | None = None,
        encoding: str | None = None,
        row_count: int | None = None,
    ) -> ValidationSummary:
        """Create a validation summary."""
        severity_counts = Counter(f.severity for f in self.findings)
        code_counts = Counter(f.code for f in self.findings)

        file_value = file or self.file or "<unknown>"
        encoding_value = encoding or self.encoding or "<unknown>"
        row_count_value = (self.row_count or 0) if row_count is None else row_count

        return ValidationSummary(
            file=file_value,
            encoding=encoding_value,
            row_count=row_count_value,
            engine_version=self.engine_version,
            profile_id=self.profile_id,
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
    FATAL_STAGES: ClassVar[set[Stage]] = {Stage.PARSE, Stage.HEADER}

    def __init__(
        self,
        registry: RuleRegistry | None = None,
        profile: Profile | None = None,
    ) -> None:
        self.registry = registry or get_registry()
        self.profile = profile
        self._rules_by_stage: dict[Stage, list[Rule]] = {}

    def run(self, parse_result: ParseResult) -> PipelineResult:
        """Run all stages, collecting findings."""
        start_time = time.perf_counter()

        findings: list[Finding] = []
        stats: dict[str, int] = {
            "rows_checked": 0,
            "rules_run": 0,
        }
        filename = str(parse_result.file_path)

        # Get profile-filtered rules
        if self.profile:
            rules = self.registry.get_rules_for_profile(self.profile)
        else:
            rules = list(self.registry.rules.values())

        # Group rules by stage
        self._rules_by_stage = {}
        for rule in rules:
            if rule.stage not in self._rules_by_stage:
                self._rules_by_stage[rule.stage] = []
            self._rules_by_stage[rule.stage].append(rule)

        # Include parser errors (header/columns) as findings.
        parser_findings = [
            self._parser_error_to_finding(error, filename) for error in parse_result.header_errors
        ]
        findings.extend(parser_findings)

        # Abort early if parsing already failed fatally.
        if any(f.severity == Severity.FATAL for f in parser_findings):
            end_time = time.perf_counter()
            stats["duration_ms"] = int((end_time - start_time) * 1000)
            return PipelineResult(
                findings=findings,
                aborted_at_stage=Stage.PARSE,
                profile_version=self.profile.version if self.profile else "1.0.0",
                stats=stats,
                file=filename,
                encoding=parse_result.encoding,
                row_count=0,
                profile_id=self.profile.id if self.profile else "default",
            )

        # Run stages in order
        row_count = 0
        for stage in Stage:
            # Run SCHEMA + ROW_SEMANTIC in a single pass for performance.
            if stage == Stage.SCHEMA:
                schema_rules = self._rules_by_stage.get(Stage.SCHEMA, [])
                semantic_rules = self._rules_by_stage.get(Stage.ROW_SEMANTIC, [])

                stage_findings, row_count = self._run_row_stages(
                    parse_result=parse_result,
                    schema_rules=schema_rules,
                    semantic_rules=semantic_rules,
                    filename=filename,
                )
                findings.extend(stage_findings)
                stats["rows_checked"] = row_count
                stats["rules_run"] += len(schema_rules) + len(semantic_rules)
                continue

            if stage == Stage.ROW_SEMANTIC:
                continue

            stage_findings = self._run_stage(stage, parse_result, filename)
            findings.extend(stage_findings)
            stats["rules_run"] += len(self._rules_by_stage.get(stage, []))

            # Check for fatal abort
            if stage in self.FATAL_STAGES and any(
                f.severity == Severity.FATAL for f in stage_findings
            ):
                end_time = time.perf_counter()
                stats["duration_ms"] = int((end_time - start_time) * 1000)
                return PipelineResult(
                    findings=findings,
                    aborted_at_stage=stage,
                    profile_version=self.profile.version if self.profile else "1.0.0",
                    stats=stats,
                    file=filename,
                    encoding=parse_result.encoding,
                    row_count=row_count,
                    profile_id=self.profile.id if self.profile else "default",
                )

        end_time = time.perf_counter()
        stats["duration_ms"] = int((end_time - start_time) * 1000)

        return PipelineResult(
            findings=findings,
            profile_version=self.profile.version if self.profile else "1.0.0",
            stats=stats,
            file=filename,
            encoding=parse_result.encoding,
            row_count=row_count,
            profile_id=self.profile.id if self.profile else "default",
        )

    def _run_row_stages(
        self,
        *,
        parse_result: ParseResult,
        schema_rules: list[Rule],
        semantic_rules: list[Rule],
        filename: str,
    ) -> tuple[list[Finding], int]:
        """Run schema + semantic row rules in a single pass over the file."""
        findings: list[Finding] = []
        rows_checked = 0

        if not schema_rules and not semantic_rules:
            return findings, rows_checked

        for item in parse_result.rows:
            if isinstance(item, ParserError):
                findings.append(self._parser_error_to_finding(item, filename))
                continue

            rows_checked += 1
            for rule in schema_rules:
                findings.extend(self._run_row_rule(rule, item, filename))
            for rule in semantic_rules:
                findings.extend(self._run_row_rule(rule, item, filename))

        return findings, rows_checked

    def _run_stage(
        self,
        stage: Stage,
        parse_result: ParseResult,
        filename: str,
    ) -> list[Finding]:
        """Run all rules for a stage."""
        rules = self._rules_by_stage.get(stage, [])
        if not rules:
            return []

        findings: list[Finding] = []

        if stage == Stage.HEADER:
            for rule in rules:
                findings.extend(self._run_header_rule(rule, parse_result, filename))

        elif stage == Stage.CROSS_ROW:
            # Cross-row rules need to collect data first.
            for rule in rules:
                findings.extend(self._run_cross_row_rule(rule, parse_result, filename))

        return findings

    def _parser_error_to_finding(self, error: ParserError, filename: str) -> Finding:
        """Convert a ParserError to a Finding."""
        return Finding(
            code=error.code,
            rule_version="1.0.0",
            engine_version=datev_lint.__version__,
            severity=Severity(error.severity.value),
            title=error.title,
            message=error.message,
            location=Location(
                file=error.location.file or filename,
                row_no=error.location.line_no,
                column=error.location.column,
                field=error.location.field,
            ),
            context=error.context,
        )

    def _run_header_rule(
        self,
        rule: Rule,
        parse_result: ParseResult,
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
        value = "" if value is None else str(value)

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
                findings.append(self._create_finding(rule, "", row.row_no, field_name, filename))
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
        _rule: Rule,
        _parse_result: ParseResult,
        _filename: str,
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
