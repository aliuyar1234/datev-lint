"""Tests for fix preview."""

from datev_lint.core.fix.models import Patch, PatchOperation, PatchPlan
from datev_lint.core.fix.preview import DiffGenerator, preview_diff, preview_patch
from datev_lint.core.rules.models import RiskLevel


class TestDiffGenerator:
    """Tests for DiffGenerator."""

    def test_generate_empty_plan(self) -> None:
        """Test generating diff from empty plan."""
        plan = PatchPlan(
            file_path="test.csv",
            file_checksum="abc123",
            patches=[],
            conflicts=[],
        )

        generator = DiffGenerator(colorize=False)
        diff = generator.generate(plan)

        assert diff.total_changes == 0
        assert not diff.has_changes()

    def test_generate_with_patches(self) -> None:
        """Test generating diff with patches."""
        patches = [
            Patch(
                row_no=3,
                field="belegfeld1",
                operation=PatchOperation.UPPER,
                old_value="test",
                new_value="TEST",
                risk=RiskLevel.LOW,
                rule_id="DVL-FIELD-011",
                rule_version="1.0.0",
            ),
            Patch(
                row_no=4,
                field="belegfeld1",
                operation=PatchOperation.TRUNCATE,
                old_value="verylongvalue",
                new_value="verylong",
                risk=RiskLevel.MEDIUM,
                rule_id="DVL-FIELD-012",
                rule_version="1.0.0",
            ),
        ]

        plan = PatchPlan(
            file_path="test.csv",
            file_checksum="abc123",
            patches=patches,
            conflicts=[],
        )

        generator = DiffGenerator(colorize=False)
        diff = generator.generate(plan)

        assert diff.total_changes == 2
        assert diff.has_changes()

    def test_format_diff(self) -> None:
        """Test formatting diff output."""
        patches = [
            Patch(
                row_no=3,
                field="belegfeld1",
                operation=PatchOperation.UPPER,
                old_value="test",
                new_value="TEST",
                risk=RiskLevel.LOW,
                rule_id="DVL-FIELD-011",
                rule_version="1.0.0",
            ),
        ]

        plan = PatchPlan(
            file_path="test.csv",
            file_checksum="abc123def456",
            patches=patches,
            conflicts=[],
        )

        generator = DiffGenerator(colorize=False)
        diff = generator.generate(plan)
        output = generator.format(diff)

        assert "test.csv" in output
        assert "Row 3" in output
        assert "belegfeld1" in output
        assert "[low]" in output
        assert "DVL-FIELD-011" in output


class TestPreviewFunctions:
    """Tests for preview convenience functions."""

    def test_preview_diff(self) -> None:
        """Test preview_diff function."""
        patches = [
            Patch(
                row_no=3,
                field="belegfeld1",
                operation=PatchOperation.UPPER,
                old_value="test",
                new_value="TEST",
                risk=RiskLevel.LOW,
                rule_id="DVL-FIELD-011",
                rule_version="1.0.0",
            ),
        ]

        plan = PatchPlan(
            file_path="test.csv",
            file_checksum="abc123",
            patches=patches,
            conflicts=[],
        )

        output = preview_diff(plan, colorize=False)
        assert "test.csv" in output
        assert "Row 3" in output

    def test_preview_patch(self) -> None:
        """Test preview_patch function."""
        patch = Patch(
            row_no=3,
            field="belegfeld1",
            operation=PatchOperation.UPPER,
            old_value="test",
            new_value="TEST",
            risk=RiskLevel.LOW,
            rule_id="DVL-FIELD-011",
            rule_version="1.0.0",
        )

        output = preview_patch(patch, colorize=False)

        assert "Row 3" in output
        assert "belegfeld1" in output
        assert "[low]" in output
        assert '"test"' in output
        assert '"TEST"' in output
        assert "DVL-FIELD-011" in output
