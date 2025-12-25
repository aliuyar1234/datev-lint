"""Tests for fix planner."""

from pathlib import Path

from datev_lint.core.fix.models import ConflictResolution, PatchOperation
from datev_lint.core.fix.planner import PatchPlanner, compute_bytes_checksum
from datev_lint.core.rules.models import (
    Finding,
    FixCandidate,
    Location,
    RiskLevel,
    Severity,
)


class TestPatchPlanner:
    """Tests for PatchPlanner."""

    def test_plan_empty_findings(self, tmp_path: Path) -> None:
        """Test planning with no findings."""
        # Create test file
        test_file = tmp_path / "test.csv"
        test_file.write_text("test content")

        planner = PatchPlanner()
        plan = planner.plan(test_file, [])

        assert plan.total_patches == 0
        assert not plan.has_conflicts

    def test_plan_with_fix_candidate(self, tmp_path: Path) -> None:
        """Test planning with fix candidates."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("test content")

        findings = [
            Finding(
                code="DVL-FIELD-011",
                rule_version="1.0.0",
                engine_version="0.1.0",
                severity=Severity.WARN,
                title="Test",
                message="Test finding",
                location=Location(file=str(test_file), row_no=3, field="belegfeld1"),
                fix_candidates=[
                    FixCandidate(
                        operation="upper",
                        field="belegfeld1",
                        old_value="test",
                        new_value="TEST",
                        risk=RiskLevel.LOW,
                    )
                ],
            )
        ]

        planner = PatchPlanner()
        plan = planner.plan(test_file, findings)

        assert plan.total_patches == 1
        assert plan.patches[0].field == "belegfeld1"
        assert plan.patches[0].operation == PatchOperation.UPPER
        assert plan.low_risk_count == 1

    def test_plan_detects_conflicts(self, tmp_path: Path) -> None:
        """Test conflict detection."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("test content")

        findings = [
            Finding(
                code="DVL-FIELD-011",
                rule_version="1.0.0",
                engine_version="0.1.0",
                severity=Severity.WARN,
                title="Test 1",
                message="First finding",
                location=Location(file=str(test_file), row_no=3, field="belegfeld1"),
                fix_candidates=[
                    FixCandidate(
                        operation="upper",
                        field="belegfeld1",
                        old_value="test",
                        new_value="TEST",
                        risk=RiskLevel.LOW,
                    )
                ],
            ),
            Finding(
                code="DVL-FIELD-013",
                rule_version="1.0.0",
                engine_version="0.1.0",
                severity=Severity.INFO,
                title="Test 2",
                message="Second finding",
                location=Location(file=str(test_file), row_no=3, field="belegfeld1"),
                fix_candidates=[
                    FixCandidate(
                        operation="sanitize_chars",
                        field="belegfeld1",
                        old_value="test",
                        new_value="TST",
                        risk=RiskLevel.MEDIUM,
                    )
                ],
            ),
        ]

        planner = PatchPlanner()
        plan = planner.plan(test_file, findings)

        assert plan.has_conflicts
        assert len(plan.conflicts) == 1
        # First wins by default
        assert plan.total_patches == 1
        assert plan.patches[0].operation == PatchOperation.UPPER

    def test_plan_last_wins_resolution(self, tmp_path: Path) -> None:
        """Test last-wins conflict resolution."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("test content")

        findings = [
            Finding(
                code="DVL-FIELD-011",
                rule_version="1.0.0",
                engine_version="0.1.0",
                severity=Severity.WARN,
                title="Test 1",
                message="First",
                location=Location(file=str(test_file), row_no=3, field="belegfeld1"),
                fix_candidates=[
                    FixCandidate(
                        operation="upper",
                        field="belegfeld1",
                        old_value="test",
                        new_value="TEST",
                        risk=RiskLevel.LOW,
                    )
                ],
            ),
            Finding(
                code="DVL-FIELD-013",
                rule_version="1.0.0",
                engine_version="0.1.0",
                severity=Severity.INFO,
                title="Test 2",
                message="Second",
                location=Location(file=str(test_file), row_no=3, field="belegfeld1"),
                fix_candidates=[
                    FixCandidate(
                        operation="truncate",
                        field="belegfeld1",
                        old_value="test",
                        new_value="tes",
                        risk=RiskLevel.MEDIUM,
                    )
                ],
            ),
        ]

        planner = PatchPlanner(resolution=ConflictResolution.LAST_WINS)
        plan = planner.plan(test_file, findings)

        assert plan.total_patches == 1
        assert plan.patches[0].operation == PatchOperation.TRUNCATE


class TestComputeChecksum:
    """Tests for checksum computation."""

    def test_compute_bytes_checksum(self) -> None:
        """Test computing checksum of bytes."""
        data = b"test content"
        checksum = compute_bytes_checksum(data)

        assert len(checksum) == 64  # SHA-256 hex
        assert checksum == "6ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72"
