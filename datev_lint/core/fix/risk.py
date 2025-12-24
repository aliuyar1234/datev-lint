"""
Risk management for fix engine.

Defines risk levels and approval logic.
"""

from __future__ import annotations

from datev_lint.core.fix.models import Patch, PatchOperation, PatchPlan
from datev_lint.core.rules.models import RiskLevel

# Operation risk levels
OPERATION_RISK: dict[PatchOperation, RiskLevel] = {
    PatchOperation.UPPER: RiskLevel.LOW,
    PatchOperation.NORMALIZE_DECIMAL: RiskLevel.LOW,
    PatchOperation.SET_FIELD: RiskLevel.MEDIUM,
    PatchOperation.TRUNCATE: RiskLevel.MEDIUM,
    PatchOperation.SANITIZE_CHARS: RiskLevel.MEDIUM,
    PatchOperation.DELETE_ROW: RiskLevel.HIGH,
    PatchOperation.SPLIT_FILE: RiskLevel.MEDIUM,
}


def get_operation_risk(operation: PatchOperation) -> RiskLevel:
    """Get risk level for an operation."""
    return OPERATION_RISK.get(operation, RiskLevel.MEDIUM)


def should_apply(patch: Patch, accept_risk: RiskLevel) -> bool:
    """
    Check if a patch should be applied based on accepted risk level.

    Args:
        patch: Patch to check
        accept_risk: Maximum risk level to accept

    Returns:
        True if patch should be applied
    """
    risk_order = {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1,
        RiskLevel.HIGH: 2,
    }

    patch_level = risk_order.get(patch.risk, 1)
    accept_level = risk_order.get(accept_risk, 1)

    # If patch requires approval, always return False unless explicitly accepted
    if patch.requires_approval and accept_risk != RiskLevel.HIGH:
        return False

    return patch_level <= accept_level


def filter_by_risk(plan: PatchPlan, accept_risk: RiskLevel) -> list[Patch]:
    """
    Filter patches by acceptable risk level.

    Args:
        plan: Patch plan
        accept_risk: Maximum risk level to accept

    Returns:
        List of patches that can be applied
    """
    return [p for p in plan.patches if should_apply(p, accept_risk)]


def requires_interactive_approval(plan: PatchPlan) -> bool:
    """
    Check if any patches require interactive approval.

    Args:
        plan: Patch plan to check

    Returns:
        True if interactive approval is needed
    """
    return any(p.requires_approval for p in plan.patches)


def get_risk_summary(plan: PatchPlan) -> dict[str, int]:
    """
    Get summary of patches by risk level.

    Args:
        plan: Patch plan

    Returns:
        Dictionary with counts by risk level
    """
    return {
        "low": plan.low_risk_count,
        "medium": plan.medium_risk_count,
        "high": plan.high_risk_count,
        "requires_approval": sum(1 for p in plan.patches if p.requires_approval),
    }


def format_risk_warning(plan: PatchPlan) -> str:
    """
    Format a risk warning message for display.

    Args:
        plan: Patch plan

    Returns:
        Warning message
    """
    summary = get_risk_summary(plan)

    parts = []
    if summary["high"] > 0:
        parts.append(f"{summary['high']} HIGH risk")
    if summary["medium"] > 0:
        parts.append(f"{summary['medium']} MEDIUM risk")
    if summary["low"] > 0:
        parts.append(f"{summary['low']} LOW risk")

    if not parts:
        return "No patches to apply."

    msg = f"Patches: {', '.join(parts)}"

    if summary["requires_approval"] > 0:
        msg += f"\n⚠ {summary['requires_approval']} patch(es) require explicit approval"

    return msg
