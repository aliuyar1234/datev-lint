"""
Licensing models.

Core models for license tiers, features, and verification.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class LicenseTier(Enum):
    """License tier levels."""

    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class Feature(Enum):
    """Gated features."""

    # Free features (for documentation, always available)
    VALIDATE = "validate"
    JSON_OUTPUT = "json_output"
    FIX_DRY_RUN = "fix_dry_run"
    FINGERPRINT = "fingerprint"

    # Pro features
    FIX_APPLY = "fix_apply"
    PDF_REPORT = "pdf_report"
    HTML_REPORT = "html_report"
    SARIF_FULL = "sarif_full"
    JUNIT_OUTPUT = "junit_output"
    ROLLBACK = "rollback"

    # Team features
    SHARED_PROFILES = "shared_profiles"
    AUDIT_LOG_API = "audit_log_api"

    # Enterprise features
    SSO_SAML = "sso_saml"
    CUSTOM_RULES = "custom_rules"
    SLA_SUPPORT = "sla_support"


class ExpiryStatus(Enum):
    """License expiry status."""

    VALID = "valid"
    WARNING = "warning"  # Expires within 14 days
    EXPIRED = "expired"
    INVALID = "invalid"


# Feature to tier mapping
TIER_FEATURES: dict[LicenseTier, set[Feature]] = {
    LicenseTier.FREE: {
        Feature.VALIDATE,
        Feature.JSON_OUTPUT,
        Feature.FIX_DRY_RUN,
        Feature.FINGERPRINT,
    },
    LicenseTier.PRO: {
        Feature.VALIDATE,
        Feature.JSON_OUTPUT,
        Feature.FIX_DRY_RUN,
        Feature.FINGERPRINT,
        Feature.FIX_APPLY,
        Feature.PDF_REPORT,
        Feature.HTML_REPORT,
        Feature.SARIF_FULL,
        Feature.JUNIT_OUTPUT,
        Feature.ROLLBACK,
    },
    LicenseTier.TEAM: {
        Feature.VALIDATE,
        Feature.JSON_OUTPUT,
        Feature.FIX_DRY_RUN,
        Feature.FINGERPRINT,
        Feature.FIX_APPLY,
        Feature.PDF_REPORT,
        Feature.HTML_REPORT,
        Feature.SARIF_FULL,
        Feature.JUNIT_OUTPUT,
        Feature.ROLLBACK,
        Feature.SHARED_PROFILES,
        Feature.AUDIT_LOG_API,
    },
    LicenseTier.ENTERPRISE: set(Feature),  # All features
}


class License(BaseModel):
    """License information."""

    license_id: str = Field(description="Unique license ID")
    tier: LicenseTier = Field(default=LicenseTier.FREE)
    org_id: str | None = Field(default=None, description="Organization ID")
    org_name: str | None = Field(default=None, description="Organization name")
    seats: int = Field(default=1, ge=1, description="Number of seats")
    features: list[str] = Field(default_factory=list, description="Explicit feature list")
    issued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = Field(default=None, description="Expiry date (None = perpetual)")
    signature: str = Field(default="", description="Base64 Ed25519 signature")

    model_config = {"frozen": True}

    @property
    def is_expired(self) -> bool:
        """Check if license is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) >= self.expires_at

    @property
    def days_until_expiry(self) -> int | None:
        """Calendar days until expiry, or None if perpetual."""
        if self.expires_at is None:
            return None
        now = datetime.now(UTC)
        if now >= self.expires_at:
            return 0
        delta_days = (self.expires_at.date() - now.date()).days
        return max(0, delta_days)

    @property
    def expiry_status(self) -> ExpiryStatus:
        """Get expiry status."""
        if self.expires_at is None:
            return ExpiryStatus.VALID

        now = datetime.now(UTC)
        if now >= self.expires_at:
            return ExpiryStatus.EXPIRED

        days = self.days_until_expiry
        if days is None:
            return ExpiryStatus.VALID
        if days <= 14:
            return ExpiryStatus.WARNING
        return ExpiryStatus.VALID

    def has_feature(self, feature: Feature) -> bool:
        """Check if license grants access to a feature."""
        # Check explicit feature list first
        if feature.value in self.features:
            return True

        # Check tier features
        tier_features = TIER_FEATURES.get(self.tier, set())
        return feature in tier_features

    def get_available_features(self) -> set[Feature]:
        """Get all available features for this license."""
        features = TIER_FEATURES.get(self.tier, set()).copy()

        # Add explicit features
        for f_name in self.features:
            with contextlib.suppress(ValueError):
                features.add(Feature(f_name))

        return features


class FeatureGateError(Exception):
    """Raised when a feature is not available for the current license."""

    def __init__(
        self,
        feature: Feature,
        required_tier: LicenseTier = LicenseTier.PRO,
        message: str | None = None,
    ):
        self.feature = feature
        self.required_tier = required_tier

        if message is None:
            message = (
                f"Feature '{feature.value}' requires {required_tier.value} license. "
                f"Upgrade at https://datev-lint.dev/pricing"
            )

        super().__init__(message)


# Default free license (no file needed)
FREE_LICENSE = License(
    license_id="free",
    tier=LicenseTier.FREE,
    org_name="Free User",
    seats=1,
)
