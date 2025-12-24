# Feature Specification: Fix Engine

**Feature Branch**: `003-fix-engine`
**Created**: 2025-12-24
**Status**: Draft
**Input**: Product Specification v2.1 - Section 9 (Fix-Engine Architektur), Section 4.6 (Writer-Modi)

## User Scenarios & Testing

### User Story 1 - Dry-Run Fix Preview (Priority: P1)

Als Buchhalter möchte ich sehen, welche Korrekturen vorgeschlagen werden, bevor ich sie anwende.

**Why this priority**: Dry-Run ist in OSS-Version verfügbar und Kernfunktion.

**Independent Test**: `--dry-run` zeigt Patch-Plan ohne Dateiänderung.

**Acceptance Scenarios**:

1. **Given** Datei mit Belegfeld1 "RE-2025.001" (Punkt ungültig), **When** `fix --dry-run`, **Then** Patch-Preview zeigt `"RE-2025.001" → "RE-2025001"`.
2. **Given** Datei mit 5 Fix-Candidates, **When** `fix --dry-run`, **Then** alle 5 Patches werden angezeigt mit Zeilen-Referenz.
3. **Given** `fix --dry-run`, **When** ausgeführt, **Then** Original-Datei bleibt unverändert (Checksum gleich).

---

### User Story 2 - Apply Fixes Atomically (Priority: P1 - Pro)

Als zahlender Kunde möchte ich Korrekturen anwenden können, damit ich korrigierte Dateien direkt nutzen kann.

**Why this priority**: Kernfunktion der Pro-Version, Monetarisierung.

**Independent Test**: `--apply` schreibt korrigierte Datei und erstellt Backup.

**Acceptance Scenarios**:

1. **Given** Datei mit fixbaren Fehlern, **When** `fix --apply`, **Then** korrigierte Datei geschrieben + `.bak.{timestamp}` Backup erstellt.
2. **Given** Fix-Apply, **When** Schreibvorgang, **Then** atomisch via temp-file + rename (kein korrupter Zustand bei Crash).
3. **Given** Fix-Apply abgeschlossen, **When** Re-Validation, **Then** gefixte Fehler erscheinen nicht mehr in Findings.

---

### User Story 3 - Writer Mode: Preserve (Priority: P1)

Als Entwickler möchte ich minimale Diffs bei Korrekturen, damit Git-Reviews übersichtlich bleiben.

**Why this priority**: Default-Modus, wichtig für CI-Workflows.

**Independent Test**: Fix ändert nur betroffene Felder, nicht Quoting-Style oder Whitespace.

**Acceptance Scenarios**:

1. **Given** Datei mit custom Quoting, **When** `fix --write-mode preserve`, **Then** Original-Quoting für unveränderte Felder beibehalten.
2. **Given** Fix für Zeile 50, **When** `fix --write-mode preserve`, **Then** Zeilen 1-49 und 51+ byte-identisch zum Original.
3. **Given** Preserve nicht möglich (z.B. Encoding-Wechsel), **When** Fix angewendet, **Then** Fallback auf canonical + Warning.

---

### User Story 4 - Writer Mode: Canonical (Priority: P2)

Als Datenverantwortlicher möchte ich deterministischen Output, damit Dateien standardisiert sind.

**Why this priority**: Wichtig für automatisierte Pipelines.

**Independent Test**: Gleicher Input → immer identischer Output.

**Acceptance Scenarios**:

1. **Given** Datei mit mixed Quoting, **When** `fix --write-mode canonical`, **Then** alle Felder einheitlich gequotet.
2. **Given** Datei mit LF-Zeilenenden, **When** `fix --write-mode canonical`, **Then** Output hat CRLF (DATEV Standard).
3. **Given** gleiche Datei zweimal fixiert, **When** canonical Mode, **Then** Output byte-identisch.

---

### User Story 5 - Rollback Mechanism (Priority: P2)

Als Buchhalter möchte ich fehlerhafte Fixes rückgängig machen können.

**Why this priority**: Sicherheitsnetz für ungewollte Änderungen.

**Independent Test**: `rollback --run-id <id>` stellt Original wieder her.

**Acceptance Scenarios**:

1. **Given** Fix wurde angewendet mit run_id "abc123", **When** `rollback --run-id abc123`, **Then** Original-Datei wiederhergestellt.
2. **Given** Rollback-Befehl, **When** Backup existiert, **Then** Checksum wird verifiziert vor Restore.
3. **Given** Rollback erfolgreich, **When** Audit-Log geprüft, **Then** Rollback-Entry vorhanden.

---

### User Story 6 - Audit Log with Versions (Priority: P2)

Als Auditor möchte ich nachvollziehen können, welche Fixes wann mit welcher Version angewendet wurden.

**Why this priority**: Constitution Principle VI - Audit & Versioning.

**Independent Test**: Audit-Log enthält alle Versionen und Checksums.

**Acceptance Scenarios**:

1. **Given** Fix angewendet, **When** Audit-Log geprüft, **Then** enthält engine_version, ruleset_version, profile_version.
2. **Given** Fix angewendet, **When** Audit-Log geprüft, **Then** enthält file checksum before + after.
3. **Given** Fix angewendet, **When** Audit-Log geprüft, **Then** enthält Liste aller Patches mit row_no, field, old_value, new_value.

---

### User Story 7 - Fix Risk Levels and Approval (Priority: P2)

Als Buchhalter möchte ich bei riskanten Fixes gefragt werden, bevor sie angewendet werden.

**Why this priority**: Schutz vor unbeabsichtigten Datenänderungen.

**Independent Test**: Fixes mit `risk: high` erfordern explizite Bestätigung.

**Acceptance Scenarios**:

1. **Given** Fix mit `risk: low` (z.B. Dezimalformat), **When** `fix --accept-risk low`, **Then** automatisch angewendet.
2. **Given** Fix mit `risk: medium` (z.B. Truncation), **When** `fix --yes`, **Then** angewendet mit Warning.
3. **Given** Fix mit `risk: high` (z.B. Belegfeld-ID ändern), **When** `requires_approval: true`, **Then** interaktiver Prompt oder `--accept-risk high` erforderlich.

---

### User Story 8 - Conflict Detection (Priority: P3)

Als Fix-Engine möchte ich Konflikte erkennen, wenn mehrere Fixes das gleiche Feld betreffen.

**Why this priority**: Edge Case, aber wichtig für Robustheit.

**Independent Test**: Zwei Fixes für gleiches Feld werden als Konflikt erkannt.

**Acceptance Scenarios**:

1. **Given** zwei Regeln wollen Belegfeld1 ändern, **When** Patch-Planner läuft, **Then** Konflikt-Warning + nur erste Regel angewendet.
2. **Given** Konflikt erkannt, **When** Dry-Run, **Then** beide Alternativen werden angezeigt.

---

### Edge Cases

- Was passiert bei Dateien ohne Schreibrechte?
- Wie werden sehr große Fixes (1000+ Zeilen) gehandhabt?
- Was passiert bei Disk Full während Write?
- Wie verhält sich Rollback bei gelöschtem Backup?

## Requirements

### Functional Requirements

- **FR-001**: Engine MUSS Patch-Plan aus Findings generieren
- **FR-002**: Engine MUSS `--dry-run` Mode mit Diff-Preview unterstützen
- **FR-003**: Engine MUSS `--apply` mit atomischem Write (temp + rename) unterstützen (Pro)
- **FR-004**: Engine MUSS automatische Backups vor Apply erstellen
- **FR-005**: Engine MUSS Writer-Modi `preserve` (default) und `canonical` unterstützen
- **FR-006**: Engine MUSS Rollback via `run_id` ermöglichen
- **FR-007**: Engine MUSS Audit-Log mit allen Versionen und Checksums schreiben
- **FR-008**: Engine MUSS Risk-Levels (low, medium, high) für Fixes unterstützen
- **FR-009**: Engine MUSS Konflikt-Detection für überlappende Patches implementieren
- **FR-010**: Engine MUSS Re-Validation nach Apply durchführen

### Patch Operations

| Operation | Beschreibung | Risk |
|-----------|--------------|------|
| `set_field` | Feldwert setzen | varies |
| `normalize_decimal` | Dezimalformat korrigieren | low |
| `truncate` | Feld kürzen | medium |
| `sanitize_chars` | Zeichen ersetzen | medium |
| `upper` | Uppercase | low |
| `delete_row` | Zeile löschen | high |
| `split_file` | Datei aufteilen (>99.999) | medium |

### Key Entities

- **Patch**: Einzelne Änderung (row_no, field, operation, old_value, new_value, risk)
- **PatchPlan**: Geordnete Liste von Patches mit Konflikt-Info
- **AuditEntry**: Log-Eintrag mit run_id, timestamp, versions, checksums, patches
- **WriteResult**: Ergebnis des Schreibvorgangs (success, backup_path, new_checksum)

## Success Criteria

### Measurable Outcomes

- **SC-001**: Dry-Run für 50k Zeilen mit 100 Fixes ≤ 2s
- **SC-002**: Apply + Backup für 50k Zeilen ≤ 5s
- **SC-003**: 100% der Applies erzeugen Audit-Log-Entry
- **SC-004**: Preserve Mode: ≤ 5% Diff-Zeilen bei Einzel-Feld-Fix
- **SC-005**: Rollback stellt Original byte-identisch wieder her
