"""Tests for licensing module."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from datev_lint.core.licensing import (
    ExpiryStatus,
    Feature,
    FeatureGate,
    FeatureGateError,
    License,
    LicenseTier,
    FREE_LICENSE,
    check_feature,
    get_effective_license,
    get_expiry_warning,
    require_feature,
)


class TestLicenseTier:
    """Tests for LicenseTier enum."""

    def test_tier_values(self) -> None:
        """Test tier values."""
        assert LicenseTier.FREE.value == "free"
        assert LicenseTier.PRO.value == "pro"
        assert LicenseTier.TEAM.value == "team"
        assert LicenseTier.ENTERPRISE.value == "enterprise"


class TestFeature:
    """Tests for Feature enum."""

    def test_free_features(self) -> None:
        """Test free feature values."""
        assert Feature.VALIDATE.value == "validate"
        assert Feature.JSON_OUTPUT.value == "json_output"
        assert Feature.FIX_DRY_RUN.value == "fix_dry_run"

    def test_pro_features(self) -> None:
        """Test pro feature values."""
        assert Feature.FIX_APPLY.value == "fix_apply"
        assert Feature.PDF_REPORT.value == "pdf_report"


class TestLicense:
    """Tests for License model."""

    def test_free_license(self) -> None:
        """Test FREE_LICENSE constant."""
        assert FREE_LICENSE.tier == LicenseTier.FREE
        assert FREE_LICENSE.license_id == "free"
        assert FREE_LICENSE.seats == 1

    def test_license_has_feature_by_tier(self) -> None:
        """Test feature access by tier."""
        license_obj = License(
            license_id="test",
            tier=LicenseTier.PRO,
        )

        # Free features should be available
        assert license_obj.has_feature(Feature.VALIDATE)
        assert license_obj.has_feature(Feature.JSON_OUTPUT)

        # Pro features should be available
        assert license_obj.has_feature(Feature.FIX_APPLY)
        assert license_obj.has_feature(Feature.PDF_REPORT)

        # Team features should NOT be available
        assert not license_obj.has_feature(Feature.SHARED_PROFILES)

    def test_license_has_feature_explicit(self) -> None:
        """Test explicit feature grants."""
        license_obj = License(
            license_id="test",
            tier=LicenseTier.FREE,
            features=["fix_apply"],  # Explicit grant
        )

        # Free features
        assert license_obj.has_feature(Feature.VALIDATE)

        # Explicitly granted
        assert license_obj.has_feature(Feature.FIX_APPLY)

        # Not granted
        assert not license_obj.has_feature(Feature.PDF_REPORT)

    def test_license_not_expired(self) -> None:
        """Test non-expired license."""
        license_obj = License(
            license_id="test",
            tier=LicenseTier.PRO,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

        assert not license_obj.is_expired
        assert license_obj.expiry_status == ExpiryStatus.VALID

    def test_license_expired(self) -> None:
        """Test expired license."""
        license_obj = License(
            license_id="test",
            tier=LicenseTier.PRO,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )

        assert license_obj.is_expired
        assert license_obj.expiry_status == ExpiryStatus.EXPIRED

    def test_license_warning_period(self) -> None:
        """Test license in warning period."""
        license_obj = License(
            license_id="test",
            tier=LicenseTier.PRO,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

        assert not license_obj.is_expired
        assert license_obj.expiry_status == ExpiryStatus.WARNING
        assert license_obj.days_until_expiry == 7

    def test_license_perpetual(self) -> None:
        """Test perpetual license (no expiry)."""
        license_obj = License(
            license_id="test",
            tier=LicenseTier.PRO,
            expires_at=None,
        )

        assert not license_obj.is_expired
        assert license_obj.expiry_status == ExpiryStatus.VALID
        assert license_obj.days_until_expiry is None


class TestFeatureGate:
    """Tests for FeatureGate."""

    def test_gate_check_free_feature(self) -> None:
        """Test checking a free feature."""
        license_obj = License(license_id="test", tier=LicenseTier.FREE)
        gate = FeatureGate(license_obj)

        assert gate.check(Feature.VALIDATE)
        assert gate.check(Feature.JSON_OUTPUT)

    def test_gate_check_pro_feature_without_license(self) -> None:
        """Test checking pro feature with free license."""
        gate = FeatureGate(FREE_LICENSE)

        assert not gate.check(Feature.FIX_APPLY)
        assert not gate.check(Feature.PDF_REPORT)

    def test_gate_check_pro_feature_with_license(self) -> None:
        """Test checking pro feature with pro license."""
        license_obj = License(license_id="test", tier=LicenseTier.PRO)
        gate = FeatureGate(license_obj)

        assert gate.check(Feature.FIX_APPLY)
        assert gate.check(Feature.PDF_REPORT)

    def test_gate_require_raises(self) -> None:
        """Test require raises for missing feature."""
        gate = FeatureGate(FREE_LICENSE)

        with pytest.raises(FeatureGateError) as exc_info:
            gate.require(Feature.FIX_APPLY)

        assert exc_info.value.feature == Feature.FIX_APPLY
        assert "pro" in str(exc_info.value).lower()

    def test_gate_require_passes(self) -> None:
        """Test require passes for available feature."""
        license_obj = License(license_id="test", tier=LicenseTier.PRO)
        gate = FeatureGate(license_obj)

        # Should not raise
        gate.require(Feature.FIX_APPLY)


class TestCheckFeature:
    """Tests for check_feature function."""

    def test_check_free_feature(self) -> None:
        """Test checking free feature."""
        assert check_feature(Feature.VALIDATE, FREE_LICENSE)

    def test_check_pro_feature_without_license(self) -> None:
        """Test checking pro feature without license."""
        assert not check_feature(Feature.FIX_APPLY, FREE_LICENSE)


class TestRequireFeatureDecorator:
    """Tests for require_feature decorator."""

    def test_decorator_blocks_without_license(self) -> None:
        """Test decorator blocks without proper license."""
        from datev_lint.core.licensing.loader import reset_license_cache

        reset_license_cache()

        @require_feature(Feature.FIX_APPLY)
        def pro_function() -> str:
            return "success"

        # Should raise without Pro license
        with pytest.raises(FeatureGateError):
            pro_function()


class TestExpiryHandling:
    """Tests for expiry handling."""

    def test_get_effective_license_valid(self) -> None:
        """Test effective license when valid."""
        license_obj = License(
            license_id="test",
            tier=LicenseTier.PRO,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

        effective = get_effective_license(license_obj)
        assert effective.tier == LicenseTier.PRO

    def test_get_effective_license_expired(self) -> None:
        """Test effective license when expired."""
        license_obj = License(
            license_id="test",
            tier=LicenseTier.PRO,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )

        effective = get_effective_license(license_obj)
        assert effective.tier == LicenseTier.FREE

    def test_expiry_warning_message(self) -> None:
        """Test expiry warning message."""
        license_obj = License(
            license_id="test",
            tier=LicenseTier.PRO,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

        warning = get_expiry_warning(license_obj)
        assert warning is not None
        assert "7 days" in warning

    def test_no_warning_for_valid_license(self) -> None:
        """Test no warning for valid license."""
        license_obj = License(
            license_id="test",
            tier=LicenseTier.PRO,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

        warning = get_expiry_warning(license_obj)
        assert warning is None
