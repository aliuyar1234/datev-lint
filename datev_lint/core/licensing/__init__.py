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
    FREE_LICENSE,
    TIER_FEATURES,
    ExpiryStatus,
    Feature,
    FeatureGateError,
    License,
    LicenseTier,
)
from datev_lint.core.licensing.verifier import (
    LicenseVerifier,
    VerificationError,
    verify_license,
)

__all__ = [
    "FREE_LICENSE",
    "TIER_FEATURES",
    "ExpiryStatus",
    "Feature",
    # Gates
    "FeatureGate",
    "FeatureGateError",
    # Models
    "License",
    "LicenseTier",
    # Verification
    "LicenseVerifier",
    "VerificationError",
    "check_feature",
    "find_license_file",
    "get_effective_license",
    "get_effective_tier",
    # Expiry
    "get_expiry_status",
    "get_expiry_warning",
    # Loading
    "get_license",
    "get_license_search_paths",
    "get_upgrade_cta",
    "has_feature_with_expiry_check",
    "require_feature",
    "require_feature_or_raise",
    "reset_license_cache",
    "verify_license",
]
