"""
SARIF output adapter.

Renders findings as SARIF 2.1.0 for GitHub Code Scanning.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, TextIO

from datev_lint.cli.output.base import OutputAdapter, OutputFormat

if TYPE_CHECKING:
    from datev_lint.core.rules.models import Finding, ValidationSummary
    from datev_lint.core.rules.pipeline import PipelineResult


# SARIF severity mapping
SARIF_LEVEL = {
    "fatal": "error",
    "error": "error",
    "warn": "warning",
    "info": "note",
    "hint": "none",
}


class SarifOutput(OutputAdapter):
    """SARIF 2.1.0 output adapter."""

    format = OutputFormat.SARIF
    SARIF_VERSION = "2.1.0"
    SARIF_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"

    def __init__(self, stream: TextIO | None = None, color: bool = False, indent: int = 2):
        super().__init__(stream=stream, color=False)
        self.indent = indent

    def render_findings(
        self,
        findings: list["Finding"],
        summary: "ValidationSummary | None" = None,
    ) -> str:
        """Render findings as SARIF."""
        # Collect unique rules
        rules_dict: dict[str, "Finding"] = {}
        for finding in findings:
            if finding.code not in rules_dict:
                rules_dict[finding.code] = finding

        sarif = {
            "$schema": self.SARIF_SCHEMA,
            "version": self.SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "datev-lint",
                            "version": "0.1.0",
                            "informationUri": "https://github.com/datev-lint/datev-lint",
                            "rules": [
                                self._rule_to_sarif(f) for f in rules_dict.values()
                            ],
                        }
                    },
                    "results": [self._finding_to_sarif(f) for f in findings],
                }
            ],
        }

        return json.dumps(sarif, indent=self.indent)

    def render_result(self, result: "PipelineResult") -> str:
        """Render pipeline result as SARIF."""
        return self.render_findings(result.findings)

    def _rule_to_sarif(self, finding: "Finding") -> dict[str, Any]:
        """Convert a rule to SARIF rule descriptor."""
        return {
            "id": finding.code,
            "name": finding.title,
            "shortDescription": {
                "text": finding.title,
            },
            "fullDescription": {
                "text": finding.message,
            },
            "defaultConfiguration": {
                "level": SARIF_LEVEL.get(finding.severity.value, "note"),
            },
            "helpUri": finding.docs_url,
            "properties": {
                "rule_version": finding.rule_version,
            },
        }

    def _finding_to_sarif(self, finding: "Finding") -> dict[str, Any]:
        """Convert a finding to SARIF result."""
        result: dict[str, Any] = {
            "ruleId": finding.code,
            "level": SARIF_LEVEL.get(finding.severity.value, "note"),
            "message": {
                "text": finding.message,
            },
        }

        # Add location if available
        if finding.location.file or finding.location.row_no:
            locations = []
            location: dict[str, Any] = {
                "physicalLocation": {}
            }

            if finding.location.file:
                location["physicalLocation"]["artifactLocation"] = {
                    "uri": finding.location.file,
                }

            if finding.location.row_no:
                location["physicalLocation"]["region"] = {
                    "startLine": finding.location.row_no,
                }
                if finding.location.column:
                    location["physicalLocation"]["region"]["startColumn"] = finding.location.column

            locations.append(location)
            result["locations"] = locations

        # Add fix suggestions
        if finding.fix_candidates:
            fixes = []
            for fc in finding.fix_candidates:
                fix = {
                    "description": {
                        "text": f"Apply {fc.operation}: {fc.old_value} → {fc.new_value}",
                    },
                    "artifactChanges": [
                        {
                            "artifactLocation": {
                                "uri": finding.location.file or "<unknown>",
                            },
                            "replacements": [
                                {
                                    "deletedRegion": {
                                        "startLine": finding.location.row_no or 1,
                                    },
                                    "insertedContent": {
                                        "text": fc.new_value,
                                    },
                                }
                            ],
                        }
                    ],
                }
                fixes.append(fix)
            result["fixes"] = fixes

        return result
