# Feature Specification: CLI & Output Adapters

**Feature Branch**: `004-cli-outputs`
**Created**: 2025-12-24
**Status**: Draft
**Input**: Product Specification v2.1 - Section 11 (CLI-Interface), Section 12 (Reporting Engine), Section 7 (Exporter Fingerprinting)

## User Scenarios & Testing

### User Story 1 - Validate Command with Terminal Output (Priority: P1)

Als Entwickler möchte ich `datev-lint validate <file>` ausführen und farbige Terminal-Ausgabe sehen.

**Why this priority**: Basis-CLI ist Einstiegspunkt für alle Nutzer.

**Independent Test**: `validate` zeigt Findings mit Farben (rot=ERROR, gelb=WARN).

**Acceptance Scenarios**:

1. **Given** Datei mit Fehlern, **When** `validate file.csv`, **Then** Findings werden farbig angezeigt mit Zeilennummern.
2. **Given** valide Datei, **When** `validate file.csv`, **Then** "No issues found" Meldung + Exit Code 0.
3. **Given** Datei mit FATAL Error, **When** `validate file.csv`, **Then** Exit Code 2.

---

### User Story 2 - JSON Output for Automation (Priority: P1)

Als CI-Pipeline möchte ich Findings als JSON erhalten, damit ich sie automatisiert verarbeiten kann.

**Why this priority**: Machine-readable Output ist Kernfunktion für Automation.

**Independent Test**: `--format json` liefert valides JSON mit allen Finding-Feldern.

**Acceptance Scenarios**:

1. **Given** Datei mit Fehlern, **When** `validate --format json`, **Then** Output ist valides JSON-Array.
2. **Given** JSON Output, **When** geparst, **Then** jedes Finding enthält `code`, `rule_version`, `severity`, `message`, `location`.
3. **Given** `--out findings.json`, **When** ausgeführt, **Then** JSON wird in Datei geschrieben.

---

### User Story 3 - Exit Codes for CI/CD (Priority: P1)

Als CI-Pipeline möchte ich korrekte Exit Codes, damit Builds bei Fehlern fehlschlagen.

**Why this priority**: CI-Integration ist Kernfeature.

**Independent Test**: Exit Code entspricht höchstem Severity-Level.

**Acceptance Scenarios**:

1. **Given** keine Findings, **When** `validate`, **Then** Exit Code 0.
2. **Given** nur WARN Findings, **When** `validate`, **Then** Exit Code 0 (default).
3. **Given** ERROR Findings, **When** `validate`, **Then** Exit Code 1.
4. **Given** FATAL Error, **When** `validate`, **Then** Exit Code 2.
5. **Given** WARN Findings, **When** `validate --fail-on warn`, **Then** Exit Code 1.

---

### User Story 4 - SARIF Output for GitHub (Priority: P2)

Als GitHub-Nutzer möchte ich SARIF-Output, damit Findings im Code Scanning erscheinen.

**Why this priority**: GitHub Integration erhöht Visibility.

**Independent Test**: SARIF-Output ist valides SARIF 2.1.0 JSON.

**Acceptance Scenarios**:

1. **Given** Datei mit Fehlern, **When** `validate --format sarif`, **Then** Output ist valides SARIF 2.1.0.
2. **Given** SARIF Output, **When** in GitHub hochgeladen, **Then** Findings erscheinen als Code Scanning Alerts.
3. **Given** SARIF Output, **When** geparst, **Then** `runs[0].tool.driver.rules` enthält alle getriggerten Regeln.

---

### User Story 5 - Profile Selection (Priority: P1)

Als Steuerberater möchte ich Profile auswählen können, damit mandantenspezifische Regeln gelten.

**Why this priority**: Profile-System ist Kernfeature für Flexibilität.

**Independent Test**: `--profile de.skr03.default` aktiviert SKR03-spezifische Regeln.

**Acceptance Scenarios**:

1. **Given** Datei, **When** `validate --profile de.skr03.default`, **Then** SKR03-Profil wird verwendet.
2. **Given** ungültiger Profil-Name, **When** `validate --profile xyz`, **Then** Error-Meldung mit Liste verfügbarer Profile.
3. **Given** kein Profil angegeben, **When** `validate`, **Then** Default-Profil wird verwendet.

---

### User Story 6 - Exporter Fingerprinting (Priority: P2)

Als Erstnutzer möchte ich automatische Exporter-Erkennung, damit das richtige Profil vorgeschlagen wird.

**Why this priority**: Reduziert Setup-Friction, erhöht Adoption.

**Independent Test**: sevDesk-Export wird erkannt und Profil vorgeschlagen.

**Acceptance Scenarios**:

1. **Given** sevDesk-Export, **When** `validate`, **Then** Hinweis "Exporter erkannt: sevDesk (87%)" + Profil-Vorschlag.
2. **Given** `--auto-profile`, **When** Exporter erkannt, **Then** empfohlenes Profil wird automatisch verwendet.
3. **Given** `fingerprint file.csv`, **When** ausgeführt, **Then** zeigt erkannte Exporter-Signale und Konfidenz.

---

### User Story 7 - PDF/HTML Reports (Priority: P3 - Pro)

Als Steuerberater möchte ich PDF-Reports erstellen, um sie an Mandanten zu senden.

**Why this priority**: Pro-Feature für Steuerberater-Workflow.

**Independent Test**: `report --format pdf` erstellt valide PDF-Datei.

**Acceptance Scenarios**:

1. **Given** Datei mit Fehlern, **When** `report --format pdf --out report.pdf`, **Then** PDF mit Findings erstellt.
2. **Given** PDF-Report, **When** geöffnet, **Then** enthält Header-Summary, Findings-Liste, Fix-Vorschläge.
3. **Given** 50k-Zeilen-Datei, **When** PDF-Report generiert, **Then** Generierungszeit ≤ 5s.

---

### User Story 8 - List Available Commands (Priority: P1)

Als Nutzer möchte ich Hilfe zu verfügbaren Befehlen sehen.

**Why this priority**: UX-Grundlage.

**Independent Test**: `--help` zeigt alle Befehle mit Beschreibung.

**Acceptance Scenarios**:

1. **Given** `datev-lint --help`, **When** ausgeführt, **Then** Liste aller Commands (validate, fix, report, profiles, rules, explain).
2. **Given** `datev-lint validate --help`, **When** ausgeführt, **Then** alle Optionen für validate gezeigt.
3. **Given** `datev-lint explain DVL-FIELD-011`, **When** ausgeführt, **Then** Regel-Beschreibung, Beispiele, Fix-Hinweise.

---

### Edge Cases

- Was passiert bei Terminal ohne Farbunterstützung?
- Wie werden sehr lange Findings-Listen gehandhabt (Pagination)?
- Was passiert bei Output in Pipe (kein TTY)?
- Wie verhält sich `--quiet` Mode?

## Requirements

### Functional Requirements

- **FR-001**: CLI MUSS `validate` Command mit Terminal-Output unterstützen
- **FR-002**: CLI MUSS `--format` Option für Output-Format (terminal, json, sarif) unterstützen
- **FR-003**: CLI MUSS korrekte Exit Codes liefern (0=ok, 1=error, 2=fatal)
- **FR-004**: CLI MUSS `--fail-on` Option für CI-Schwellenwert unterstützen
- **FR-005**: CLI MUSS `--profile` Option für Profil-Auswahl unterstützen
- **FR-006**: CLI MUSS Exporter-Fingerprinting mit Profil-Vorschlag unterstützen
- **FR-007**: CLI MUSS `fix` Command mit `--dry-run` und `--apply` unterstützen
- **FR-008**: CLI MUSS `report` Command für PDF/HTML-Export unterstützen (Pro)
- **FR-009**: CLI MUSS `profiles list` und `rules list` Commands unterstützen
- **FR-010**: CLI MUSS `explain <rule-code>` für Regel-Dokumentation unterstützen

### CLI Commands

| Command | Beschreibung | Tier |
|---------|--------------|------|
| `validate <file>` | Datei validieren | Free |
| `fix <file>` | Fixes anzeigen/anwenden | Free (dry-run) / Pro (apply) |
| `report <file>` | Report generieren | Pro |
| `profiles list` | Profile auflisten | Free |
| `rules list` | Regeln auflisten | Free |
| `explain <code>` | Regel erklären | Free |
| `fingerprint <file>` | Exporter erkennen | Free |
| `rollback --run-id <id>` | Fix rückgängig | Pro |

### Output Formats

| Format | Beschreibung | Tier |
|--------|--------------|------|
| Terminal (Rich) | Farbige CLI-Ausgabe | Free |
| JSON | Machine-readable | Free |
| SARIF | GitHub Code Scanning | Free (basic) / Pro (full) |
| JUnit XML | CI Test Reports | Pro |
| PDF/HTML | Steuerberater-Reports | Pro |

### Key Entities

- **CliContext**: Parsed Arguments, Config, Profile
- **OutputAdapter**: Interface für verschiedene Output-Formate
- **ExporterFingerprint**: Erkannter Exporter mit Konfidenz

## Success Criteria

### Measurable Outcomes

- **SC-001**: Terminal-Output für 1000 Findings ≤ 1s
- **SC-002**: JSON-Output ist 100% valides JSON (Schema-validiert)
- **SC-003**: SARIF-Output ist 100% SARIF 2.1.0 konform
- **SC-004**: Exporter-Fingerprinting Accuracy ≥ 80% für Top-3-Exporter
- **SC-005**: PDF-Report für 50k Zeilen ≤ 5s
