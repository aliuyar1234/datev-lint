# Tasks: Licensing & Monetization

**Input**: Design documents from `/specs/005-licensing/`
**Prerequisites**: All core features (cross-cutting concern)
**Depends on**: CLI, Rule Engine, Fix Engine

## Phase 1: Setup

- [ ] T001 Create `datev_lint/core/licensing/` directory structure
- [ ] T002 [P] Create `datev_lint/core/licensing/__init__.py` with public API
- [ ] T003 [P] Create `datev_lint/keys/` directory for public key
- [ ] T004 [P] Add `cryptography>=41.0` to dependencies
- [ ] T005 [P] Create `tests/fixtures/licenses/` directory

---

## Phase 2: Foundational

- [ ] T006 Create LicenseTier enum in `datev_lint/core/licensing/models.py`
- [ ] T007 Create Feature enum in `datev_lint/core/licensing/models.py`
- [ ] T008 [P] Create License model in `datev_lint/core/licensing/models.py`
- [ ] T009 [P] Create ExpiryStatus enum in `datev_lint/core/licensing/models.py`
- [ ] T010 Create FeatureGateError in `datev_lint/core/licensing/models.py`

**Checkpoint**: All models defined

---

## Phase 3: License Verification - US3 (Priority: P1) 🎯 MVP

**Goal**: Offline Ed25519 verification

- [ ] T011 [P] [US3] Create test key pair for development
- [ ] T012 [P] [US3] Create `tests/fixtures/licenses/valid_pro.json`
- [ ] T013 [P] [US3] Create `tests/fixtures/licenses/invalid_signature.json`
- [ ] T014 [P] [US3] Create `tests/unit/test_verifier.py`
- [ ] T015 [US3] Implement LicenseVerifier in `datev_lint/core/licensing/verifier.py`
- [ ] T016 [US3] Add public key to `datev_lint/keys/public_key.pem`
- [ ] T017 [US3] Implement `verify_license()` in `datev_lint/core/licensing/__init__.py`

**Checkpoint**: License verification works offline

---

## Phase 4: License Loading - US3 (Priority: P1)

**Goal**: Find and load license from multiple paths

- [ ] T018 [P] [US3] Create `tests/unit/test_loader.py`
- [ ] T019 [US3] Implement LicenseLoader in `datev_lint/core/licensing/loader.py`
- [ ] T020 [US3] Implement search path logic in `datev_lint/core/licensing/loader.py`
- [ ] T021 [US3] Implement `get_license()` in `datev_lint/core/licensing/__init__.py`

---

## Phase 5: Feature Gates - US1, US2, US4 (Priority: P1)

**Goal**: Gate Pro features

- [ ] T022 [P] [US2] Create `tests/unit/test_gates.py`
- [ ] T023 [US4] Define tier → features mapping in `datev_lint/core/licensing/gates.py`
- [ ] T024 [US2] Implement FeatureGate class in `datev_lint/core/licensing/gates.py`
- [ ] T025 [US2] Implement `check_feature()` in `datev_lint/core/licensing/__init__.py`
- [ ] T026 [US2] Implement `@require_feature` decorator in `datev_lint/core/licensing/gates.py`
- [ ] T027 [US1] Verify Free tier works without license in `tests/integration/test_free_tier.py`
- [ ] T028 [US2] Add feature gates to fix apply in `datev_lint/core/fix/__init__.py`
- [ ] T029 [US2] Add feature gates to PDF report in `datev_lint/cli/output/pdf.py`

**Checkpoint**: Feature gates work

---

## Phase 6: Expiry Handling - US5 (Priority: P2)

**Goal**: 14-day warning, graceful fallback

- [ ] T030 [P] [US5] Create `tests/fixtures/licenses/expired.json`
- [ ] T031 [P] [US5] Create `tests/unit/test_expiry.py`
- [ ] T032 [US5] Implement expiry checking in `datev_lint/core/licensing/expiry.py`
- [ ] T033 [US5] Add 14-day warning to CLI in `datev_lint/cli/main.py`
- [ ] T034 [US5] Implement graceful fallback in `datev_lint/core/licensing/gates.py`

---

## Phase 7: Pro Plugin Architecture - US6 (Priority: P1)

**Goal**: Separate Pro package

- [ ] T035 [P] [US6] Create `datev_lint_pro/` directory structure
- [ ] T036 [P] [US6] Create `datev_lint_pro/__init__.py`
- [ ] T037 [US6] Move fix apply implementation to `datev_lint_pro/fix_apply.py`
- [ ] T038 [US6] Add plugin detection in `datev_lint/core/licensing/__init__.py`
- [ ] T039 [US6] Create separate `pyproject.toml` for datev-lint-pro

---

## Phase 8: Telemetry - US7 (Priority: P2)

**Goal**: Opt-in telemetry

- [ ] T040 [P] [US7] Create TelemetryEvent model in `datev_lint/core/licensing/telemetry.py`
- [ ] T041 [P] [US7] Create TelemetryConfig model in `datev_lint/core/licensing/telemetry.py`
- [ ] T042 [P] [US7] Create `tests/unit/test_telemetry.py`
- [ ] T043 [US7] Implement TelemetryClient in `datev_lint/core/licensing/telemetry.py`
- [ ] T044 [US7] Implement opt-in prompt in `datev_lint/cli/main.py`
- [ ] T045 [US7] Add DATEV_LINT_TELEMETRY=0 check in `datev_lint/core/licensing/telemetry.py`
- [ ] T046 [US7] Create `/docs/telemetry.md` documentation

---

## Phase 9: Seat-based Licensing - US8 (Priority: P3)

**Goal**: Team/Enterprise seat tracking

- [ ] T047 [P] [US8] Create `tests/fixtures/licenses/valid_team.json`
- [ ] T048 [P] [US8] Create `tests/unit/test_seats.py`
- [ ] T049 [US8] Implement seat tracking in `datev_lint/core/licensing/seats.py`
- [ ] T050 [US8] Add seat warning to CLI in `datev_lint/cli/main.py`

---

## Phase 10: CLI Integration

**Goal**: Show license info in CLI

- [ ] T051 Add license info to --version in `datev_lint/cli/main.py`
- [ ] T052 Show upgrade CTA on feature gate hit in `datev_lint/cli/main.py`
- [ ] T053 [P] Create `tests/integration/test_licensing_cli.py`

---

## Phase 11: Performance

**Goal**: Verification ≤ 10ms

- [ ] T054 [P] Create `tests/benchmark/test_verify_performance.py`
- [ ] T055 Optimize signature verification in `datev_lint/core/licensing/verifier.py`

---

## Phase 12: Polish

- [ ] T056 [P] Add docstrings to all public functions
- [ ] T057 [P] Run mypy and fix type errors
- [ ] T058 [P] Run ruff and fix linting issues
- [ ] T059 Update public API exports in `datev_lint/core/licensing/__init__.py`

---

## Summary

| Phase | Tasks | Purpose |
|-------|-------|---------|
| 1. Setup | T001-T005 | Directory structure |
| 2. Foundational | T006-T010 | Models |
| 3. Verification | T011-T017 | Ed25519 (MVP) |
| 4. Loading | T018-T021 | License files |
| 5. Gates | T022-T029 | Feature gates |
| 6. Expiry | T030-T034 | Warnings |
| 7. Pro Plugin | T035-T039 | Separate package |
| 8. Telemetry | T040-T046 | Opt-in analytics |
| 9. Seats | T047-T050 | Team licensing |
| 10. CLI | T051-T053 | Integration |
| 11. Performance | T054-T055 | Optimization |
| 12. Polish | T056-T059 | Docs, types |

**Total Tasks**: 59
**MVP Tasks (Phase 1-5)**: 29
