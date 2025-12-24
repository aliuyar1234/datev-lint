# Data Model: Licensing & Monetization

**Feature**: 005-licensing
**Date**: 2025-12-24

## Entity Overview

```
┌─────────────────┐     ┌─────────────────┐
│  LicenseLoader  │────▶│  License        │
└─────────────────┘     └────────┬────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ LicenseVerifier │     │  FeatureGate    │     │ TelemetryClient │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Core Entities

### LicenseTier

```python
from enum import Enum

class LicenseTier(Enum):
    """License tier levels."""
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"
```

### Feature

```python
from enum import Enum

class Feature(Enum):
    """Gated features."""
    # Free features
    VALIDATE = "validate"
    JSON_OUTPUT = "json_output"
    FIX_DRYRUN = "fix_dryrun"
    FINGERPRINT = "fingerprint"

    # Pro features
    FIX_APPLY = "fix_apply"
    PDF_REPORT = "pdf_report"
    HTML_REPORT = "html_report"
    SARIF_FULL = "sarif_full"
    JUNIT_OUTPUT = "junit_output"

    # Team features
    SHARED_PROFILES = "shared_profiles"
    AUDIT_API = "audit_api"

    # Enterprise features
    SSO = "sso"
    CUSTOM_RULES = "custom_rules"
    SLA = "sla"
```

### License

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class License(BaseModel, frozen=True):
    """
    License information.

    CRITICAL: Verified by Ed25519 signature.
    """
    license_id: str
    tier: LicenseTier
    org_id: Optional[str] = None
    org_name: Optional[str] = None
    seats: int = 1
    features: list[str]  # Feature IDs
    issued_at: datetime
    expires_at: datetime
    signature: str  # Base64 Ed25519 signature

    def has_feature(self, feature: Feature) -> bool:
        """Check if license includes feature."""
        return feature.value in self.features

    def is_expired(self) -> bool:
        """Check if license is expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def days_until_expiry(self) -> int:
        """Days until license expires."""
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, delta.days)
```

### ExpiryStatus

```python
from enum import Enum

class ExpiryStatus(Enum):
    """License expiry status."""
    VALID = "valid"
    EXPIRING_SOON = "expiring_soon"  # < 14 days
    EXPIRED = "expired"
```

### FeatureGateError

```python
class FeatureGateError(Exception):
    """Raised when accessing gated feature without license."""

    def __init__(self, feature: Feature, required_tier: LicenseTier):
        self.feature = feature
        self.required_tier = required_tier
        super().__init__(
            f"Feature '{feature.value}' requires {required_tier.value} license. "
            f"Upgrade at https://datev-lint.dev/pricing"
        )
```

### TelemetryEvent

```python
from pydantic import BaseModel
from datetime import datetime

class TelemetryEvent(BaseModel, frozen=True):
    """
    Anonymized telemetry event.

    CRITICAL: NEVER contains PII or booking data.
    """
    event_type: str  # "validation", "fix", "error"
    timestamp: datetime
    version: str
    os: str  # "windows", "linux", "macos"

    # Aggregated data only
    file_size_bucket: str  # "<10k", "10k-100k", "100k-1M", ">1M"
    profile_id: str
    finding_counts: dict[str, int]  # {"DVL-FIELD-011": 5}
    duration_ms: int

    # Optional
    license_tier: Optional[str] = None
```

### TelemetryConfig

```python
from pydantic import BaseModel
from pathlib import Path

class TelemetryConfig(BaseModel):
    """Telemetry configuration."""
    enabled: bool = False
    endpoint: str = "https://telemetry.datev-lint.dev/v1/events"
    config_path: Path = Path.home() / ".datev-lint" / "telemetry.json"

    @classmethod
    def load(cls) -> "TelemetryConfig":
        """Load from config file or environment."""
        # Check environment first
        if os.environ.get("DATEV_LINT_TELEMETRY") == "0":
            return cls(enabled=False)

        # Check config file
        config_path = cls.model_fields["config_path"].default
        if config_path.exists():
            return cls.model_validate_json(config_path.read_text())

        return cls()
```

## Service Models

### LicenseVerifier

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
import base64
import json

class LicenseVerifier:
    """
    Verifies license signatures offline.

    Uses Ed25519 for fast, secure verification.
    """

    def __init__(self, public_key: Ed25519PublicKey):
        self.public_key = public_key

    def verify(self, license_data: dict) -> bool:
        """Verify license signature."""
        signature = base64.b64decode(license_data.pop("signature"))
        payload = json.dumps(license_data, sort_keys=True).encode()

        try:
            self.public_key.verify(signature, payload)
            return True
        except Exception:
            return False

    @classmethod
    def from_pem(cls, pem_data: bytes) -> "LicenseVerifier":
        """Create verifier from PEM public key."""
        from cryptography.hazmat.primitives import serialization
        public_key = serialization.load_pem_public_key(pem_data)
        return cls(public_key)
```

### LicenseLoader

```python
from pathlib import Path

class LicenseLoader:
    """Loads and validates license files."""

    SEARCH_PATHS = [
        Path(".datev-lint-license.json"),
        Path.home() / ".datev-lint" / "license.json",
        Path("/etc/datev-lint/license.json"),
    ]

    def __init__(self, verifier: LicenseVerifier):
        self.verifier = verifier

    def load(self) -> License | None:
        """Find and load valid license."""
        for path in self.SEARCH_PATHS:
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    if self.verifier.verify(data.copy()):
                        return License.model_validate(data)
                except Exception:
                    continue
        return None
```

### FeatureGate

```python
from functools import wraps

class FeatureGate:
    """Checks feature access based on license."""

    # Feature to tier mapping
    TIER_FEATURES = {
        LicenseTier.FREE: {
            Feature.VALIDATE,
            Feature.JSON_OUTPUT,
            Feature.FIX_DRYRUN,
            Feature.FINGERPRINT,
        },
        LicenseTier.PRO: {
            Feature.FIX_APPLY,
            Feature.PDF_REPORT,
            Feature.HTML_REPORT,
            Feature.SARIF_FULL,
            Feature.JUNIT_OUTPUT,
        },
        LicenseTier.TEAM: {
            Feature.SHARED_PROFILES,
            Feature.AUDIT_API,
        },
        LicenseTier.ENTERPRISE: {
            Feature.SSO,
            Feature.CUSTOM_RULES,
            Feature.SLA,
        },
    }

    @classmethod
    def check(cls, feature: Feature, license: License | None) -> bool:
        """Check if feature is available."""
        if license is None:
            return feature in cls.TIER_FEATURES[LicenseTier.FREE]

        if license.is_expired():
            return feature in cls.TIER_FEATURES[LicenseTier.FREE]

        # Check all tiers up to and including license tier
        available = set()
        for tier in LicenseTier:
            available.update(cls.TIER_FEATURES.get(tier, set()))
            if tier == license.tier:
                break

        return feature in available

    @classmethod
    def require(cls, feature: Feature):
        """Decorator to require feature."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                license = get_current_license()
                if not cls.check(feature, license):
                    raise FeatureGateError(feature, cls.get_required_tier(feature))
                return func(*args, **kwargs)
            return wrapper
        return decorator
```

### TelemetryClient

```python
import httpx

class TelemetryClient:
    """Sends anonymized telemetry (opt-in only)."""

    def __init__(self, config: TelemetryConfig):
        self.config = config
        self.client = httpx.AsyncClient() if config.enabled else None

    async def send(self, event: TelemetryEvent) -> bool:
        """Send telemetry event (if enabled)."""
        if not self.config.enabled or not self.client:
            return False

        try:
            response = await self.client.post(
                self.config.endpoint,
                json=event.model_dump(mode="json")
            )
            return response.is_success
        except Exception:
            return False  # Fail silently

    def prompt_opt_in(self) -> bool:
        """Prompt user for telemetry opt-in."""
        console.print(
            "[bold]datev-lint[/] can send anonymous usage data to help improve the tool.\n"
            "No booking data is ever sent.\n\n"
            "Learn more: https://datev-lint.dev/telemetry\n"
        )
        response = Prompt.ask("Enable telemetry?", choices=["y", "n"], default="n")
        return response.lower() == "y"
```
