"""Tests for risk management."""

from datev_lint.core.fix.models import Patch, PatchOperation, PatchPlan
from datev_lint.core.fix.risk import (
    filter_by_risk,
    format_risk_warning,
    get_operation_risk,
    get_risk_summary,
    requires_interactive_approval,
    should_apply,
)
from datev_lint.core.rules.models import RiskLevel


def make_patch(
    risk: RiskLevel = RiskLevel.LOW,
    requires_approval: bool = False,
    operation: PatchOperation = PatchOperation.UPPER,
) -> Patch:
    """Helper to create patches."""
    return Patch(
        row_no=3,
        field="belegfeld1",
        operation=operation,
        old_value="test",
        new_value="TEST",
        risk=risk,
        requires_approval=requires_approval,
        rule_id="DVL-TEST-001",
        rule_version="1.0.0",
    )


class TestGetOperationRisk:
    """Tests for get_operation_risk."""

    def test_low_risk_operations(self) -> None:
        """Test low-risk operations."""
        assert get_operation_risk(PatchOperation.UPPER) == RiskLevel.LOW
        assert get_operation_risk(PatchOperation.NORMALIZE_DECIMAL) == RiskLevel.LOW

    def test_medium_risk_operations(self) -> None:
        """Test medium-risk operations."""
        assert get_operation_risk(PatchOperation.TRUNCATE) == RiskLevel.MEDIUM
        assert get_operation_risk(PatchOperation.SANITIZE_CHARS) == RiskLevel.MEDIUM

    def test_high_risk_operations(self) -> None:
        """Test high-risk operations."""
        assert get_operation_risk(PatchOperation.DELETE_ROW) == RiskLevel.HIGH


class TestShouldApply:
    """Tests for should_apply."""

    def test_low_risk_with_low_accept(self) -> None:
        """Test low risk with low acceptance."""
        patch = make_patch(risk=RiskLevel.LOW)
        assert should_apply(patch, RiskLevel.LOW) is True

    def test_medium_risk_with_low_accept(self) -> None:
        """Test medium risk with low acceptance."""
        patch = make_patch(risk=RiskLevel.MEDIUM)
        assert should_apply(patch, RiskLevel.LOW) is False

    def test_medium_risk_with_medium_accept(self) -> None:
        """Test medium risk with medium acceptance."""
        patch = make_patch(risk=RiskLevel.MEDIUM)
        assert should_apply(patch, RiskLevel.MEDIUM) is True

    def test_high_risk_with_high_accept(self) -> None:
        """Test high risk with high acceptance."""
        patch = make_patch(risk=RiskLevel.HIGH)
        assert should_apply(patch, RiskLevel.HIGH) is True

    def test_requires_approval_without_high_accept(self) -> None:
        """Test requires_approval blocks unless high accept."""
        patch = make_patch(risk=RiskLevel.LOW, requires_approval=True)
        assert should_apply(patch, RiskLevel.LOW) is False
        assert should_apply(patch, RiskLevel.MEDIUM) is False
        assert should_apply(patch, RiskLevel.HIGH) is True


class TestFilterByRisk:
    """Tests for filter_by_risk."""

    def test_filter_mixed_risks(self) -> None:
        """Test filtering mixed risk levels."""
        patches = [
            make_patch(risk=RiskLevel.LOW),
            make_patch(risk=RiskLevel.MEDIUM),
            make_patch(risk=RiskLevel.HIGH),
        ]

        plan = PatchPlan(
            file_path="test.csv",
            file_checksum="abc",
            patches=patches,
            conflicts=[],
            low_risk_count=1,
            medium_risk_count=1,
            high_risk_count=1,
        )

        # Filter with low acceptance
        filtered = filter_by_risk(plan, RiskLevel.LOW)
        assert len(filtered) == 1
        assert filtered[0].risk == RiskLevel.LOW

        # Filter with medium acceptance
        filtered = filter_by_risk(plan, RiskLevel.MEDIUM)
        assert len(filtered) == 2

        # Filter with high acceptance
        filtered = filter_by_risk(plan, RiskLevel.HIGH)
        assert len(filtered) == 3


class TestRequiresInteractiveApproval:
    """Tests for requires_interactive_approval."""

    def test_no_approval_needed(self) -> None:
        """Test no approval needed."""
        plan = PatchPlan(
            file_path="test.csv",
            file_checksum="abc",
            patches=[make_patch(requires_approval=False)],
            conflicts=[],
        )

        assert requires_interactive_approval(plan) is False

    def test_approval_needed(self) -> None:
        """Test approval needed."""
        plan = PatchPlan(
            file_path="test.csv",
            file_checksum="abc",
            patches=[
                make_patch(requires_approval=False),
                make_patch(requires_approval=True),
            ],
            conflicts=[],
        )

        assert requires_interactive_approval(plan) is True


class TestGetRiskSummary:
    """Tests for get_risk_summary."""

    def test_summary(self) -> None:
        """Test risk summary."""
        patches = [
            make_patch(risk=RiskLevel.LOW),
            make_patch(risk=RiskLevel.LOW),
            make_patch(risk=RiskLevel.MEDIUM),
            make_patch(risk=RiskLevel.HIGH, requires_approval=True),
        ]

        plan = PatchPlan(
            file_path="test.csv",
            file_checksum="abc",
            patches=patches,
            conflicts=[],
            low_risk_count=2,
            medium_risk_count=1,
            high_risk_count=1,
        )

        summary = get_risk_summary(plan)

        assert summary["low"] == 2
        assert summary["medium"] == 1
        assert summary["high"] == 1
        assert summary["requires_approval"] == 1


class TestFormatRiskWarning:
    """Tests for format_risk_warning."""

    def test_format_warning(self) -> None:
        """Test formatting risk warning."""
        patches = [
            make_patch(risk=RiskLevel.LOW),
            make_patch(risk=RiskLevel.HIGH, requires_approval=True),
        ]

        plan = PatchPlan(
            file_path="test.csv",
            file_checksum="abc",
            patches=patches,
            conflicts=[],
            low_risk_count=1,
            high_risk_count=1,
        )

        warning = format_risk_warning(plan)

        assert "HIGH" in warning
        assert "LOW" in warning
        assert "approval" in warning.lower()

    def test_format_empty_plan(self) -> None:
        """Test formatting empty plan."""
        plan = PatchPlan(
            file_path="test.csv",
            file_checksum="abc",
            patches=[],
            conflicts=[],
        )

        warning = format_risk_warning(plan)
        assert "No patches" in warning
