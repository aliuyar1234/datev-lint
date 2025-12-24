"""
Licensing module for DATEV Lint.

Provides license verification, feature gates, and tier management.
"""

from datev_lint.core.licensing.expiry import (
    get_effective_license,
    get_effective_tier,
    get_expiry_status,
    get_expiry_warning,
    has_feature_with_expiry_check,
)
from datev_lint.core.licensing.gates import (
    FeatureGate,
    check_feature,
    get_upgrade_cta,
    require_feature,
    require_feature_or_raise,
)
from datev_lint.core.licensing.loader import (
    find_license_file,
    get_license,
    get_license_search_paths,
    reset_license_cache,
)
from datev_lint.core.licensing.models import (
    ExpiryStatus,
    Feature,
    FeatureGateError,
    License,
    LicenseTier,
    FREE_LICENSE,
    TIER_FEATURES,
)
from datev_lint.core.licensing.verifier import (
    LicenseVerifier,
    VerificationError,
    verify_license,
)


__all__ = [
    # Models
    "License",
    "LicenseTier",
    "Feature",
    "ExpiryStatus",
    "FeatureGateError",
    "FREE_LICENSE",
    "TIER_FEATURES",
    # Verification
    "LicenseVerifier",
    "VerificationError",
    "verify_license",
    # Loading
    "get_license",
    "find_license_file",
    "get_license_search_paths",
    "reset_license_cache",
    # Gates
    "FeatureGate",
    "check_feature",
    "require_feature",
    "require_feature_or_raise",
    "get_upgrade_cta",
    # Expiry
    "get_expiry_status",
    "get_expiry_warning",
    "get_effective_license",
    "get_effective_tier",
    "has_feature_with_expiry_check",
]
