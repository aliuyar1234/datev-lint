"""Tests for CLI output adapters."""

import json
import xml.etree.ElementTree as ET

from datev_lint.cli.output import (
    JsonOutput,
    JunitOutput,
    OutputFormat,
    SarifOutput,
    TerminalOutput,
    get_output_adapter,
)
from datev_lint.core.rules.models import Finding, Location, Severity


def make_finding(
    code: str = "DVL-TEST-001",
    severity: Severity = Severity.ERROR,
    message: str = "Test message",
    row_no: int | None = 3,
) -> Finding:
    """Create a test finding."""
    return Finding(
        code=code,
        rule_version="1.0.0",
        engine_version="0.1.0",
        severity=severity,
        title="Test Finding",
        message=message,
        location=Location(file="test.csv", row_no=row_no),
    )


class TestTerminalOutput:
    """Tests for TerminalOutput."""

    def test_render_empty_findings(self) -> None:
        """Test rendering no findings."""
        output = TerminalOutput(color=False)
        result = output.render_findings([])
        assert "No issues found" in result

    def test_render_with_findings(self) -> None:
        """Test rendering findings."""
        findings = [
            make_finding(severity=Severity.ERROR, message="Error message"),
            make_finding(code="DVL-TEST-002", severity=Severity.WARN, message="Warning"),
        ]
        output = TerminalOutput(color=False)
        result = output.render_findings(findings)

        assert "test.csv" in result
        assert "Error message" in result
        assert "Warning" in result

    def test_severity_symbols(self) -> None:
        """Test severity symbols are included."""
        findings = [make_finding(severity=Severity.ERROR)]
        output = TerminalOutput(color=False)
        result = output.render_findings(findings)

        assert "✖" in result or "Error" in result


class TestJsonOutput:
    """Tests for JsonOutput."""

    def test_render_findings(self) -> None:
        """Test rendering findings as JSON."""
        findings = [make_finding()]
        output = JsonOutput()
        result = output.render_findings(findings)

        parsed = json.loads(result)
        assert "findings" in parsed
        assert len(parsed["findings"]) == 1
        assert parsed["findings"][0]["code"] == "DVL-TEST-001"

    def test_json_structure(self) -> None:
        """Test JSON has correct structure."""
        findings = [make_finding()]
        output = JsonOutput()
        result = output.render_findings(findings)

        parsed = json.loads(result)
        finding = parsed["findings"][0]

        assert "code" in finding
        assert "rule_version" in finding
        assert "severity" in finding
        assert "message" in finding
        assert "location" in finding

    def test_render_patch_plan(self) -> None:
        """Test rendering patch plan as JSON."""
        from datev_lint.core.fix.models import Patch, PatchOperation, PatchPlan
        from datev_lint.core.rules.models import RiskLevel

        plan = PatchPlan(
            file_path="test.csv",
            file_checksum="abc123",
            patches=[
                Patch(
                    row_no=3,
                    field="belegfeld1",
                    operation=PatchOperation.UPPER,
                    old_value="test",
                    new_value="TEST",
                    risk=RiskLevel.LOW,
                    rule_id="DVL-FIELD-011",
                    rule_version="1.0.0",
                )
            ],
            conflicts=[],
        )

        output = JsonOutput()
        result = output.render_patch_plan(plan)

        parsed = json.loads(result)
        assert "patches" in parsed
        assert len(parsed["patches"]) == 1
        assert parsed["patches"][0]["field"] == "belegfeld1"


class TestSarifOutput:
    """Tests for SarifOutput."""

    def test_sarif_version(self) -> None:
        """Test SARIF version is correct."""
        findings = [make_finding()]
        output = SarifOutput()
        result = output.render_findings(findings)

        parsed = json.loads(result)
        assert parsed["version"] == "2.1.0"

    def test_sarif_structure(self) -> None:
        """Test SARIF has correct structure."""
        findings = [make_finding()]
        output = SarifOutput()
        result = output.render_findings(findings)

        parsed = json.loads(result)
        assert "$schema" in parsed
        assert "runs" in parsed
        assert len(parsed["runs"]) == 1

        run = parsed["runs"][0]
        assert "tool" in run
        assert "results" in run

        tool = run["tool"]["driver"]
        assert tool["name"] == "datev-lint"
        assert "rules" in tool

    def test_sarif_results(self) -> None:
        """Test SARIF results are correct."""
        findings = [make_finding()]
        output = SarifOutput()
        result = output.render_findings(findings)

        parsed = json.loads(result)
        results = parsed["runs"][0]["results"]

        assert len(results) == 1
        assert results[0]["ruleId"] == "DVL-TEST-001"
        assert results[0]["level"] == "error"


class TestGetOutputAdapter:
    """Tests for get_output_adapter."""

    def test_get_terminal_adapter(self) -> None:
        """Test getting terminal adapter."""
        adapter = get_output_adapter(OutputFormat.TERMINAL)
        assert isinstance(adapter, TerminalOutput)

    def test_get_json_adapter(self) -> None:
        """Test getting JSON adapter."""
        adapter = get_output_adapter(OutputFormat.JSON)
        assert isinstance(adapter, JsonOutput)

    def test_get_sarif_adapter(self) -> None:
        """Test getting SARIF adapter."""
        adapter = get_output_adapter(OutputFormat.SARIF)
        assert isinstance(adapter, SarifOutput)

    def test_get_junit_adapter(self) -> None:
        """Test getting JUnit adapter."""
        adapter = get_output_adapter(OutputFormat.JUNIT)
        assert isinstance(adapter, JunitOutput)

    def test_get_by_string(self) -> None:
        """Test getting adapter by string."""
        adapter = get_output_adapter("json")
        assert isinstance(adapter, JsonOutput)


class TestJunitOutput:
    """Tests for JunitOutput."""

    def test_render_empty_findings(self) -> None:
        """Test rendering no findings as JUnit XML."""
        output = JunitOutput()
        xml = output.render_findings([])

        root = ET.fromstring(xml)  # noqa: S314
        assert root.tag == "testsuite"
        assert root.attrib["tests"] == "1"
        assert root.attrib["failures"] == "0"
        assert root.attrib["errors"] == "0"

    def test_render_counts_by_severity(self) -> None:
        """Test JUnit counters match severity mapping."""
        findings = [
            make_finding(code="DVL-TEST-001", severity=Severity.ERROR),
            make_finding(code="DVL-TEST-002", severity=Severity.WARN),
            make_finding(code="DVL-TEST-003", severity=Severity.FATAL),
            make_finding(code="DVL-TEST-004", severity=Severity.INFO),
        ]

        output = JunitOutput()
        xml = output.render_findings(findings)
        root = ET.fromstring(xml)  # noqa: S314

        assert root.attrib["tests"] == "4"
        assert root.attrib["failures"] == "2"
        assert root.attrib["errors"] == "1"
        assert root.attrib["skipped"] == "1"
