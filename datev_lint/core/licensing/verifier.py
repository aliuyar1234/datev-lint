"""
License verification using Ed25519 signatures.

Provides offline verification of license files.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from datev_lint.core.licensing.models import License, LicenseTier

# Try to import cryptography, fall back gracefully
try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class VerificationError(Exception):
    """Raised when license verification fails."""

    pass


class LicenseVerifier:
    """Verifies Ed25519 signatures on license files."""

    def __init__(self, public_key_path: Path | None = None):
        """
        Initialize verifier with public key.

        Args:
            public_key_path: Path to PEM public key file.
                            If None, uses bundled key.
        """
        self._public_key: Ed25519PublicKey | None = None
        self._key_error: str | None = None

        if not HAS_CRYPTO:
            self._key_error = "cryptography is not installed; cannot verify license signatures"
            return

        if public_key_path is None:
            env_key_path = os.environ.get("DATEV_LINT_PUBLIC_KEY_PATH")
            public_key_path = Path(env_key_path) if env_key_path else None

        if public_key_path is None:
            public_key_path = Path(__file__).resolve().parents[2] / "keys" / "public_key.pem"

        if not public_key_path.exists():
            self._key_error = f"Public key not found: {public_key_path}"
            return

        self._load_public_key(public_key_path)

    def _load_public_key(self, path: Path) -> None:
        """Load public key from PEM file."""
        if not HAS_CRYPTO:
            return

        try:
            key_data = path.read_bytes()
            key = load_pem_public_key(key_data)
            if not isinstance(key, Ed25519PublicKey):
                raise VerificationError("Public key is not an Ed25519 key")
            self._public_key = key
        except Exception as e:
            raise VerificationError(f"Failed to load public key: {e}") from e

    def verify(self, license_data: dict[str, Any]) -> License:
        """
        Verify license signature and return License object.

        Args:
            license_data: License data dict with 'signature' field

        Returns:
            Verified License object

        Raises:
            VerificationError: If signature is invalid
        """
        if not HAS_CRYPTO:
            raise VerificationError(
                "cryptography is required to verify license signatures; "
                "install datev-lint with the 'pro' extra"
            )
        if self._public_key is None:
            raise VerificationError(self._key_error or "Public key not loaded")

        # Extract signature
        signature_b64 = license_data.get("signature", "")
        if not signature_b64:
            raise VerificationError("License has no signature")

        # Create data to verify (everything except signature)
        verify_data = {k: v for k, v in license_data.items() if k != "signature"}
        message = json.dumps(verify_data, sort_keys=True, separators=(",", ":")).encode("utf-8")

        # Verify signature
        try:
            signature = base64.b64decode(signature_b64)
            self._public_key.verify(signature, message)
        except InvalidSignature:
            raise VerificationError("Invalid license signature") from None
        except Exception as e:
            raise VerificationError(f"Signature verification failed: {e}") from e

        # Parse license
        try:
            # Handle tier enum
            tier_str = license_data.get("tier", "free")
            tier = LicenseTier(tier_str)

            return License(
                license_id=license_data.get("license_id", "unknown"),
                tier=tier,
                org_id=license_data.get("org_id"),
                org_name=license_data.get("org_name"),
                seats=license_data.get("seats", 1),
                features=license_data.get("features", []),
                issued_at=license_data.get("issued_at"),  # type: ignore[arg-type]  # pydantic parses
                expires_at=license_data.get("expires_at"),
                signature=signature_b64,
            )
        except Exception as e:
            raise VerificationError(f"Invalid license format: {e}") from e

    def verify_file(self, license_path: Path) -> License:
        """
        Verify license from file.

        Args:
            license_path: Path to license JSON file

        Returns:
            Verified License object

        Raises:
            VerificationError: If file is invalid or signature fails
        """
        try:
            data = json.loads(license_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise VerificationError(f"Invalid license JSON: {e}") from e
        except Exception as e:
            raise VerificationError(f"Failed to read license file: {e}") from e

        return self.verify(data)


def verify_license(license_data: dict[str, Any] | Path) -> License:
    """
    Convenience function to verify a license.

    Args:
        license_data: License dict or path to license file

    Returns:
        Verified License object

    Raises:
        VerificationError: If verification fails
    """
    verifier = LicenseVerifier()

    if isinstance(license_data, Path):
        return verifier.verify_file(license_data)
    else:
        return verifier.verify(license_data)
