"""
License verification using Ed25519 signatures.

Provides offline verification of license files.
"""

from __future__ import annotations

import base64
import json
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
        self._public_key: Any = None

        if not HAS_CRYPTO:
            return

        if public_key_path is None:
            # Use bundled public key
            public_key_path = Path(__file__).parent.parent.parent / "keys" / "public_key.pem"

        if public_key_path.exists():
            self._load_public_key(public_key_path)

    def _load_public_key(self, path: Path) -> None:
        """Load public key from PEM file."""
        if not HAS_CRYPTO:
            return

        try:
            key_data = path.read_bytes()
            self._public_key = load_pem_public_key(key_data)
        except Exception as e:
            raise VerificationError(f"Failed to load public key: {e}")

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
        # Extract signature
        signature_b64 = license_data.get("signature", "")
        if not signature_b64:
            raise VerificationError("License has no signature")

        # Create data to verify (everything except signature)
        verify_data = {k: v for k, v in license_data.items() if k != "signature"}
        message = json.dumps(verify_data, sort_keys=True, separators=(",", ":")).encode("utf-8")

        # Verify signature if crypto is available
        if HAS_CRYPTO and self._public_key is not None:
            try:
                signature = base64.b64decode(signature_b64)
                self._public_key.verify(signature, message)
            except InvalidSignature:
                raise VerificationError("Invalid license signature")
            except Exception as e:
                raise VerificationError(f"Signature verification failed: {e}")

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
            raise VerificationError(f"Invalid license format: {e}")

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
            raise VerificationError(f"Invalid license JSON: {e}")
        except Exception as e:
            raise VerificationError(f"Failed to read license file: {e}")

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
