# Quickstart: Licensing & Monetization

**Feature**: 005-licensing
**Date**: 2025-12-24

## Free Tier Usage

All core validation features work without a license:

```bash
# Validate files
datev-lint validate file.csv

# Preview fixes (dry-run)
datev-lint fix file.csv --dry-run

# JSON output
datev-lint validate file.csv --format json

# Fingerprint exporter
datev-lint fingerprint file.csv
```

## Pro Features

Pro features require a license:

```bash
# Apply fixes (Pro)
datev-lint fix file.csv --apply
# Error: Feature 'fix_apply' requires Pro license.
# Upgrade at https://datev-lint.dev/pricing

# PDF reports (Pro)
datev-lint report file.csv --format pdf --out report.pdf
# Error: Feature 'pdf_report' requires Pro license.
```

## Installing a License

### 1. Purchase License

Visit https://datev-lint.dev/pricing to purchase a Pro license.

### 2. Download License File

After purchase, download your license file (`.datev-lint-license.json`).

### 3. Install License

Place the license file in one of these locations:

```bash
# Option 1: Current directory
cp license.json .datev-lint-license.json

# Option 2: Home directory
mkdir -p ~/.datev-lint
cp license.json ~/.datev-lint/license.json

# Option 3: System-wide (Linux)
sudo cp license.json /etc/datev-lint/license.json
```

### 4. Verify License

```bash
datev-lint --version
# datev-lint 1.0.0
# License: Pro (expires 2026-01-01)
# Organization: Mustermann GmbH
```

## Pro Plugin Installation

For Pro features, install the Pro plugin:

```bash
pip install datev-lint-pro
```

With both the license and plugin installed, all Pro features work:

```bash
datev-lint fix file.csv --apply  # Works!
datev-lint report file.csv --format pdf --out report.pdf  # Works!
```

## License File Format

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
  "signature": "..."
}
```

## License Tiers

| Tier | Price | Features |
|------|-------|----------|
| **Free** | €0 | Validate, JSON, Dry-run, Fingerprint |
| **Pro** | €29/mo | + Fix apply, PDF/HTML, SARIF full, JUnit |
| **Team** | €79/mo | + Shared profiles, Audit API |
| **Enterprise** | Custom | + SSO, Custom rules, SLA |

## Expiry Warnings

```bash
# 14 days before expiry
datev-lint validate file.csv
# ⚠️  License expires in 14 days. Renew at https://datev-lint.dev/account

# After expiry
datev-lint fix file.csv --apply
# ⚠️  License expired. Pro features disabled.
# Renew at https://datev-lint.dev/account
```

## Telemetry

### First Run Opt-In

```
datev-lint can send anonymous usage data to help improve the tool.
No booking data is ever sent.

Learn more: https://datev-lint.dev/telemetry

Enable telemetry? [y/N]
```

### Disable Telemetry

```bash
# Environment variable
export DATEV_LINT_TELEMETRY=0

# Or config file
echo '{"enabled": false}' > ~/.datev-lint/telemetry.json
```

### What We Collect (if opted in)

- File size bucket (e.g., "<10k", "10k-100k")
- Profile used
- Finding counts by rule
- Execution duration
- Tool version, OS

### What We NEVER Collect

- File contents
- Booking data (amounts, accounts, texts)
- File paths
- Organization/user identifiers
- IP addresses (if possible)

## Programmatic License Check

```python
from datev_lint.core.licensing import get_license, check_feature, Feature

# Check current license
license = get_license()
if license:
    print(f"Tier: {license.tier}")
    print(f"Expires: {license.expires_at}")
else:
    print("No license (Free tier)")

# Check feature availability
if check_feature(Feature.FIX_APPLY):
    print("Fix apply available")
else:
    print("Fix apply requires Pro")
```

## Feature Gate Decorator

```python
from datev_lint.core.licensing import require_feature, Feature

@require_feature(Feature.PDF_REPORT)
def generate_pdf(findings):
    # Only runs if Pro license is present
    ...
```

## Team Licensing

For Team tier with multiple seats:

```json
{
  "tier": "team",
  "seats": 5,
  ...
}
```

Usage is tracked, and warnings appear when nearing seat limit:

```
⚠️  4 of 5 seats in use. Contact admin to add more seats.
```
