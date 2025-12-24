"""
Conflict detection for fix engine.

Detects and resolves conflicts when multiple patches target the same field.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterator

from datev_lint.core.fix.models import Conflict, ConflictResolution, Patch


class ConflictDetector:
    """Detects conflicts between patches."""

    def __init__(self, resolution: ConflictResolution = ConflictResolution.FIRST_WINS):
        self.resolution = resolution

    def detect(self, patches: list[Patch]) -> list[Conflict]:
        """
        Detect conflicts in a list of patches.

        Two patches conflict if they target the same field in the same row.

        Args:
            patches: List of patches to check

        Returns:
            List of detected conflicts
        """
        # Group by (row_no, field)
        by_location: dict[tuple[int, str], list[Patch]] = defaultdict(list)

        for patch in patches:
            key = (patch.row_no, patch.field)
            by_location[key].append(patch)

        # Find conflicts
        conflicts: list[Conflict] = []

        for (row_no, field), patch_list in by_location.items():
            if len(patch_list) > 1:
                # Determine selected patch based on resolution strategy
                if self.resolution == ConflictResolution.FIRST_WINS:
                    selected = patch_list[0]
                elif self.resolution == ConflictResolution.LAST_WINS:
                    selected = patch_list[-1]
                else:
                    selected = None  # Manual resolution

                conflict = Conflict(
                    row_no=row_no,
                    field=field,
                    patches=patch_list,
                    resolution=self.resolution,
                    selected_patch=selected,
                )
                conflicts.append(conflict)

        return conflicts

    def resolve(self, patches: list[Patch], conflicts: list[Conflict]) -> list[Patch]:
        """
        Resolve conflicts by filtering patches.

        Args:
            patches: All patches
            conflicts: Detected conflicts

        Returns:
            Filtered list of patches with conflicts resolved
        """
        # Build set of excluded patches
        excluded: set[int] = set()

        for conflict in conflicts:
            if conflict.selected_patch is None:
                # No resolution - exclude all
                for patch in conflict.patches:
                    excluded.add(id(patch))
            else:
                # Exclude non-selected patches
                for patch in conflict.patches:
                    if patch != conflict.selected_patch:
                        excluded.add(id(patch))

        return [p for p in patches if id(p) not in excluded]


def detect_conflicts(
    patches: list[Patch],
    resolution: ConflictResolution = ConflictResolution.FIRST_WINS,
) -> tuple[list[Patch], list[Conflict]]:
    """
    Detect and resolve conflicts in patches.

    Args:
        patches: List of patches
        resolution: Resolution strategy

    Returns:
        Tuple of (resolved patches, conflicts)
    """
    detector = ConflictDetector(resolution)
    conflicts = detector.detect(patches)
    resolved = detector.resolve(patches, conflicts)
    return resolved, conflicts


def iter_conflict_groups(patches: list[Patch]) -> Iterator[tuple[int, str, list[Patch]]]:
    """
    Iterate over groups of patches that would conflict.

    Yields:
        Tuples of (row_no, field, patches)
    """
    by_location: dict[tuple[int, str], list[Patch]] = defaultdict(list)

    for patch in patches:
        by_location[(patch.row_no, patch.field)].append(patch)

    for (row_no, field), patch_list in by_location.items():
        if len(patch_list) > 1:
            yield row_no, field, patch_list
