# Implementation Plan: Licensing & Monetization

**Branch**: `005-licensing` | **Date**: 2025-12-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-licensing/spec.md`
**Depends on**: All core features (cross-cutting)

## Summary

Implementierung des Lizenz- und Monetarisierungssystems für datev-lint. Ermöglicht Feature-Gates zwischen Free und Paid Tiers. Kernfunktionen:

1. **Offline License Verification** via Ed25519-Signatur
2. **Feature Gates** basierend auf License Tier
3. **Pro Plugin Distribution** als separates Package
4. **Telemetry Opt-In** (DACH-tauglich)
5. **License Expiry Handling** mit Warnings
6. **Graceful Degradation** bei abgelaufener Lizenz

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `cryptography` - Ed25519 Signature Verification
- `pydantic` - License Model
- `httpx` - Telemetry Client (optional)

**Storage**: License file (.datev-lint-license.json)
**Testing**: pytest with mock licenses
**Target Platform**: Windows, Linux, macOS (CLI)
**Project Type**: Single project + Pro Plugin
**Performance Goals**:
- License Verification ≤ 10ms
- No network latency for offline mode

**Constraints**:
- NEVER send booking data
- Telemetry must be opt-in
- Graceful fallback to Free tier

**Scale/Scope**: 4 tiers, 15+ gated features

## Constitution Check

| Principle | Requirement | Status |
|-----------|-------------|--------|
| **I. Library-First** | License module in core | ✅ Planned |
| **II. Parser Robustness** | N/A | ✅ N/A |
| **III. Type Safety** | Typed License model | ✅ Planned |
| **IV. Golden File Testing** | Test licenses | ✅ Planned |
| **V. Performance Gates** | Verify ≤ 10ms | ✅ Benchmarks |
| **VI. Audit & Versioning** | License in audit log | ✅ Planned |
| **VII. Privacy** | Opt-in telemetry, no PII | ✅ Core Feature |

**Gate Status**: ✅ PASSED

## Project Structure

### Source Code

```text
datev_lint/
├── core/
│   └── licensing/
│       ├── __init__.py      # Public API: check_license(), require_feature()
│       ├── models.py        # License, LicenseTier, Feature models
│       ├── verifier.py      # Ed25519 signature verification
│       ├── loader.py        # License file loading
│       ├── gates.py         # Feature gate decorators
│       ├── expiry.py        # Expiry checking and warnings
│       └── telemetry.py     # Opt-in telemetry client

datev_lint/
└── keys/
    └── public_key.pem       # Public key for verification

# Separate package: datev-lint-pro
datev_lint_pro/
├── __init__.py              # Plugin entry point
├── fix_apply.py             # Fix apply implementation
├── reports/
│   ├── pdf.py               # PDF report generation
│   └── html.py              # HTML report generation
└── advanced/
    └── sarif_full.py        # Full SARIF output

tests/
├── fixtures/
│   └── licenses/
│       ├── valid_pro.json
│       ├── valid_team.json
│       ├── expired.json
│       └── invalid_signature.json
├── unit/
│   ├── test_verifier.py
│   ├── test_gates.py
│   ├── test_expiry.py
│   └── test_telemetry.py
├── integration/
│   └── test_licensing_e2e.py
└── benchmark/
    └── test_verify_performance.py
```

## Complexity Tracking

> No Constitution violations - no complexity justification needed.
