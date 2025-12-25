"""Tests for license signature verification."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from datev_lint.core.licensing import FREE_LICENSE, LicenseTier, VerificationError, get_license
from datev_lint.core.licensing.loader import reset_license_cache
from datev_lint.core.licensing.verifier import LicenseVerifier

if TYPE_CHECKING:
    from pathlib import Path


def _make_test_keypair(public_key_path: Path) -> Ed25519PrivateKey:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_key_path.write_bytes(
        public_key.public_bytes(encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo)
    )
    return private_key


def _sign_license(private_key: Ed25519PrivateKey, license_data: dict[str, object]) -> str:
    verify_data = {k: v for k, v in license_data.items() if k != "signature"}
    message = json.dumps(verify_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(private_key.sign(message)).decode("ascii")


def test_license_verifier_accepts_valid_signature(tmp_path: Path) -> None:
    key_path = tmp_path / "public_key.pem"
    private_key = _make_test_keypair(key_path)

    license_data: dict[str, object] = {
        "license_id": "lic_test_pro_001",
        "tier": "pro",
        "org_id": "org_test",
        "org_name": "Test Organization",
        "seats": 1,
        "features": ["fix_apply", "sarif_full"],
        "issued_at": "2025-01-01T00:00:00Z",
        "expires_at": "2030-01-01T00:00:00Z",
        "signature": "",
    }
    license_data["signature"] = _sign_license(private_key, license_data)

    verifier = LicenseVerifier(public_key_path=key_path)
    license_obj = verifier.verify(license_data)
    assert license_obj.tier == LicenseTier.PRO


def test_license_verifier_rejects_invalid_signature(tmp_path: Path) -> None:
    key_path = tmp_path / "public_key.pem"
    _make_test_keypair(key_path)

    license_data: dict[str, object] = {
        "license_id": "lic_test_pro_001",
        "tier": "pro",
        "org_name": "Test Organization",
        "seats": 1,
        "features": ["fix_apply"],
        "issued_at": "2025-01-01T00:00:00Z",
        "expires_at": "2030-01-01T00:00:00Z",
        "signature": "",
    }

    wrong_key = Ed25519PrivateKey.generate()
    license_data["signature"] = _sign_license(wrong_key, license_data)

    verifier = LicenseVerifier(public_key_path=key_path)
    with pytest.raises(VerificationError):
        verifier.verify(license_data)


def test_get_license_returns_free_on_verification_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key_path = tmp_path / "public_key.pem"
    _make_test_keypair(key_path)

    expires_at = datetime.now(UTC) + timedelta(days=30)
    license_data: dict[str, object] = {
        "license_id": "lic_test_pro_001",
        "tier": "pro",
        "org_name": "Test Organization",
        "seats": 1,
        "features": ["fix_apply"],
        "issued_at": "2025-01-01T00:00:00Z",
        "expires_at": expires_at.isoformat(),
        "signature": "not-a-real-signature",
    }
    license_path = tmp_path / "license.json"
    license_path.write_text(json.dumps(license_data), encoding="utf-8")

    monkeypatch.setenv("DATEV_LINT_PUBLIC_KEY_PATH", str(key_path))
    reset_license_cache()

    loaded = get_license(path=license_path)
    assert loaded == FREE_LICENSE


def test_get_license_verifies_when_key_is_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key_path = tmp_path / "public_key.pem"
    private_key = _make_test_keypair(key_path)

    license_data: dict[str, object] = {
        "license_id": "lic_test_pro_001",
        "tier": "pro",
        "org_name": "Test Organization",
        "seats": 1,
        "features": ["fix_apply"],
        "issued_at": "2025-01-01T00:00:00Z",
        "expires_at": "2030-01-01T00:00:00Z",
        "signature": "",
    }
    license_data["signature"] = _sign_license(private_key, license_data)

    license_path = tmp_path / "license.json"
    license_path.write_text(json.dumps(license_data), encoding="utf-8")

    monkeypatch.setenv("DATEV_LINT_PUBLIC_KEY_PATH", str(key_path))
    reset_license_cache()

    loaded = get_license(path=license_path)
    assert loaded.tier == LicenseTier.PRO
