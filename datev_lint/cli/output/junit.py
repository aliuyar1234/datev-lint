"""
JUnit XML output adapter.

Renders findings as JUnit XML for CI systems.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import TYPE_CHECKING, TextIO

from datev_lint.cli.output.base import OutputAdapter, OutputFormat

if TYPE_CHECKING:
    from datev_lint.core.rules.models import Finding, ValidationSummary
    from datev_lint.core.rules.pipeline import PipelineResult


def _location_label(finding: Finding) -> str:
    parts: list[str] = []
    if finding.location.row_no is not None:
        parts.append(f"L{finding.location.row_no}")
    if finding.location.column is not None:
        parts.append(f"C{finding.location.column}")
    if finding.location.field:
        parts.append(str(finding.location.field))
    return ":".join(parts)


def _details(finding: Finding) -> str:
    file_name = finding.location.file or "<unknown>"
    location = _location_label(finding)
    loc_suffix = f" ({location})" if location else ""
    return (
        f"{finding.code}{loc_suffix}\n"
        f"{finding.title}\n"
        f"{finding.message}\n"
        f"File: {file_name}\n"
        f"Severity: {finding.severity.value}\n"
        f"Rule version: {finding.rule_version}\n"
        f"Engine version: {finding.engine_version}\n"
    )


class JunitOutput(OutputAdapter):
    """JUnit XML output adapter."""

    format = OutputFormat.JUNIT

    def __init__(self, stream: TextIO | None = None, color: bool = False):
        del color  # JUnit is never colorized.
        super().__init__(stream=stream, color=False)

    def render_findings(
        self,
        findings: list[Finding],
        summary: ValidationSummary | None = None,
    ) -> str:
        failures = 0
        errors = 0
        skipped = 0

        testsuite = ET.Element(
            "testsuite",
            {
                "name": "datev-lint",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

        if summary:
            properties = ET.SubElement(testsuite, "properties")
            ET.SubElement(properties, "property", {"name": "file", "value": summary.file})
            ET.SubElement(
                properties, "property", {"name": "encoding", "value": str(summary.encoding)}
            )
            ET.SubElement(
                properties, "property", {"name": "row_count", "value": str(summary.row_count)}
            )
            ET.SubElement(
                properties,
                "property",
                {"name": "engine_version", "value": str(summary.engine_version)},
            )

        if not findings:
            ET.SubElement(
                testsuite,
                "testcase",
                {
                    "classname": "datev-lint",
                    "name": "validate",
                },
            )
        else:
            for finding in findings:
                file_name = finding.location.file or "<unknown>"
                location = _location_label(finding)
                name = f"{finding.code} {location}".strip()

                testcase = ET.SubElement(
                    testsuite,
                    "testcase",
                    {
                        "classname": file_name,
                        "name": name,
                    },
                )

                details = _details(finding)
                severity = finding.severity.value

                if severity == "fatal":
                    errors += 1
                    element = ET.SubElement(
                        testcase, "error", {"message": finding.message, "type": severity}
                    )
                    element.text = details
                elif severity in {"error", "warn"}:
                    failures += 1
                    element = ET.SubElement(
                        testcase, "failure", {"message": finding.message, "type": severity}
                    )
                    element.text = details
                else:
                    skipped += 1
                    element = ET.SubElement(testcase, "skipped", {"message": finding.message})
                    element.text = details

        testsuite.set("tests", str(len(testsuite.findall("testcase"))))
        testsuite.set("failures", str(failures))
        testsuite.set("errors", str(errors))
        testsuite.set("skipped", str(skipped))

        ET.indent(testsuite, space="  ")
        xml_bytes: bytes | str = ET.tostring(testsuite, encoding="utf-8", xml_declaration=True)
        if isinstance(xml_bytes, bytes):
            return xml_bytes.decode("utf-8")
        return xml_bytes

    def render_result(self, result: PipelineResult) -> str:
        """Render pipeline result as JUnit XML."""
        return self.render_findings(result.findings, result.get_summary())
