# Tabula – Find it. Clear it. Move it.

> **Modularer Windows-Desktop-Host für Storage-Analyse, Programm-Triage, sichere Aktionsplanung und System-Cleanup.**  
> Konservativ by default – jede Aktion zuerst als Plan, jede Ausführung mit Vorschau und Undo.

---

## Inhalt

- [Was Tabula ist](#was-tabula-ist)
- [Module](#module)
- [Profil-System](#profil-system)
- [Sicherheitsarchitektur](#sicherheitsarchitektur)
- [Datenmodell-Übersicht](#datenmodell-übersicht)
- [Verzeichnisstruktur](#verzeichnisstruktur)
- [Start & Voraussetzungen](#start--voraussetzungen)
- [Aktueller Stand & Roadmap](#aktueller-stand--roadmap)

---

## Was Tabula ist

Tabula ist ein modularer Windows-Desktop-Host (customtkinter/tkinter). Er lädt beim Start `modules.json` und baut für jedes aktivierte Modul einen eigenen Tab. Neue Module können hinzugefügt werden, ohne den Host selbst anzufassen.

**Kernprinzip:** Erst verstehen → dann planen → dann (optional) ausführen.  
Keine stillen Auto-Fixes. Kein blinder Ausführungszwang.

Die GUI verwendet ein **Dark/Light-Theme** (Anthrazit/Orange ↔ Weiß/Rot) mit Live-Toggle.

---

## Module

Alle Module sind in `modules.json` einzeln aktivierbar/deaktivierbar.

### Programme (`programs`)

- Win32-Programme aus allen relevanten Registry-Quellen inventarisieren:  
  `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` +  
  `HKCU\...` + WOW6432Node-Varianten
- Namen normalisieren und deduplizieren
- Klassifizieren nach `RecordType` (App / Microsoft / Runtime / Driver / Hotfix) und  
  `Category` (Game / Launcher / Creative / Utility / DevTool / SystemComponent / Other)
- Risikostufen vergeben (Low / Medium / High)
- **Import-Matching:** eigene Textliste (eine Zeile = ein Programmname) tolerant abgleichen –  
  ignoriert Versions-/Bitness-Suffixe, bewertet Treffer als Exact / Fuzzy / Weak
- **Größenabschätzung:** realistischere Größe als Windows-Standard –  
  InstallLocation + Nutzerdaten/Screenshots/Caches mit Confidence-Feld (Low/Medium/High)
- Uninstall-Skript-Export (prüfbar, kein blindes Ausführen) + CSV-Export
- Filter/Presets (z. B. „Nur Games + Launcher", „High Risk ausblenden")

### Archive (`archives`)

- ZIP / RAR / 7z / MSI / EXE erfassen und einordnen (Dateiname, Metadaten, Signatur)
- Erkennt, ob ein Artefakt vermutlich bereits installiert ist oder funktional überlappt
- **Passwortlistenprüfung:** ZIP-Archive auf Passwortverschlüsselung prüfen –  
  optionale eigene Passwortliste (eine Zeile = ein Passwort), nie geloggt, kein Brute-Force
- Status-Spalten: `öffnbar` / `verschlüsselt` / `Overlap` / `unbekannt`
- Ausgewählte Archive direkt in den Plan übernehmbar

### UWP & AI (`uwp_ai`)

- Installierte UWP/AppX-Pakete inventarisieren
- KI-bezogene Pakete markieren (Copilot, Recall, NPU-nahe Komponenten)
- AI-Companion-Einstellungen (Ollama / CustomGPT)

### Tasks & Services (`tasks_services`)

- Geplante Aufgaben vollständig inventarisieren (Windows Task Scheduler via WMI/COM)
- Klassifizierung: SystemCritical / Security / Update / Maintenance / Telemetry / AppSupport
- Farb-Codierung: rot = kritisch, grün = aktiv, grau = deaktiviert
- Detail-Panel: Pfad, Trigger, Ausführungskonto, Letzter/Nächster Run, Beschreibung
- **Gaming-Preset** und **Minimal-Preset** für Service-Anpassungen (in Plan übernehmbar)
- Threaded Scan (kein UI-Freeze)

### Privacy & Autoruns (`privacy`)

- Registry-Autostart- und Hook-Bereiche prüfen:  
  `Run` / `RunOnce` / `Winlogon\Shell` / `Userinit` / `AppInit_DLLs` / Policy-Keys  
  (`DisableTaskMgr`, `DisableCMD`, `DisableRegistryTools`, `DisableLockWorkStation`)
- Auffällige/unsignierte Einträge rot markieren
- Privacy-Presets: **Balanced** / **Strict** / **Paranoid** (in Plan übernehmbar)

### Duplikate (`duplicates`)

- Datei-Duplikate per Inhalts-Hash finden
- **Keep-Best-Scoring:** welches Exemplar ist das beste (Pfad, Datum, Größe)?
- DOCX/TXT-Merge-Unterstützung via Smart Merge
- Ausgewählte Aktionen in Plan übernehmbar

### Micro-Apps / Add-ons (`micro_apps`)

Zentraler Katalog (`micro_apps/catalog.json`) mit 12 vorproduzierten Add-ons:

| Add-on | Kategorie | Risiko |
|---|---|---|
| True Debloat Undo | Snapshot & Restore | Medium |
| PathSafe Duplicate | Files | Low |
| Safe ARP Cleaner | Registry | Medium |
| Update Guard | Windows Update | Medium |
| Context Menu Safe Cleaner | Shell | Medium |
| Vendor Bloat Guardian | OEM Cleanup | High |
| Background Killer | Processes | High |
| OneDrive Repair Guard | Repair | Medium |
| Explorer Shell Guard | Shell | Medium |
| Recall Storage Wiper | AI Data | High |
| NPU Guard | AI Control | High |
| Winget Source Fix | Package Mgmt | Low |

### Plan & Execute (`plan_execute`)

Alle Module fügen Aktionen in einen gemeinsamen `SafePlanner` ein. Dieses Modul verwaltet und führt den Plan aus:

- **Vorschau:** Aktionen mit Timing, Risiko, Impact-MB und High-Risk-Markierung
- **Dry-Run:** nur Vorschau, keine Systemänderung
- **JETZT AUSFÜHREN:** mit doppelter Bestätigung bei High/Critical-Risk-Aktionen
- **Timing pro Aktion:** `Jetzt` / `Nach Re-Login` / `Nach Neustart`  
  (deferred Actions werden in `tabula_deferred_actions.json` serialisiert)
- **Undo:** letzten Registry-Snapshot importieren
- **Plan exportieren/importieren:** JSON-Serialisierung aller Aktionen
- **Benchmarks:** Vorher/Nachher-Vergleich von Systemkennzahlen

### Module Manager (`module_manager`)

- Module einzeln aktivieren/deaktivieren
- Profil laden (Core-only / Full) – sofort wirksam nach Neustart
- Aktuelle Konfiguration als `modules.json` speichern

---

## Profil-System

| Profil | Datei | Aktivierte Module |
|---|---|---|
| Core | `profiles/core_only.modules.json` | Programme, Tasks & Services, Privacy, Plan & Execute, Module Manager |
| Full | `profiles/full.modules.json` | Alle Module außer Micro-Apps (Nightly) |

Das aktive Profil wird als `modules.json` im App-Root gespeichert.  
**Default:** Core-Profil (konservativ, stabil).

---

## Sicherheitsarchitektur

### Hard-Block (nie automatisch)

Der `SafePlanner` blockt Aktionen, die folgende Systempfade betreffen – unabhängig vom Nutzerbefehl:

```
\windows\system32\
\windows\syswow64\
\windows\winsxs\
\microsoft\windows defender\
\microsoft\windows\windowsupdate
\microsoft\windows\updateorchestrator
\microsoft\windows\waasmedic
\microsoft\windows\systemrestore
```

Zusätzlich werden Einträge aus `rules/task-whitelist.txt` und eigene Tabula-Dateipfade geschützt.

### High-Risk-Doppelbestätigung

Beim Klick auf „JETZT AUSFÜHREN" mit ≥ 1 High/Critical-Risk-Aktion im Plan erscheint ein zweiter Bestätigungs-Dialog mit expliziter Warnung.

### Dry-Run / WhatIf

Jede Aktion unterstützt Dry-Run. Das Ergebnis erscheint im Textfeld ohne jede Systemänderung.

### Snapshots & Undo

Vor jeder Live-Ausführung wird ein Registry-Snapshot (`reg export HKLM`) in `tabula_backups/` erstellt.  
Undo: letzten Snapshot via `reg import` zurückspielen.

### Deferred Actions

Aktionen mit Timing `AfterRelogin` oder `AfterRestart` werden **nicht sofort** ausgeführt, sondern in `tabula_deferred_actions.json` serialisiert und beim nächsten Start aufgerufen (geplant, noch nicht automatisiert).

---

## Datenmodell-Übersicht

### `ProgramEntry`

| Feld | Typ | Beschreibung |
|---|---|---|
| `record_type` | Enum | App / Microsoft / Runtime / Driver / Hotfix |
| `category` | Enum | Game / Launcher / Utility / DevTool / … |
| `risk_level` | Enum | Low / Medium / High |
| `estimated_total_bytes` | int | Gesamtgröße (Install + UserData + Cache + Captures) |
| `estimate_confidence` | str | Low / Medium / High |
| `legal_status` | Enum | Free / Paid / Paid/Trial / … |

### `ActionPlan`

| Feld | Typ | Beschreibung |
|---|---|---|
| `action_type` | str | delete / uninstall / powershell / reg / service / task / keep_merged |
| `target` | str | Pfad oder Kommando |
| `risk` | str | Low / Medium / High / Critical |
| `execution_timing` | str | Now / AfterRelogin / AfterRestart |
| `requires_reboot` | bool | Neustart notwendig? |

### `TaskEntry`

| Feld | Typ | Beschreibung |
|---|---|---|
| `is_critical` | bool | Systemkritischer Task? |
| `enabled` | bool | Aktuell aktiv? |
| `status` | str | Ready / Running / Disabled / Unknown |
| `run_as` | str | Ausführungskonto |

---

## Verzeichnisstruktur

```
Tabula/
├── tabula.py               # Einstiegspunkt (setup_logging → TabulaApp)
├── modules.json            # Aktive Modul-Konfiguration
├── gui/
│   ├── main_window.py      # TabulaApp: lädt modules.json, baut Tabs
│   ├── module_api.py       # BaseModule / AppContext
│   ├── module_registry.py  # MODULES-Liste (Registrierung neuer Module hier)
│   └── modules/            # Ein Python-Modul je Tab
│       ├── programs_module.py
│       ├── archive_module.py
│       ├── tasks_services_module.py
│       ├── privacy_module.py
│       ├── duplicates_module.py
│       ├── uwp_ai_module.py
│       ├── micro_apps_module.py
│       ├── plan_execute_module.py
│       └── module_manager_module.py
├── core/
│   ├── models.py           # Alle Datenklassen und Enums
│   ├── planner.py          # SafePlanner (Hard-Block, Deferred, Undo)
│   ├── scanners.py         # Registry-, Task-, Autorun-, Archiv-Scanner
│   ├── execution.py        # Aktions-Ausführung
│   ├── history.py          # Ledger / Aktions-Historie
│   ├── logging_utils.py    # setup_logging, install_global_excepthook
│   └── …
├── micro_apps/
│   └── catalog.json        # Add-on-Katalog
├── ai_companion/
│   ├── tabula_ai_companion_ollama.py
│   └── CUSTOMGPT_SETUP.md
├── profiles/
│   ├── core_only.modules.json
│   └── full.modules.json
├── requirements/
│   ├── base.txt
│   ├── gui.txt             # customtkinter, pillow
│   ├── core.txt            # py7zr, rapidfuzz, python-docx, pymupdf, xxhash
│   ├── windows.txt         # pywin32
│   ├── ai_companion.txt    # ollama
│   ├── build.txt           # pyinstaller, pyyaml
│   └── dev-smoke.txt       # CI-Smoke-Test-Deps
├── scripts/
│   └── smoke_test.py       # 7-Check-Smoke-Test (CI)
└── logs/
    └── tabula.log          # Startup-Log (auto-erstellt)
```

---

## Start & Voraussetzungen

**Python 3.11+** empfohlen. Voller Funktionsumfang erfordert Windows (Admin-Rechte für Registry/Tasks).

```bash
# Mindest-Setup
pip install -r requirements/gui.txt
pip install -r requirements/core.txt

# Optional: Windows-Extras (pywin32 für Registry/Task-Scanner)
pip install -r requirements/windows.txt

# Optional: AI Companion (Ollama)
pip install -r requirements/ai_companion.txt

python tabula.py
```

---

## Aktueller Stand & Roadmap

### Implementiert

- [x] Modulare GUI, alle 9 Module, Dark/Light-Theme
- [x] Programme: Registry-Scan, Klassifikation, Risk-Level, Import-Matching, Größenabschätzung, CSV/Skript-Export
- [x] Archive: Infocheck, Overlap-Erkennung, Passwortlisten-Prüfung
- [x] Tasks & Services: vollständiges Inventar, Kritisch-Markierung, Presets
- [x] Privacy/Autoruns: Triage, Risk-Farb-Codierung, Privacy-Presets
- [x] Duplikate-Finder mit Keep-Best-Scoring
- [x] Micro-App-Katalog (12 Add-ons)
- [x] Plan & Execute: Timing-Queue, Dry-Run, High-Risk-Doppelbestätigung, Undo, Benchmarks
- [x] System-Critical-Blocklist (Hard-Block)
- [x] Profil-System (Core-only / Full)
- [x] Strukturiertes Logging + globaler Exception-Hook
- [x] PyInstaller-Build → `builds/Tabula.exe`
- [x] Smoke-Test in CI

### Noch offen

- [ ] **Windows Live-Tests:** Mind. 10 End-to-End-Szenarien auf echtem Windows-System
- [ ] **Post-Reboot-Verifikation:** deferred Actions automatisch nach Neustart verarbeiten
- [ ] **Relation Engine (Artefakte):** Installiert-vs.-Archiv-Vergleich (Exact/Near/Weak-Matching)
- [ ] **UWP-Modul:** vollständig ausgebaut (Deinstallation, Review-Pflicht)
- [ ] **Import/Export JSON:** stabil dokumentiert und rückwärtskompatibel versioniert
- [ ] **Accessibility / HiDPI:** UI-Skalierung auf hochauflösenden Displays
- [ ] **Signierter Build + MSIX-Installer**
