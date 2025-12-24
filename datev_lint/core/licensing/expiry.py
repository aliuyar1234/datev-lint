"""
License expiry handling.

Provides warnings and graceful fallback for expiring/expired licenses.
"""

from __future__ import annotations

from datev_lint.core.licensing.models import (
    FREE_LICENSE,
    ExpiryStatus,
    Feature,
    License,
    LicenseTier,
)

# Warning threshold in days
EXPIRY_WARNING_DAYS = 14


def get_expiry_status(license_obj: License) -> ExpiryStatus:
    """
    Get the expiry status of a license.

    Args:
        license_obj: License to check

    Returns:
        ExpiryStatus enum value
    """
    return license_obj.expiry_status


def get_expiry_warning(license_obj: License) -> str | None:
    """
    Get expiry warning message if applicable.

    Args:
        license_obj: License to check

    Returns:
        Warning message or None if not expiring soon
    """
    status = license_obj.expiry_status

    if status == ExpiryStatus.WARNING:
        days = license_obj.days_until_expiry
        if days is not None:
            if days == 0:
                return "Your license expires today! Renew now to avoid interruption."
            elif days == 1:
                return "Your license expires tomorrow! Renew at https://datev-lint.dev/renew"
            else:
                return f"Your license expires in {days} days. Renew at https://datev-lint.dev/renew"

    elif status == ExpiryStatus.EXPIRED:
        return (
            "Your license has expired. Pro features are disabled.\n"
            "Renew at https://datev-lint.dev/renew"
        )

    return None


def get_effective_license(license_obj: License) -> License:
    """
    Get effective license considering expiry.

    If license is expired, returns a FREE license.

    Args:
        license_obj: Original license

    Returns:
        Effective license (may be FREE if expired)
    """
    if license_obj.expiry_status == ExpiryStatus.EXPIRED:
        return FREE_LICENSE
    return license_obj


def get_effective_tier(license_obj: License) -> LicenseTier:
    """
    Get effective tier considering expiry.

    Args:
        license_obj: License to check

    Returns:
        Effective tier (FREE if expired)
    """
    effective = get_effective_license(license_obj)
    return effective.tier


def has_feature_with_expiry_check(license_obj: License, feature: Feature) -> bool:
    """
    Check if feature is available considering expiry.

    Args:
        license_obj: License to check
        feature: Feature to check

    Returns:
        True if feature is available
    """
    effective = get_effective_license(license_obj)
    return effective.has_feature(feature)


def format_expiry_date(license_obj: License) -> str:
    """
    Format expiry date for display.

    Args:
        license_obj: License to format

    Returns:
        Formatted expiry string
    """
    if license_obj.expires_at is None:
        return "Never (perpetual license)"

    return license_obj.expires_at.strftime("%Y-%m-%d")
