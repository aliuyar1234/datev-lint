# Feature Specification: Licensing & Monetization

**Feature Branch**: `005-licensing`
**Created**: 2025-12-24
**Status**: Draft
**Input**: Product Specification v2.1 - Section 13 (Monetarisierungs-Architektur)

## User Scenarios & Testing

### User Story 1 - Free Tier Validation (Priority: P1)

Als Entwickler möchte ich datev-lint kostenlos für Validierung nutzen können.

**Why this priority**: Adoption über Free Tier, dann Conversion zu Paid.

**Independent Test**: Ohne Lizenz funktionieren alle Free-Features.

**Acceptance Scenarios**:

1. **Given** keine Lizenz installiert, **When** `validate file.csv`, **Then** Validierung funktioniert vollständig.
2. **Given** keine Lizenz, **When** `fix --dry-run`, **Then** Patch-Preview wird angezeigt.
3. **Given** keine Lizenz, **When** `--format json`, **Then** JSON-Output funktioniert.

---

### User Story 2 - Pro Feature Gate (Priority: P1)

Als Free-Nutzer sehe ich CTA für Pro-Features, wenn ich sie nutzen will.

**Why this priority**: Conversion-Treiber.

**Independent Test**: `fix --apply` ohne Lizenz zeigt Upgrade-CTA.

**Acceptance Scenarios**:

1. **Given** keine Lizenz, **When** `fix --apply`, **Then** Error mit "Upgrade to Pro for fix apply" + Link.
2. **Given** keine Lizenz, **When** `report --format pdf`, **Then** Error mit Upgrade-CTA.
3. **Given** Pro-Lizenz, **When** `fix --apply`, **Then** Fixes werden angewendet.

---

### User Story 3 - Offline License Verification (Priority: P1)

Als Enterprise-Kunde möchte ich datev-lint ohne Internet-Verbindung nutzen können.

**Why this priority**: On-Prem/Air-Gapped Environments sind häufig in DACH.

**Independent Test**: Signierte Lizenz-Datei wird offline verifiziert.

**Acceptance Scenarios**:

1. **Given** gültige Lizenz-Datei `.datev-lint-license.json`, **When** CLI startet, **Then** Lizenz wird ohne HTTP-Call verifiziert.
2. **Given** Lizenz mit Ed25519-Signatur, **When** Signatur valide, **Then** Features entsprechend `tier` freigeschaltet.
3. **Given** Lizenz-Datei manipuliert, **When** Signatur-Check, **Then** Lizenz wird abgelehnt + Error.

---

### User Story 4 - License Tiers and Features (Priority: P1)

Als Lizenz-System muss ich Features basierend auf Tier freischalten.

**Why this priority**: Kernlogik der Monetarisierung.

**Independent Test**: Pro-Tier schaltet fix-apply frei, Team-Tier zusätzlich shared profiles.

**Acceptance Scenarios**:

1. **Given** Lizenz mit `tier: "pro"`, **When** `fix --apply`, **Then** erlaubt.
2. **Given** Lizenz mit `tier: "pro"`, **When** `report --format pdf`, **Then** erlaubt.
3. **Given** Lizenz mit `tier: "free"`, **When** `fix --apply`, **Then** CTA.
4. **Given** Lizenz mit `tier: "team"`, **When** Shared Profile Upload, **Then** erlaubt.

---

### User Story 5 - License Expiry Handling (Priority: P2)

Als Kunde erwarte ich klare Kommunikation bei ablaufender Lizenz.

**Why this priority**: Retention durch rechtzeitige Warnung.

**Independent Test**: 14 Tage vor Ablauf erscheint Warning.

**Acceptance Scenarios**:

1. **Given** Lizenz läuft in 14 Tagen ab, **When** CLI startet, **Then** Warning "License expires in 14 days".
2. **Given** Lizenz abgelaufen, **When** Pro-Feature genutzt, **Then** Fallback auf Free + Renew-CTA.
3. **Given** Lizenz abgelaufen, **When** Free-Features genutzt, **Then** funktionieren normal.

---

### User Story 6 - Pro Plugin Distribution (Priority: P1)

Als zahlender Kunde installiere ich das Pro-Plugin separat.

**Why this priority**: Packaging-Strategie aus Spezifikation.

**Independent Test**: `pip install datev-lint-pro` + Lizenz = Pro-Features verfügbar.

**Acceptance Scenarios**:

1. **Given** `datev-lint` installiert (OSS), **When** `pip install datev-lint-pro`, **Then** Pro-Plugin wird erkannt.
2. **Given** Pro-Plugin ohne Lizenz, **When** Pro-Feature genutzt, **Then** CTA für Lizenz-Aktivierung.
3. **Given** Pro-Plugin + gültige Lizenz, **When** `fix --apply`, **Then** funktioniert.

---

### User Story 7 - Telemetry Opt-In (Priority: P2)

Als datenschutzbewusster Nutzer möchte ich bei Telemetrie gefragt werden.

**Why this priority**: Constitution Principle VII - Privacy by Design.

**Independent Test**: Erster Start zeigt Opt-In Prompt.

**Acceptance Scenarios**:

1. **Given** erster CLI-Start, **When** interaktiv, **Then** Opt-In Prompt für Telemetrie.
2. **Given** `DATEV_LINT_TELEMETRY=0`, **When** CLI startet, **Then** kein Prompt, keine Telemetrie.
3. **Given** Opt-In akzeptiert, **When** Validierung läuft, **Then** anonymisierte Nutzungsdaten gesendet.
4. **Given** Telemetrie aktiv, **When** Daten gesendet, **Then** keine Buchungstexte/Kontonummern enthalten.

---

### User Story 8 - Seat-based Licensing (Priority: P3 - Team/Enterprise)

Als Team-Admin möchte ich Lizenzen für mehrere Nutzer verwalten.

**Why this priority**: Team/Enterprise Tier.

**Independent Test**: Lizenz mit `seats: 5` erlaubt 5 gleichzeitige Nutzer.

**Acceptance Scenarios**:

1. **Given** Lizenz mit `seats: 5`, **When** 5 Nutzer aktiv, **Then** alle können Pro-Features nutzen.
2. **Given** Lizenz mit `seats: 5`, **When** 6. Nutzer startet, **Then** Warning + Fallback auf Free oder Queue.
3. **Given** Team-Lizenz, **When** Admin-Dashboard, **Then** Seat-Nutzung sichtbar.

---

### Edge Cases

- Was passiert bei korrupter Lizenz-Datei?
- Wie werden Zeitzonen bei Expiry behandelt?
- Was passiert bei Clock-Skew (System-Zeit falsch)?
- Wie wird License Revocation gehandhabt?

## Requirements

### Functional Requirements

- **FR-001**: System MUSS Offline-License-Verification via Ed25519-Signatur unterstützen
- **FR-002**: System MUSS Feature-Gates basierend auf License-Tier implementieren
- **FR-003**: System MUSS License-Expiry mit 14-Tage-Warning kommunizieren
- **FR-004**: System MUSS Pro-Plugin als separates Package unterstützen
- **FR-005**: System MUSS Telemetrie opt-in bei erstem Start implementieren
- **FR-006**: System MUSS `DATEV_LINT_TELEMETRY=0` für Opt-Out respektieren
- **FR-007**: System DARF NIE Buchungsdaten in Telemetrie senden
- **FR-008**: System MUSS CTA mit Upgrade-Link bei Feature-Gate zeigen
- **FR-009**: System MUSS graceful Fallback bei abgelaufener Lizenz (Free-Features bleiben)
- **FR-010**: System MUSS Seat-Count für Team/Enterprise Lizenzen unterstützen

### License File Structure

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
  "signature": "base64_ed25519_signature"
}
```

### Feature Matrix

| Feature | Free | Pro | Team | Enterprise |
|---------|------|-----|------|------------|
| Validate (30 rules) | ✅ | ✅ | ✅ | ✅ |
| JSON Output | ✅ | ✅ | ✅ | ✅ |
| Exporter Fingerprinting | ✅ | ✅ | ✅ | ✅ |
| Fix dry-run | ✅ | ✅ | ✅ | ✅ |
| Fix apply | ❌ | ✅ | ✅ | ✅ |
| PDF/HTML Reports | ❌ | ✅ | ✅ | ✅ |
| SARIF full | ❌ | ✅ | ✅ | ✅ |
| JUnit XML | ❌ | ✅ | ✅ | ✅ |
| Shared Profiles | ❌ | ❌ | ✅ | ✅ |
| Audit Log API | ❌ | ❌ | ✅ | ✅ |
| SSO/SAML | ❌ | ❌ | ❌ | ✅ |
| Custom Rules | ❌ | ❌ | ❌ | ✅ |
| SLA | ❌ | ❌ | ❌ | ✅ |

### Key Entities

- **License**: Lizenz-Objekt mit tier, features, expiry, signature
- **LicenseVerifier**: Verifiziert Ed25519-Signatur offline
- **FeatureGate**: Prüft ob Feature für aktuelle Lizenz verfügbar
- **TelemetryClient**: Sendet anonymisierte Nutzungsdaten (opt-in)

## Success Criteria

### Measurable Outcomes

- **SC-001**: License-Verification ≤ 10ms (keine Netzwerk-Latenz)
- **SC-002**: 0% False Positives bei Signatur-Verification
- **SC-003**: Telemetrie enthält 0 PII (Buchungsdaten, Kontonummern)
- **SC-004**: Free→Pro Conversion Rate ≥ 3% (Tracking via Telemetrie)
- **SC-005**: Upgrade-CTA wird bei 100% der Feature-Gate-Hits angezeigt
