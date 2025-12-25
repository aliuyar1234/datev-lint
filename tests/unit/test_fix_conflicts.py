"""Tests for conflict detection."""

from datev_lint.core.fix.conflicts import (
    ConflictDetector,
    detect_conflicts,
    iter_conflict_groups,
)
from datev_lint.core.fix.models import ConflictResolution, Patch, PatchOperation
from datev_lint.core.rules.models import RiskLevel


def make_patch(
    row_no: int = 3,
    field: str = "belegfeld1",
    operation: PatchOperation = PatchOperation.UPPER,
    old_value: str = "test",
    new_value: str = "TEST",
) -> Patch:
    """Helper to create patches."""
    return Patch(
        row_no=row_no,
        field=field,
        operation=operation,
        old_value=old_value,
        new_value=new_value,
        risk=RiskLevel.LOW,
        rule_id="DVL-TEST-001",
        rule_version="1.0.0",
    )


class TestConflictDetector:
    """Tests for ConflictDetector."""

    def test_no_conflicts(self) -> None:
        """Test with no conflicts."""
        patches = [
            make_patch(row_no=3, field="belegfeld1"),
            make_patch(row_no=4, field="belegfeld1"),
            make_patch(row_no=3, field="buchungstext"),
        ]

        detector = ConflictDetector()
        conflicts = detector.detect(patches)

        assert len(conflicts) == 0

    def test_detect_conflict(self) -> None:
        """Test detecting a conflict."""
        patches = [
            make_patch(row_no=3, field="belegfeld1", operation=PatchOperation.UPPER),
            make_patch(row_no=3, field="belegfeld1", operation=PatchOperation.TRUNCATE),
        ]

        detector = ConflictDetector()
        conflicts = detector.detect(patches)

        assert len(conflicts) == 1
        assert conflicts[0].row_no == 3
        assert conflicts[0].field == "belegfeld1"
        assert len(conflicts[0].patches) == 2

    def test_first_wins_resolution(self) -> None:
        """Test first-wins resolution."""
        patches = [
            make_patch(row_no=3, operation=PatchOperation.UPPER),
            make_patch(row_no=3, operation=PatchOperation.TRUNCATE),
        ]

        detector = ConflictDetector(resolution=ConflictResolution.FIRST_WINS)
        conflicts = detector.detect(patches)
        resolved = detector.resolve(patches, conflicts)

        assert len(resolved) == 1
        assert resolved[0].operation == PatchOperation.UPPER

    def test_last_wins_resolution(self) -> None:
        """Test last-wins resolution."""
        patches = [
            make_patch(row_no=3, operation=PatchOperation.UPPER),
            make_patch(row_no=3, operation=PatchOperation.TRUNCATE),
        ]

        detector = ConflictDetector(resolution=ConflictResolution.LAST_WINS)
        conflicts = detector.detect(patches)
        resolved = detector.resolve(patches, conflicts)

        assert len(resolved) == 1
        assert resolved[0].operation == PatchOperation.TRUNCATE


class TestDetectConflictsFunction:
    """Tests for detect_conflicts convenience function."""

    def test_detect_and_resolve(self) -> None:
        """Test combined detection and resolution."""
        patches = [
            make_patch(row_no=3, operation=PatchOperation.UPPER),
            make_patch(row_no=3, operation=PatchOperation.TRUNCATE),
            make_patch(row_no=4, field="buchungstext"),
        ]

        resolved, conflicts = detect_conflicts(patches)

        assert len(resolved) == 2
        assert len(conflicts) == 1


class TestIterConflictGroups:
    """Tests for iter_conflict_groups."""

    def test_iterate_groups(self) -> None:
        """Test iterating over conflict groups."""
        patches = [
            make_patch(row_no=3, field="belegfeld1"),
            make_patch(row_no=3, field="belegfeld1"),
            make_patch(row_no=4, field="belegfeld1"),
        ]

        groups = list(iter_conflict_groups(patches))

        assert len(groups) == 1
        row_no, field, patch_list = groups[0]
        assert row_no == 3
        assert field == "belegfeld1"
        assert len(patch_list) == 2
