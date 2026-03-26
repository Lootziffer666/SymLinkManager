# TabulaRasa – Purge safely. Reclaim space.

> **Purge-orientiertes Cleanup-Tool für Windows – klar getrennt von Tabula, mit gleicher Sicherheitsdisziplin.**  
> Drei explizite Lösch-Modi, Review-Pflicht für riskante Kategorien, vollständige Ledger-Historie.

---

## Inhalt

- [Was TabulaRasa ist](#was-tabularasa-ist)
- [Workflow: 4 Tabs](#workflow-4-tabs)
- [Ausführungs-Modi](#ausführungs-modi)
- [Scanner & Regelwerk](#scanner--regelwerk)
- [Sicherheitsregeln](#sicherheitsregeln)
- [Datenmodell-Übersicht](#datenmodell-übersicht)
- [Verzeichnisstruktur](#verzeichnisstruktur)
- [Start & Voraussetzungen](#start--voraussetzungen)
- [Aktueller Stand & Roadmap](#aktueller-stand--roadmap)

---

## Was TabulaRasa ist

TabulaRasa ist das destruktivere Schwester-Tool zu Tabula. Während Tabula auf Storage-Analyse und sichere Relocation fokussiert, liegt TabulaRasas Schwerpunkt auf **Purge-Workflows**: erkennen, was sicher gelöscht werden kann, planen, prüfen, ausführen – mit vollständiger Ledger-Historie.

**Kernprinzip:** Kein Auto-Delete. Keine stille Aktion. Orphaned App Data immer review-pflichtig.

---

## Workflow: 4 Tabs

### 1. Scan

**Purge Map – disposable data first**

- Startet beide Scanner: `scan_known_paths()` (bekannte Windows-Pfade) und `load_rule_packs()` (YAML-Regelwerk)
- Ergebnis-Tabelle mit Spalten:  
  `Selected` | `Name` | `Kind` | `Size` | `Risk` | `Action` | `Review` | `Path`
- Doppelklick togglet die Auswahl eines Eintrags
- Detail-Panel zeigt Pfad, Kind, Risiko, empfohlene Aktion und Notizen
- Einträge per Preset oder manuell selektierbar

### 2. Plan

**Presets und Lösch-Modi wählen**

| Preset | Selektiert | Standard-Modus |
|---|---|---|
| **Safe Cleanup** | Nur Low-Risk, kein Review-Pflicht | RecycleBinPreferred |
| **Aggressive Cleanup** | Alles mit Aktion Purge oder Review | PermanentDelete |
| **Orphaned App Data Review** | Nur `AppResidue` / `OrphanedAppData` | DryRun (nur Vorschau) |

- Ausführungs-Modus manuell überschreibbar
- „Preview current plan“ zeigt detaillierte Vorschau ohne Ausführung

### 3. Run

**Ausführung – Dry-Run bevorzugt**

- „Execute plan“ führt den Plan im gewählten Modus aus
- Bei `PermanentDelete`: Pflicht-Bestätigung mit Warnhinweis
- Ergebnis wird im Log-Textfeld ausgegeben
- Nach Ausführung: History wird automatisch aktualisiert

### 4. History

**Ledger, Export, Tagesrückblick**

- Alle bisherigen Purge-Runs werden angezeigt:  
  `Zeitstempel` | `Modus` | `Anzahl Items` | `Geschätzte Bytes`
- **Export JSON + CSV:** vollständige Historie in zwei Formaten
- **„Was würde ich heute löschen?“:** Replay der heutigen Entscheidungen ohne Ausführung

---

## Ausführungs-Modi

| Modus | Intern | Verhalten |
|---|---|---|
| **DryRun** | `DryRun` | Nur Vorschau, keine Systemänderung |
| **Safe** | `RecycleBinPreferred` | Dateien in den Papierkorb (wiederherstellbar) |
| **Aggressive** | `PermanentDelete` | Dauerhaftes Löschen nach expliziter Bestätigung |

> Aggressive Mode erfordert eine zusätzliche `messagebox.askyesno`-Bestätigung in der GUI.

---

## Scanner & Regelwerk

### Known-Paths-Scanner (`scanners/known_paths.py`)

Scannt bekannte Windows-Standardpfade:

- `%TEMP%` und `%TMP%`
- Shader-Caches (z. B. NVIDIA, AMD, DirectX)
- Browser-Caches
- Windows Update-Caches
- Weitere systemnahe temporäre Ordner

### Regelbasierter Scanner (`scanners/rule_based.py`)

Lädt YAML-Regelwerk aus `shared/rule_packs/default.yaml`.  
Jede Regel definiert:

```yaml
- name: Windows Temp
  path: "%TEMP%"          # Windows-Umgebungsvariablen werden expandiert
  kind: Temp              # PurgeKind (Temp / Cache / ShaderCache / OrphanedAppData / …)
  risk: Low               # RiskLevel (Low / Medium / High)
  action: Purge           # RecommendedAction (Purge / Review / Keep)
  review_required: false  # Review-Pflicht (erzwingt manuelles Abhaken)
  notes: "…"
```

Pfade werden nur einbezogen, wenn sie existieren und nicht geschützt sind.  
Ergebnisse werden absteigend nach Größe sortiert.

**Standard-Regeln (`default.yaml`):**

| Name | Pfad | Kind | Risiko | Review-Pflicht |
|---|---|---|---|---|
| Windows Temp | `%TEMP%` | Temp | Low | Nein |
| Local AppData Cache | `%LOCALAPPDATA%` | Cache | Medium | Ja |
| Orphaned App Data Review | `%APPDATA%` | OrphanedAppData | High | Ja |

Eigene Regeln können in `default.yaml` ergänzt oder als neue YAML-Dateien unter `shared/rule_packs/` abgelegt werden.

---

## Sicherheitsregeln

- **Kein Auto-Delete.** Alle Aktionen werden erst geplant, dann bestätigt.
- **DryRun als Standard.** Beim Start ist der Modus immer `DryRun`, bis der Nutzer explizit wechselt.
- **Review-Pflicht:** Items mit `review_required: true` (insb. `OrphanedAppData`) können via Preset nur im DryRun-Modus selektiert werden.
- **Aggressive-Bestätigung:** `PermanentDelete` erfordert eine explizite `messagebox`-Bestätigung.
- **Geschützte Pfade:** `is_protected()` verhindert, dass kritische System-Ordner (Windows, System32, Programme) in den Scan-Ergebnissen auftauchen.
- **Backups:** Das `backups/`-Verzeichnis speichert Snapshots vor Ausführungen.
- **Keine Cloud, keine Telemetrie.**

---

## Datenmodell-Übersicht

### `PurgeItem`

| Feld | Typ | Beschreibung |
|---|---|---|
| `kind` | `PurgeKind` | Temp / Cache / ShaderCache / Logs / OrphanedAppData / … |
| `risk_level` | `RiskLevel` | Low / Medium / High |
| `recommended_action` | `RecommendedAction` | Purge / Review / Keep |
| `review_required` | bool | Nutzer muss manuell bestätigen |
| `size_bytes` | int | Größe des Ordners/der Datei |
| `detection_source` | str | KnownPath / RuleBased |

### `PurgeRun` (Ledger-Eintrag)

| Feld | Typ | Beschreibung |
|---|---|---|
| `started_at` | datetime | Start der Ausführung |
| `mode` | `ExecutionMode` | DryRun / RecycleBinPreferred / PermanentDelete |
| `selected_item_count` | int | Anzahl der selektierten Items |
| `estimated_bytes` | int | Geschätzte Einsparung |
| `deleted_bytes` | int? | Tatsächlich gelöschte Bytes |
| `failed_count` | int | Fehlgeschlagene Aktionen |

### `PurgeKind`-Werte

`Temp` · `Cache` · `ShaderCache` · `Logs` · `Thumbnails` · `Screenshots` · `Captures` ·  
`InstallerLeftovers` · `UpdaterResidue` · `AppResidue` · `OrphanedAppData` · `Unknown`

---

## Verzeichnisstruktur

```
TabulaRasa/
├── tabula_rasa.py              # Einstiegspunkt (_setup_logging → TabulaRasaApp)
├── gui/
│   ├── __init__.py
│   └── main_window.py          # TabulaRasaApp: 4 Tabs (Scan/Plan/Run/History)
├── scanners/
│   ├── known_paths.py          # Scanner für bekannte Windows-Systempfade
│   └── rule_based.py           # YAML-Regelwerk-Scanner
├── shared/
│   ├── core/
│   │   ├── models.py           # PurgeItem, PurgeRun, PurgeKind, ExecutionMode, …
│   │   └── path_utils.py       # expand_windows_path, folder_size, is_protected
│   ├── engine/
│   │   ├── execution.py        # ExecutionEngine (preview, execute, what_would_delete_today)
│   │   └── history.py          # Ledger (load, export_json, export_csv)
│   └── rule_packs/
│       └── default.yaml        # Standard-Regelwerk (erweiterbar)
├── backups/                    # Backup-Snapshots vor Ausführungen
└── logs/
    └── tabula_rasa.log         # Startup-Log (auto-erstellt)
```

---

## Start & Voraussetzungen

**Python 3.11+** empfohlen. TabulaRasa teilt die Requirements aus dem `Tabula/`-Unterverzeichnis.

```bash
# Vom Repo-Root aus:
pip install -r Tabula/requirements/gui.txt
pip install -r Tabula/requirements/core.txt  # pyyaml ist hier enthalten (Regelwerk-Parser)

python TabulaRasa/tabula_rasa.py
```

> **Hinweis:** Auf Linux/macOS startet die GUI (customtkinter), aber Windows-spezifische  
> Purge-Kategorien (Shader-Caches, AppData-Pfade) werden **nicht erkannt und sind nicht verfügbar**.

---

## Aktueller Stand & Roadmap

### Implementiert

- [x] 4-Tab-Workflow: Scan / Plan / Run / History
- [x] Known-Paths-Scanner (Windows Temp, AppData, System-Caches)
- [x] YAML-Regelwerk-Scanner mit Pfad-Expansion, Größenmessung, Schutzprüfung
- [x] 3 Ausführungs-Modi: DryRun / Safe (RecycleBin) / Aggressive (PermanentDelete)
- [x] Presets: Safe Cleanup / Aggressive Cleanup / Orphaned App Data Review
- [x] Review-Pflicht für `OrphanedAppData`
- [x] Ledger-Persistenz (JSON)
- [x] Export: JSON + CSV
- [x] „Was würde ich heute löschen?“-Tagesrückblick
- [x] Aggressive-Bestätigung via messagebox
- [x] Strukturiertes Logging in `logs/tabula_rasa.log`
- [x] PyInstaller-Build → `builds/TabulaRasa.exe`

### Noch offen

- [ ] **Windows Live-Tests** für alle drei Modi
- [ ] **Backup vor Ausführung:** automatischen Snapshot in `backups/` vor Safe/Aggressive anlegen
- [ ] **Erweitertes Regelwerk:** Shader-Cache-Pfade (NVIDIA/AMD/DirectX), Browser-Caches (Chrome/Edge/Firefox), WinSxS-Analyse
- [ ] **Orphaned App Data:** automatischer Abgleich mit installierten Programmen (Exact/Fuzzy-Match)
- [ ] **Post-Run-Differenzbericht:** tatsächlich gelöschte Bytes vs. Schätzung
- [ ] **Signierter Build + MSIX-Installer**
