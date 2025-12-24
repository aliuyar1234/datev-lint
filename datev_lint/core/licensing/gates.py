"""
Feature gates for license-based access control.

Provides decorators and functions to gate features by license tier.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from datev_lint.core.licensing.loader import get_license
from datev_lint.core.licensing.models import (
    Feature,
    FeatureGateError,
    License,
    LicenseTier,
)

# Minimum tier required for each feature
FEATURE_MIN_TIER: dict[Feature, LicenseTier] = {
    # Free features
    Feature.VALIDATE: LicenseTier.FREE,
    Feature.JSON_OUTPUT: LicenseTier.FREE,
    Feature.FIX_DRY_RUN: LicenseTier.FREE,
    Feature.FINGERPRINT: LicenseTier.FREE,

    # Pro features
    Feature.FIX_APPLY: LicenseTier.PRO,
    Feature.PDF_REPORT: LicenseTier.PRO,
    Feature.HTML_REPORT: LicenseTier.PRO,
    Feature.SARIF_FULL: LicenseTier.PRO,
    Feature.JUNIT_OUTPUT: LicenseTier.PRO,
    Feature.ROLLBACK: LicenseTier.PRO,

    # Team features
    Feature.SHARED_PROFILES: LicenseTier.TEAM,
    Feature.AUDIT_LOG_API: LicenseTier.TEAM,

    # Enterprise features
    Feature.SSO_SAML: LicenseTier.ENTERPRISE,
    Feature.CUSTOM_RULES: LicenseTier.ENTERPRISE,
    Feature.SLA_SUPPORT: LicenseTier.ENTERPRISE,
}


class FeatureGate:
    """
    Feature gate for checking license access.

    Usage:
        gate = FeatureGate()
        if gate.check(Feature.FIX_APPLY):
            # Feature is available
        else:
            # Show upgrade CTA
    """

    def __init__(self, license_obj: License | None = None):
        """
        Initialize gate with license.

        Args:
            license_obj: License to use. Gets current if None.
        """
        self._license = license_obj

    @property
    def license(self) -> License:
        """Get the license object."""
        if self._license is None:
            self._license = get_license()
        return self._license

    def check(self, feature: Feature) -> bool:
        """
        Check if feature is available.

        Args:
            feature: Feature to check

        Returns:
            True if feature is available
        """
        return self.license.has_feature(feature)

    def require(self, feature: Feature) -> None:
        """
        Require a feature, raising if not available.

        Args:
            feature: Required feature

        Raises:
            FeatureGateError: If feature is not available
        """
        if not self.check(feature):
            min_tier = FEATURE_MIN_TIER.get(feature, LicenseTier.PRO)
            raise FeatureGateError(feature, min_tier)

    def get_upgrade_message(self, feature: Feature) -> str:
        """
        Get upgrade message for a feature.

        Args:
            feature: Feature that requires upgrade

        Returns:
            User-friendly upgrade message
        """
        min_tier = FEATURE_MIN_TIER.get(feature, LicenseTier.PRO)

        messages = {
            Feature.FIX_APPLY: "Fix apply requires a Pro license to write corrected files.",
            Feature.PDF_REPORT: "PDF reports require a Pro license.",
            Feature.HTML_REPORT: "HTML reports require a Pro license.",
            Feature.ROLLBACK: "Rollback requires a Pro license.",
            Feature.SHARED_PROFILES: "Shared profiles require a Team license.",
            Feature.AUDIT_LOG_API: "Audit log API requires a Team license.",
            Feature.SSO_SAML: "SSO/SAML requires an Enterprise license.",
            Feature.CUSTOM_RULES: "Custom rules require an Enterprise license.",
        }

        base_msg = messages.get(feature, f"This feature requires a {min_tier.value} license.")
        return f"{base_msg}\n\nUpgrade at: https://datev-lint.dev/pricing"


# Type variable for decorator
F = TypeVar("F", bound=Callable[..., Any])


def require_feature(feature: Feature) -> Callable[[F], F]:
    """
    Decorator to require a feature for a function.

    Usage:
        @require_feature(Feature.FIX_APPLY)
        def apply_fixes(...):
            ...

    Raises:
        FeatureGateError: If feature is not available
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            gate = FeatureGate()
            gate.require(feature)
            return func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator


def check_feature(feature: Feature, license_obj: License | None = None) -> bool:
    """
    Check if a feature is available.

    Args:
        feature: Feature to check
        license_obj: License to check against (uses current if None)

    Returns:
        True if feature is available
    """
    gate = FeatureGate(license_obj)
    return gate.check(feature)


def require_feature_or_raise(feature: Feature, license_obj: License | None = None) -> None:
    """
    Require a feature or raise FeatureGateError.

    Args:
        feature: Required feature
        license_obj: License to check against

    Raises:
        FeatureGateError: If feature is not available
    """
    gate = FeatureGate(license_obj)
    gate.require(feature)


def get_upgrade_cta(feature: Feature) -> str:
    """
    Get upgrade call-to-action for a feature.

    Args:
        feature: Feature requiring upgrade

    Returns:
        CTA message string
    """
    gate = FeatureGate()
    return gate.get_upgrade_message(feature)
