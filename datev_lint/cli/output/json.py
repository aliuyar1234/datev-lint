"""
JSON output adapter.

Renders findings as JSON for machine processing.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, TextIO

from datev_lint.cli.output.base import OutputAdapter, OutputFormat

if TYPE_CHECKING:
    from datev_lint.core.rules.models import Finding, ValidationSummary
    from datev_lint.core.rules.pipeline import PipelineResult
    from datev_lint.core.fix.models import PatchPlan


class JsonOutput(OutputAdapter):
    """JSON output adapter."""

    format = OutputFormat.JSON

    def __init__(self, stream: TextIO | None = None, color: bool = False, indent: int = 2):
        super().__init__(stream=stream, color=False)  # Never colorize JSON
        self.indent = indent

    def render_findings(
        self,
        findings: list["Finding"],
        summary: "ValidationSummary | None" = None,
    ) -> str:
        """Render findings as JSON."""
        output: dict[str, Any] = {
            "findings": [self._finding_to_dict(f) for f in findings],
        }

        if summary:
            output["summary"] = self._summary_to_dict(summary)

        return json.dumps(output, indent=self.indent, default=str)

    def render_result(self, result: "PipelineResult") -> str:
        """Render pipeline result as JSON."""
        from datev_lint.core.rules.models import ValidationSummary

        summary = ValidationSummary(
            file=result.file or "<unknown>",
            encoding="utf-8",
            row_count=0,
            engine_version="0.1.0",
            profile_id="default",
            profile_version="1.0.0",
            fatal_count=sum(1 for f in result.findings if f.severity.value == "fatal"),
            error_count=sum(1 for f in result.findings if f.severity.value == "error"),
            warn_count=sum(1 for f in result.findings if f.severity.value == "warn"),
            info_count=sum(1 for f in result.findings if f.severity.value == "info"),
            hint_count=sum(1 for f in result.findings if f.severity.value == "hint"),
        )

        return self.render_findings(result.findings, summary)

    def render_patch_plan(self, plan: "PatchPlan") -> str:
        """Render patch plan as JSON."""
        output = {
            "file_path": plan.file_path,
            "file_checksum": plan.file_checksum,
            "patches": [
                {
                    "row_no": p.row_no,
                    "field": p.field,
                    "operation": p.operation.value,
                    "old_value": p.old_value,
                    "new_value": p.new_value,
                    "risk": p.risk.value,
                    "rule_id": p.rule_id,
                    "rule_version": p.rule_version,
                    "requires_approval": p.requires_approval,
                }
                for p in plan.patches
            ],
            "conflicts": [
                {
                    "row_no": c.row_no,
                    "field": c.field,
                    "patch_count": len(c.patches),
                    "resolution": c.resolution.value,
                }
                for c in plan.conflicts
            ],
            "summary": {
                "total_patches": plan.total_patches,
                "low_risk_count": plan.low_risk_count,
                "medium_risk_count": plan.medium_risk_count,
                "high_risk_count": plan.high_risk_count,
                "has_conflicts": plan.has_conflicts,
                "requires_approval": plan.requires_approval,
            },
        }

        return json.dumps(output, indent=self.indent)

    def _finding_to_dict(self, finding: "Finding") -> dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "code": finding.code,
            "rule_version": finding.rule_version,
            "engine_version": finding.engine_version,
            "severity": finding.severity.value,
            "title": finding.title,
            "message": finding.message,
            "location": {
                "file": finding.location.file,
                "row_no": finding.location.row_no,
                "column": finding.location.column,
                "field": finding.location.field,
            },
            "context": finding.context,
            "fix_candidates": [
                {
                    "operation": fc.operation,
                    "field": fc.field,
                    "old_value": fc.old_value,
                    "new_value": fc.new_value,
                    "risk": fc.risk.value,
                }
                for fc in finding.fix_candidates
            ],
            "docs_url": finding.docs_url,
        }

    def _summary_to_dict(self, summary: "ValidationSummary") -> dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "file": summary.file,
            "encoding": summary.encoding,
            "row_count": summary.row_count,
            "engine_version": summary.engine_version,
            "profile_id": summary.profile_id,
            "profile_version": summary.profile_version,
            "fatal_count": summary.fatal_count,
            "error_count": summary.error_count,
            "warn_count": summary.warn_count,
            "info_count": summary.info_count,
            "hint_count": summary.hint_count,
            "total_findings": summary.total_findings,
            "has_errors": summary.has_errors,
        }
