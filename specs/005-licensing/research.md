# Research: Licensing & Monetization

**Feature**: 005-licensing
**Date**: 2025-12-24
**Status**: Complete

## Research Questions

### RQ-1: License File Format

**Decision**: Signed JSON with Ed25519

```json
{
  "license_id": "lic_abc123",
  "tier": "pro",
  "org_id": "org_xyz",
  "org_name": "Mustermann GmbH",
  "seats": 1,
  "features": ["fix_engine", "pdf_report", "sarif_full"],
  "issued_at": "2025-01-01T00:00:00Z",
  "expires_at": "2026-01-01T00:00:00Z",
  "signature": "base64_ed25519_signature_of_payload"
}
```

**Signature Scope**: All fields except `signature` itself

---

### RQ-2: Ed25519 Verification

**Decision**: `cryptography` library for offline verification

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
import json
import base64

class LicenseVerifier:
    def __init__(self, public_key_pem: bytes):
        self.public_key = serialization.load_pem_public_key(public_key_pem)

    def verify(self, license_data: dict) -> bool:
        signature = base64.b64decode(license_data.pop("signature"))
        payload = json.dumps(license_data, sort_keys=True).encode()

        try:
            self.public_key.verify(signature, payload)
            return True
        except Exception:
            return False
```

**Performance**: < 1ms per verification

---

### RQ-3: Feature Gate Implementation

**Decision**: Decorator-based gates

```python
from functools import wraps

def require_feature(feature: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            license = get_current_license()
            if not license.has_feature(feature):
                raise FeatureGateError(
                    f"Feature '{feature}' requires Pro license. "
                    f"Upgrade at https://datev-lint.dev/pricing"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@require_feature("fix_engine")
def apply_fixes(patches):
    ...
```

---

### RQ-4: License Tiers

**Decision**: 4 Tiers with feature sets

| Tier | Features |
|------|----------|
| `free` | validate, json, dry-run, fingerprint |
| `pro` | + fix apply, pdf, sarif full, junit |
| `team` | + shared profiles, audit log api |
| `enterprise` | + sso, custom rules, sla |

```python
class LicenseTier(Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"

TIER_FEATURES = {
    LicenseTier.FREE: {"validate", "json_output", "fix_dryrun", "fingerprint"},
    LicenseTier.PRO: {"fix_apply", "pdf_report", "sarif_full", "junit"},
    LicenseTier.TEAM: {"shared_profiles", "audit_api"},
    LicenseTier.ENTERPRISE: {"sso", "custom_rules", "sla"},
}
```

---

### RQ-5: Telemetry Design (DACH-compliant)

**Decision**: Opt-in with minimal data

**Opt-in Flow**:
```
First run:
┌─────────────────────────────────────────────────────────┐
│ datev-lint can send anonymous usage data to help       │
│ improve the tool. No booking data is ever sent.        │
│                                                         │
│ Learn more: https://datev-lint.dev/telemetry           │
│                                                         │
│ Enable telemetry? [y/N]                                │
└─────────────────────────────────────────────────────────┘
```

**Data Collected (if opted in)**:
```python
class TelemetryEvent(BaseModel):
    event_type: str  # "validation", "fix", "error"
    timestamp: datetime
    version: str
    os: str  # "windows", "linux", "macos"

    # Aggregated, no PII
    file_size_bucket: str  # "<10k", "10k-100k", "100k-1M", ">1M"
    profile_id: str
    finding_counts: dict[str, int]  # {"DVL-FIELD-011": 5}
    duration_ms: int
```

**NEVER Collected**:
- File paths
- Booking data (amounts, accounts, texts)
- IP addresses (if possible)
- Organization/user identifiers

---

### RQ-6: Pro Plugin Architecture

**Decision**: Separate package with entry points

**OSS Package** (`datev-lint`):
```python
# datev_lint/core/fix/apply.py
def apply_fixes(patches):
    # Check for Pro plugin
    try:
        from datev_lint_pro.fix_apply import apply_fixes_impl
        return apply_fixes_impl(patches)
    except ImportError:
        raise FeatureGateError("Fix apply requires datev-lint-pro")
```

**Pro Package** (`datev-lint-pro`):
```python
# datev_lint_pro/__init__.py
# Entry point for plugin discovery

# datev_lint_pro/fix_apply.py
def apply_fixes_impl(patches):
    # Actual implementation
    ...
```

**Distribution**:
- OSS: PyPI public
- Pro: Private PyPI / GitHub Releases with license check

---

### RQ-7: Expiry Handling

**Decision**: 14-day warning + graceful fallback

```python
def check_license_expiry(license: License) -> ExpiryStatus:
    now = datetime.now(timezone.utc)
    days_until_expiry = (license.expires_at - now).days

    if days_until_expiry < 0:
        return ExpiryStatus.EXPIRED
    elif days_until_expiry <= 14:
        return ExpiryStatus.EXPIRING_SOON
    else:
        return ExpiryStatus.VALID

def handle_expired_license():
    # Log warning
    console.print("[yellow]License expired. Pro features disabled.[/yellow]")
    console.print("Renew at https://datev-lint.dev/account")

    # Fall back to Free tier
    return License(tier=LicenseTier.FREE)
```

---

### RQ-8: License File Locations

**Decision**: Multiple search paths

```python
LICENSE_SEARCH_PATHS = [
    Path(".datev-lint-license.json"),  # Current directory
    Path.home() / ".datev-lint" / "license.json",  # User home
    Path("/etc/datev-lint/license.json"),  # System (Linux)
]

def find_license() -> License | None:
    for path in LICENSE_SEARCH_PATHS:
        if path.exists():
            return load_and_verify(path)
    return None
```

---

## Dependencies

```toml
[project]
dependencies = [
    "pydantic>=2.0",
    "cryptography>=41.0",
]

[project.optional-dependencies]
telemetry = [
    "httpx>=0.25",
]
```
