"""
Patch planner for fix engine.

Generates PatchPlan from validation findings with fix candidates.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from datev_lint.core.fix.models import (
    Conflict,
    ConflictResolution,
    Patch,
    PatchOperation,
    PatchPlan,
)
from datev_lint.core.rules.models import Finding, RiskLevel

if TYPE_CHECKING:
    from datev_lint.core.rules.pipeline import PipelineResult


def compute_file_checksum(file_path: str | Path) -> str:
    """Compute SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_bytes_checksum(data: bytes) -> str:
    """Compute SHA-256 checksum of bytes."""
    return hashlib.sha256(data).hexdigest()


class PatchPlanner:
    """Generates patch plans from findings."""

    def __init__(self, resolution: ConflictResolution = ConflictResolution.FIRST_WINS):
        self.resolution = resolution

    def plan(
        self,
        file_path: str | Path,
        findings: list[Finding],
        file_checksum: str | None = None,
    ) -> PatchPlan:
        """
        Generate a patch plan from findings.

        Args:
            file_path: Path to the file being fixed
            findings: Validation findings with fix candidates
            file_checksum: Optional pre-computed checksum

        Returns:
            PatchPlan with patches and detected conflicts
        """
        file_path = Path(file_path)

        # Compute checksum if not provided
        if file_checksum is None:
            file_checksum = compute_file_checksum(file_path)

        # Extract patches from fix candidates
        patches: list[Patch] = []
        for finding in findings:
            for candidate in finding.fix_candidates:
                try:
                    operation = PatchOperation(candidate.operation)
                except ValueError:
                    # Skip unknown operations
                    continue

                if finding.location.row_no is None:
                    # Skip findings without row location
                    continue

                patch = Patch(
                    row_no=finding.location.row_no,
                    field=candidate.field,
                    operation=operation,
                    old_value=candidate.old_value,
                    new_value=candidate.new_value,
                    risk=candidate.risk,
                    requires_approval=candidate.requires_approval,
                    rule_id=finding.code,
                    rule_version=finding.rule_version,
                )
                patches.append(patch)

        # Sort patches by row, then field
        patches.sort(key=lambda p: (p.row_no, p.field))

        # Detect conflicts
        conflicts = self._detect_conflicts(patches)

        # Filter patches based on conflict resolution
        resolved_patches = self._resolve_conflicts(patches, conflicts)

        # Count by risk level
        low_count = sum(1 for p in resolved_patches if p.risk == RiskLevel.LOW)
        medium_count = sum(1 for p in resolved_patches if p.risk == RiskLevel.MEDIUM)
        high_count = sum(1 for p in resolved_patches if p.risk == RiskLevel.HIGH)

        # Check if approval required
        requires_approval = any(p.requires_approval for p in resolved_patches)

        return PatchPlan(
            file_path=str(file_path),
            file_checksum=file_checksum,
            patches=resolved_patches,
            conflicts=conflicts,
            low_risk_count=low_count,
            medium_risk_count=medium_count,
            high_risk_count=high_count,
            requires_approval=requires_approval,
        )

    def _detect_conflicts(self, patches: list[Patch]) -> list[Conflict]:
        """Detect patches that modify the same field in the same row."""
        # Group patches by (row_no, field)
        by_location: dict[tuple[int, str], list[Patch]] = defaultdict(list)
        for patch in patches:
            by_location[(patch.row_no, patch.field)].append(patch)

        # Find conflicts (multiple patches for same field)
        conflicts: list[Conflict] = []
        for (row_no, field), patch_list in by_location.items():
            if len(patch_list) > 1:
                # Select based on resolution strategy
                selected = patch_list[0] if self.resolution == ConflictResolution.FIRST_WINS else patch_list[-1]

                conflict = Conflict(
                    row_no=row_no,
                    field=field,
                    patches=patch_list,
                    resolution=self.resolution,
                    selected_patch=selected,
                )
                conflicts.append(conflict)

        return conflicts

    def _resolve_conflicts(
        self,
        patches: list[Patch],
        conflicts: list[Conflict],
    ) -> list[Patch]:
        """Filter patches based on conflict resolution."""
        # Build set of patches to exclude due to conflicts
        excluded: set[Patch] = set()

        for conflict in conflicts:
            for patch in conflict.patches:
                if patch != conflict.selected_patch:
                    excluded.add(patch)

        return [p for p in patches if p not in excluded]


def plan_fixes(
    file_path: str | Path,
    result: PipelineResult,
    resolution: ConflictResolution = ConflictResolution.FIRST_WINS,
) -> PatchPlan:
    """
    Convenience function to create a patch plan from pipeline result.

    Args:
        file_path: Path to the file being fixed
        result: Pipeline validation result
        resolution: How to resolve conflicts

    Returns:
        PatchPlan with patches and conflicts
    """
    planner = PatchPlanner(resolution=resolution)
    return planner.plan(file_path, result.findings)
