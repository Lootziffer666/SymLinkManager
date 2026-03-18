# Regelwerk v1.1 — SymLinkManager Suite

Stand: 2026-03-18  
Sprache: de-DE  
Ziel: Umsetzbares Feinkonzept für eine sichere, modulare Aufräum-Suite (Win32-Programme, Archive-Infocheck, ACL/Cache/Link-Operations) mit Rollback, Risikoabsicherung und Reboot-Queue.

---

## 1) Datenmodell (final)

### 1.1 Kernobjekt `ProgramEntry`

```ts
ProgramEntry {
  id: string
  selected: boolean

  rawDisplayName: string
  normalizedName: string
  displayVersion?: string
  publisher?: string

  recordType: 'App' | 'Microsoft' | 'Runtime' | 'Driver' | 'Hotfix'
  category: 'Game' | 'Launcher' | 'Creative' | 'Utility' | 'DevTool' | 'Other' | 'Runtime' | 'Driver' | 'Microsoft' | 'Hotfix'
  riskLevel: 'Low' | 'Medium' | 'High'

  installLocation?: string
  uninstallString?: string
  quietUninstallString?: string
  windowsEstimatedSizeKB?: number

  estimatedInstallBytes: number
  estimatedUserDataBytes: number
  estimatedScreenshotBytes: number
  estimatedTotalBytes: number
  estimatedTotalHuman: string
  estimateConfidence: 'Low' | 'Medium' | 'High'
  estimateNotes: string[]

  legalStatus: 'Free' | 'Free Tier' | 'Free Available' | 'Paid' | 'Paid/Trial' | 'Unknown'
  legalAlternativeHint?: string
  legalAlternativeCandidates: string[]

  duplicateCount: number
  duplicateSources: string[]

  importMatch: {
    state: 'None' | 'Exact' | 'Fuzzy' | 'Weak'
    score: number // 0..100
    importedLine?: string
    notes: string[]
  }

  safetyFlags: {
    blockedByPolicy: boolean
    requiresAdmin: boolean
    manualRemovalNeeded: boolean
    rebootRecommended: boolean
    reloginRecommended: boolean
  }
}
```

### 1.2 Zusatzobjekt `ArtifactEntry` (ZIP/RAR/MSI/EXE-Infocheck)

```ts
ArtifactEntry {
  id: string
  path: string
  extension: '.zip' | '.rar' | '.7z' | '.msi' | '.exe'
  sizeBytes: number
  modifiedUtc: string

  displayNameGuess: string
  normalizedNameGuess: string
  vendorGuess?: string
  versionGuess?: string

  kind: 'Installer' | 'Archive' | 'PortableApp' | 'Patch' | 'Unknown'
  riskLevel: 'Low' | 'Medium' | 'High'

  infoCheck: {
    source: string[] // filename, msi properties, pe version info, archive listing
    confidence: 'Low' | 'Medium' | 'High'
    summary: string
    tags: string[]
  }

  relation: {
    matchesInstalled: boolean
    matchedProgramIds: string[]
    relationType: 'SameProduct' | 'PotentialAlternative' | 'BundleOverlap' | 'Unknown'
    relationConfidence: 'Low' | 'Medium' | 'High'
    relationNotes: string[]
  }

  archiveCheck?: {
    encrypted: boolean
    passwordMatchState: 'NotChecked' | 'MatchFound' | 'NoMatch' | 'Corrupt' | 'Unsupported'
    matchedPasswordAlias?: string
    testMethod?: string
    note?: string
  }
}
```

### 1.3 Queue-Objekt `DeferredAction`

```ts
DeferredAction {
  id: string
  type: 'Uninstall' | 'Delete' | 'Move' | 'ACLFix' | 'CacheClean' | 'LinkRepair'
  target: string
  commandPreview: string
  schedule: 'Now' | 'Relogin' | 'Reboot'
  requiresAdmin: boolean
  riskLevel: 'Low' | 'Medium' | 'High'
  createdUtc: string
  status: 'Queued' | 'Running' | 'Done' | 'Failed' | 'Cancelled'
  logPath?: string
}
```

---

## 2) Sicherheitsregeln (Uninstall-Parser + High-Risk-Guards)

### 2.1 Parser-Grundsätze

1. **Nie blind ausführen** (`Invoke-Expression` verboten).  
2. Kommando in **Executable + Args** zerlegen (robustes Quoting).  
3. Nur erlaubte Deinstallationsmuster zulassen:
   - `msiexec.exe /x {GUID}`
   - signierte Uninstaller im Installationspfad
   - bekannte Setup-Engines (`unins*.exe`, `setup.exe /uninstall`, etc.) mit Schutzregeln
4. Wenn `UninstallString` fehlt oder fragwürdig → `manualRemovalNeeded = true`.

### 2.2 Block-/Warnregeln

**Hard Block (niemals automatisch):**
- `recordType in (Driver, Hotfix, Microsoft)`
- `riskLevel == High`
- Einträge mit sicherheitskritischen Publishern/Komponenten (Runtime/Framework/SDK)

**Soft Block (nur mit Doppelbestätigung):**
- `riskLevel == Medium` + `category in (DevTool, Runtime)`
- fehlende Signatur + unbekannter Publisher

**Erlaubt (Standardfluss):**
- `riskLevel == Low` und `recordType == App`

### 2.3 Dry-Run-first

Jede destruktive Aktion unterstützt:
- Preview
- Exportiertes Skript
- `-WhatIfOnly`
- Logfile pro Aktion

### 2.4 Policy-Matrix

| Bedingung | Aktion |
|---|---|
| High Risk | blockieren, nur expliziter Expertenmodus |
| Driver/Hotfix/Microsoft | nie automatisch markieren |
| Unklarer Uninstall-Command | nur Skript-Export, keine Direktausführung |
| Keine Adminrechte | in Queue mit `requiresAdmin=true` |

---

## 3) Workflow-States (End-to-End)

1. **Scan**  
   Registry + optionale Dateisystemquellen für Artefakte.
2. **Normalize & Classify**  
   Namen normalisieren, deduplizieren, risk/category setzen.
3. **Filter & Presets**  
   Standard: Microsoft/Hotfix/Driver/Runtime/High-Risk ausgeblendet.
4. **Import-Match**  
   Rohlisten importieren, Exact/Fuzzy/Weak markieren.
5. **Estimate**  
   Größen auf Wunsch (Selected/Visible), mit Progress + Cancel.
6. **Relation Check**  
   Installiert vs. Archive/Installer vergleichen (gleicher Produktstamm, Alternative, Bundle-Overlap).
7. **Select**  
   Nutzer markiert Kandidaten.
8. **Export**  
   CSV + Uninstall-Skript + Snapshot.
9. **Execute**  
   Now / Relogin / Reboot Queue.
10. **Verify**  
   Ergebnisprüfung + Nachscan + Differenzbericht.

---

## 4) Archive-Validator-Spec (Passwortlistenmodus, kein Voll-Bruteforce)

### 4.1 Scope

- Unterstützte Formate: `.zip`, `.rar`, optional `.7z`.
- Quelle: gewählte Ordner/Laufwerke.
- Passwortmodus: **nur nutzereigene Passwortliste** (kein combinatorial brute force).

### 4.2 Ablauf

1. Archive inventarisieren.
2. Prüfen, ob verschlüsselt.
3. Für jedes verschlüsselte Archiv Passwortliste testen (Rate-Limit, Timeout).
4. Ergebnis speichern:
   - `MatchFound`
   - `NoMatch`
   - `Corrupt`
   - `Unsupported`
5. Vorsortieren in Ergebnisordner/Views.

### 4.3 Performance-Regeln

- HDD-Profil: 1–2 Worker, niedrige I/O-Last.
- SATA-SSD: 3–4 Worker.
- NVMe: 4–8 Worker.
- Retry nur bei transienten Lesefehlern.

### 4.4 Datenschutz/Sicherheit

- Passwortliste niemals im Klartext loggen.
- Optional nur Passwort-Hash-Alias in Ergebnisdatei speichern.
- Keine Netzwerkübertragung.

---

## 5) MVP in 3 Iterationen (konkret umsetzbar)

### Iteration 1 — Kerninventar + Safety

**Umfang:**
- Registry Scan (HKLM/HKCU + WOW6432Node)
- Normalisierung + Dedupe
- Klassifikation (RecordType/Category/Risk)
- Basisfilter + Preset „Nur Games + Launcher“
- Import Rohliste (Exact/Fuzzy/Weak)
- Whitelist/Blacklist laden/speichern
- Script Export (`-WhatIfOnly`) + CSV
- Snapshot + Log-Grundlage

**Akzeptanz:**
- Tool bleibt bei >1000 Einträgen bedienbar
- High-Risk nie automatisch markiert

### Iteration 2 — Größen + Relationen + Artefakt-Infocheck

**Umfang:**
- Größenabschätzung (InstallLocation zuerst)
- Erweiterte Userdata/Screenshot-Heuristik (optional)
- Artifact Scanner für ZIP/RAR/MSI/EXE
- Infocheck je Artefakt (Dateiname, Metadaten, Signatur, MSI-Properties)
- Relation Engine:
  - „bereits installiert"
  - „potenzielle Alternative"
  - „Tool-Bundle-Overlap"

**Akzeptanz:**
- Ergebnisfelder `Estimated*` + Confidence gefüllt
- Artefakte können nach Relation gefiltert werden

### Iteration 3 — Ausführungspipeline + Reboot/Relogin Queue

**Umfang:**
- Sicherheitsparser für Uninstall-Commands
- Direktausführung optional (mit Doppelbestätigung)
- DeferredAction Queue (Now/Relogin/Reboot)
- Post-Reboot-Verifikation
- Endbericht mit Erfolg/Fehler/Manual-ToDo

**Akzeptanz:**
- Gesperrte Aktionen können geplant und später sauber abgearbeitet werden
- Jede Aktion erzeugt nachvollziehbares Log

---

## 6) Regelwerk für Vergleiche (Installiert vs. Artefakte vs. Alternativen)

### 6.1 Matching-Stufen

- **Exact**: gleicher normalisierter Produktname + ähnliche Version/Publisher.
- **Near**: Levenshtein/Token-Overlap >= Schwellwert.
- **Weak**: nur Teilstring-Treffer ohne Publisher-Absicherung.

### 6.2 Vergleichsfragen (UI-Wizard)

1. **„Schon installiert — behalten?“**
   - Treffer: Artefakt entspricht installiertem Produkt.
2. **„Funktionaler Overlap?“**
   - z. B. mehrere Bildeditoren.
3. **„Alternative ausreichend?“**
   - Paid-Tool + Free/FOSS Alternative vorhanden.
4. **„Doppelte Installer-Versionen?“**
   - nur neueste behalten, alte in Quarantäne.

### 6.3 Vorschlagslogik

- Vorschläge sind **nie auto-destruktiv**.
- Output: `Keep`, `Archive`, `Quarantine`, `RemovalCandidate`.
- `High Risk` oder unsichere Confidence => nur Hinweis, keine Aktionsempfehlung.

---

## 7) Reboot-/Relogin-Mechanik

### 7.1 Relogin nötig wenn
- User-ENV/Path angepasst
- Shell-nahe Einstellungen geändert

### 7.2 Reboot nötig wenn
- Datei-Locks/Handles Deinstallation verhindern
- Treiber-/Dienstabhängige Entfernungen ausstehen

### 7.3 UX

- Pro Aktion sichtbarer Status: `Sofort`, `Relogin`, `Reboot`.
- Sammelbutton: „Ausstehende Aktionen beim nächsten Neustart ausführen“.
- Nach Neustart: Auto-Verify + Report.

---

## 8) Standard-Regelsätze (Startwerte)

- `Microsoft ausblenden = true`
- `Hotfix ausblenden = true`
- `Treiber ausblenden = true`
- `Runtime ausblenden = true`
- `High-Risk ausblenden = true`
- `Direkt-Uninstall = false` (Script-first)

---

## 9) Nichtziele / Compliance

- Keine Piracy-/Crack-Unterstützung.
- Kein Voll-Bruteforce über unendliche Passwortkombinationen.
- Keine automatische Entfernung kritischer Systemkomponenten.
- Keine Cloud-/Telemetry-Abhängigkeit.

---

## 10) Task Scheduler Triage (für Fälle wie „247 geplante Tasks“)

### 10.1 Ziel

Geplante Aufgaben nicht blind löschen/deaktivieren, sondern nach Risiko und Nutzen ordnen:

- Welche Aufgaben sind **systemkritisch**?
- Welche sind nur **Updater-/Telemetry-Rauschen**?
- Welche sind **defekt** (`Unavailable`) oder verwaist?

### 10.2 Datenmodell `TaskEntry`

```ts
TaskEntry {
  id: string
  taskPath: string
  taskName: string
  author?: string
  state: 'Ready' | 'Running' | 'Queued' | 'Disabled' | 'Unknown'
  lastRunTime?: string
  nextRunTime?: string
  triggerSummary?: string
  actionSummary?: string
  principal?: string
  source: 'Microsoft' | 'Vendor' | 'User' | 'Unknown'
  category: 'SystemCritical' | 'Security' | 'Update' | 'Maintenance' | 'Telemetry' | 'AppSupport' | 'Unknown'
  riskLevel: 'Low' | 'Medium' | 'High'
  health: 'OK' | 'Unavailable' | 'Orphaned' | 'BrokenAction'
  recommendation: 'Keep' | 'DisableCandidate' | 'DeleteCandidate' | 'Investigate'
  recommendationReason: string[]
}
```

### 10.3 Klassifikationsregeln

**High-Risk (nur Hinweis, keine Auto-Aktion):**
- Microsoft-Tasks in Pfaden wie `\\Microsoft\\Windows\\*` mit Kategorien:
  - `SystemCritical`, `Security`, `Maintenance`
- Defender-/Update-/Storage-/Recovery-nahe Aufgaben

**Medium-Risk:**
- Vendor-Updater (Adobe, Google, NVIDIA, ASUS, WD, etc.)
- App-Helper-/Telemetry-Tasks

**Low-Risk:**
- klar user-angelegte, nicht-kritische App-Autoupdater
- doppelte/obsolet wirkende Updater mit deaktiviertem Zustand

### 10.4 Health-Checks

- `Unavailable`: Zielbinary fehlt oder Pfad ungültig.
- `Orphaned`: Hersteller-App nicht mehr installiert, Task existiert noch.
- `BrokenAction`: Kommando verweist auf nicht existente EXE/Skriptdatei.
- `Overactive`: ungewöhnlich hoher Trigger-Takt (z. B. im Minutentakt ohne Bedarf).

### 10.5 Safe Actions

1. **Preview only** (Default)
2. **Disable Candidate anwenden** (batch-fähig, reversible)
3. **Delete Candidate** erst nach Quarantänefenster
4. **Rollback**: vorheriger Task-Status wird als Snapshot gespeichert

### 10.6 Harte Schutzregeln

- Nie pauschal `\\Microsoft\\Windows\\` deaktivieren.
- Nie Defender-/WaaSMedic-/UpdateOrchestrator-/Storage-/Recovery-Aufgaben automatisch ändern.
- `Unavailable` bei Microsoft-Tasks => `Investigate`, keine Löschung.

---

## 11) Autoruns/Registry-Anomalien Triage

### 11.1 Ziel

Die „anderen Probleme“ (z. B. verdächtige Shell/AppInit/Policy-Einträge) strukturiert einordnen:

- legitime Tweaks vs. Malware-/PUP-Risiko
- Funktionsstörungen durch aggressive Tweaks erkennen

### 11.2 Prüffelder

- `HKLM/HKCU\\...\\Run`, `RunOnce`, `Winlogon\\Shell`, `Userinit`
- `AppInit_DLLs`, `ShellServiceObjectDelayLoad`
- Policy-Keys wie `DisableTaskMgr`, `DisableCMD`, `DisableRegistryTools`, `DisableLockWorkStation`
- Signaturstatus der referenzierten Binärdateien

### 11.3 Bewertungslogik

- **High-Risk**:
  - Unsignierte Autostarts in sensiblen Hooks (AppInit/Winlogon/Shell)
  - Policy-Keys, die Admin-/Recovery-Werkzeuge sperren
  - fehlende Datei + persistenter Startpunkt
- **Medium-Risk**:
  - unbekannter Publisher, aber gültiger Pfad
  - fragwürdige Browser-/Shell-Helfer
- **Low-Risk**:
  - signierte, bekannte Einträge mit stabiler Herkunft

### 11.4 Aktionen

- `Investigate`: nur markieren + Kontext anzeigen
- `DisableCandidate`: nicht löschen, nur deaktivieren (reversibel)
- `RemoveCandidate`: erst nach Snapshot + optional Reboot

---

## 12) Erweiterte MVP-Planung (inkl. Task/Autoruns)

### Iteration 1.1 (direkt nach Iteration 1)

- Task Scheduler Inventar + Klassifikation + Health-Status
- Preset: „Nur Disable-Kandidaten (Low/Medium, nicht Microsoft-kritisch)“
- Export: `tasks-review.csv` + `tasks-disable-plan.ps1`

### Iteration 2.1

- Autoruns/Registry-Triage-Modul mit Risikoampel
- Sicherheitsreport „Hardening vs. Breaking Tweaks“
- Export: `autoruns-review.csv` + `autoruns-remediation-plan.ps1`

### Iteration 3.1

- Reboot-/Relogin-Queue für Task-/Autoruns-Änderungen
- Post-Reboot-Verifikation (Task-Status + Key-Diff)
- Sammelbericht: „Applied / Skipped / Manual Investigation“
