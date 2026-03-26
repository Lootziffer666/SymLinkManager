# Tabula Suite

> **Lokale Windows-Desktop-Suite für sicheres Aufräumen, Storage-Analyse und System-Triage.**  
> Zwei eigenständige, aber konzeptionell verwandte Tools – konservativ by default, transparent in jeder Aktion.

---

## Inhalt

- [Tabula — Map. Move. Link.](#tabula--map-move-link)
- [TabulaRasa — Purge safely. Reclaim space.](#tabularasa--purge-safely-reclaim-space)
- [Architektur](#architektur)
- [Sicherheitsphilosophie](#sicherheitsphilosophie)
- [Voraussetzungen & Start](#voraussetzungen--start)
- [Als Executable bauen](#als-executable-bauen)
- [Aktueller Stand & offene Punkte](#aktueller-stand--offene-punkte)

---

## Tabula — Map. Move. Link.

**Fokus:** Storage Intelligence + sichere Relocation-Planung

Tabula hilft dabei, ein über Jahre gewachsenes Windows-System wieder überschaubar zu machen – ohne blinde Auto-Fixes. Der Ansatz ist: erst verstehen, dann planen, dann (optional) ausführen.

### Module (einzeln zuschaltbar)

| Modul | Funktion |
|---|---|
| **Programme** | Win32-Programme aus allen relevanten Registry-Quellen (HKLM/HKCU + WOW6432Node) inventarisieren, normalisieren, deduplizieren, klassifizieren (App/Runtime/Treiber/Hotfix/Microsoft) und nach Risiko filtern. Import-Matching gegen eigene Textlisten (tolerant gegen Versions-/Bitness-Suffixe). Uninstall-Skript-Export + CSV. |
| **Archive** | ZIP/RAR/7z/MSI/EXE erfassen und einordnen (was ist das ungefähr?), ohne blindes Ausführen. Erkennt, ob ein Artefakt vermutlich bereits installiert ist oder mit installierten Programmen überlappt. Optionale Passwortlistenprüfung für verschlüsselte Archive (nur eigene Liste, kein Brute-Force). |
| **UWP & AI** | UWP-App-Inventar; AI-Companion-Einstellungen (Ollama / CustomGPT). |
| **Tasks & Services** | Geplante Aufgaben vollständig inventarisieren, nach Risiko/Quelle klassifizieren (SystemCritical / Security / Update / Maintenance / Telemetry / AppSupport), verwaiste/defekte Tasks markieren. Sichere Disable-/Delete-Vorschläge mit Snapshot. |
| **Privacy** | Registry-Autostart- und Hook-Bereiche (Run/RunOnce/Winlogon/AppInit/Policy-Keys) prüfen, auffällige Einträge markieren, Policy-basierte Sperren sichtbar machen. |
| **Duplikate** | Datei-Duplikate mit Keep-Best-Scoring finden; DOCX/TXT-Merge-Unterstützung. |
| **Micro-Apps / Add-ons** | Zentraler Katalog mit 12 vorproduzierten Add-ons (Snapshot & Restore, Safe ARP Cleaner, Context Menu Cleaner, OneDrive Repair Guard, Explorer Shell Guard, Recall Storage Wiper, NPU Guard, Winget Source Fix u. a.). |
| **Plan & Execute** | Alle geplanten Aktionen in einer Queue sammeln. Timing pro Aktion: `Jetzt` / `Nach Relogin` / `Nach Neustart`. Dry-Run / WhatIf-Modus. High-Risk-Doppelbestätigung. Ledger-Export. |
| **Module Manager** | Module einzeln aktivieren/deaktivieren; Profil laden (Core-only / Full). |

### Weitere Fähigkeiten

- **Größenabschätzung:** realistischere Größe als Windows-Standard (InstallLocation + Nutzerdaten/Screenshots/Caches), mit Confidence-Feld.
- **Profil-System:** `core_only.modules.json` (stabiler Alltagsbetrieb) vs. `full.modules.json` (alle Features inkl. Nightly-Add-ons).
- **Strukturiertes Logging:** Startup-Logging in `Tabula/logs/tabula.log`, globaler Exception-Hook.
- **AI Companion:** Ollama-Backend oder CustomGPT-Integration für kontextbasierte Analyse-Hilfe.

```bash
python Tabula/tabula.py
```

---

## TabulaRasa — Purge safely. Reclaim space.

**Fokus:** Purge-orientierte Cleanup-Workflows mit expliziten Lösch-Modi

TabulaRasa ist das destruktivere Schwester-Tool – klar getrennt von Tabula, aber mit gleicher Sicherheitsdisziplin.

### Modi

| Modus | Verhalten |
|---|---|
| **Dry-Run** | Nur Vorschau, keine Änderung |
| **Safe** | RecycleBin-bevorzugt (wiederherstellbar) |
| **Aggressive** | PermanentDelete nach expliziter Bestätigung |

### Scan-Kategorien

- Temp- und Cache-Ordner
- Shader-Caches
- **Orphaned App Data** – eigene, review-pflichtige Kategorie (kein Auto-Delete)
- Erweiterbar durch Regel-Dateien

### Weitere Fähigkeiten

- Exportierbare Ledger-Historie
- „Was würde ich heute löschen?"-Tagesrückblick
- Backups vor destruktiven Aktionen
- Logging in `TabulaRasa/logs/tabula_rasa.log`

```bash
python TabulaRasa/tabula_rasa.py
```

---

## Architektur

```
Tabula Suite
├── Tabula/                      # Map. Move. Link.
│   ├── tabula.py                # Einstiegspunkt
│   ├── gui/
│   │   ├── main_window.py       # Lädt modules.json, baut Tabs dynamisch
│   │   ├── module_api.py        # BaseModule / AppContext API
│   │   ├── module_registry.py   # Modul-Registrierung
│   │   └── modules/             # Ein Python-Modul je GUI-Tab
│   ├── core/                    # Planner, Scanner, Execution, History, Logging …
│   ├── micro_apps/catalog.json  # Add-on-Katalog
│   ├── ai_companion/            # Ollama / CustomGPT Integration
│   ├── profiles/                # core_only.modules.json / full.modules.json
│   ├── modules.json             # Aktive Modul-Konfiguration
│   └── requirements/            # Aufgeteilte Dependency-Gruppen
│
├── TabulaRasa/                  # Purge safely. Reclaim space.
│   ├── tabula_rasa.py           # Einstiegspunkt
│   ├── gui/                     # Eigene TabulaRasa-GUI
│   ├── scanners/                # Purge-Scanner + Regelwerk
│   ├── shared/                  # Gemeinsame Hilfsmittel
│   └── backups/                 # Backup-Snapshots
│
├── Addons/                      # Micro-App-Skripte (maintenance / system_repair / ai_shell)
├── rules/                       # Whitelist/Blacklist-Regelsätze
├── schemas/                     # JSON-Schemas für Datenmodelle
├── docs/                        # Regelwerk, Playbooks, Checklisten
└── build_executables.py         # PyInstaller-Build für beide Apps
```

Tabula nutzt ein **dynamisches Modul-System**: `modules.json` steuert, welche Tabs geladen werden. Jedes Modul implementiert `BaseModule` und erhält einen `AppContext`. Neue Module können hinzugefügt werden, ohne den Host anzufassen.

---

## Sicherheitsphilosophie

- **Nie blind ausführen.** Jede Aktion wird zuerst als Plan/Vorschau gezeigt.
- **Dry-Run/WhatIf-Modus** für alle destruktiven Flows.
- **Hard-Block für kritische Targets:** System32, Defender, WindowsApp, WindowsUpdate, SystemRestore und Einträge aus `rules/task-whitelist.txt` werden nie automatisch angefasst.
- **High-Risk-Doppelbestätigung:** Eine zweite Bestätigung ist Pflicht, bevor High/Critical-Risiko-Aktionen ausgeführt werden.
- **Passwortlisten** werden niemals im Klartext geloggt.
- **Kein Piracy-/Crack-Support**, kein Voll-Brute-Force, keine stille Telemetrie.
- **Snapshots** vor und nach Änderungen; Undo soweit technisch möglich.
- **Timing-Queue:** Aktionen können auf „Nach Relogin" oder „Nach Neustart" verschoben werden; deferred Actions werden in `tabula_deferred_actions.json` serialisiert.

---

## Voraussetzungen & Start

**Python** 3.11+ empfohlen. Auf Windows werden für den vollen Funktionsumfang Admin-Rechte benötigt.

### Tabula

```bash
pip install -r Tabula/requirements/gui.txt
pip install -r Tabula/requirements/core.txt
# Optional: Windows-spezifische Extras
pip install -r Tabula/requirements/windows.txt
python Tabula/tabula.py
```

### TabulaRasa

TabulaRasa teilt die Dependency-Dateien aus `Tabula/requirements/`:

```bash
pip install -r Tabula/requirements/gui.txt
pip install -r Tabula/requirements/core.txt
python TabulaRasa/tabula_rasa.py
```

---

## Als Executable bauen

Beide Anwendungen können mit PyInstaller in eigenständige Windows-Executables kompiliert werden.

### Voraussetzungen

```bash
pip install -r Tabula/requirements/build.txt
```

### Beide bauen

```bash
python build_executables.py
```

### Einzeln bauen

```bash
python build_executables.py tabula
python build_executables.py tabularasa
```

### Single-File `.exe` (langsamer Start, einfacher zu verteilen)

```bash
python build_executables.py --onefile
```

Die fertigen Executables liegen unter `builds/Tabula.exe` bzw. `builds/TabulaRasa.exe`.  
CI baut auf `windows-latest` und stellt sie als GitHub-Actions-Artifacts bereit.

---

## Aktueller Stand & offene Punkte

### Implementiert (v0.2 / Unreleased)

- [x] Modulare Tabula-GUI mit 9 Tabs (einzeln zuschaltbar)
- [x] Programme-Modul: Registry-Scan, Normalisierung, Klassifikation, Risk-Level, CSV/Skript-Export
- [x] Import-Matching gegen eigene Textlisten (Exact / Fuzzy / Weak)
- [x] Größenabschätzung mit Confidence-Feld
- [x] Archive-Modul: Infocheck, Overlap-Erkennung, Passwortlisten-Prüfung
- [x] Tasks & Services: vollständiges Inventar, Health-Status, Klassifikation
- [x] Privacy-Modul: Autorun- und Registry-Hook-Triage
- [x] Duplikate-Finder mit Keep-Best-Scoring
- [x] Micro-App-Katalog mit 12 Add-ons
- [x] Plan & Execute: Timing-Queue, Dry-Run, High-Risk-Doppelbestätigung
- [x] System-Critical-Blocklist (Hard-Block)
- [x] AI Companion (Ollama / CustomGPT)
- [x] Profil-System (Core-only / Full)
- [x] TabulaRasa: Safe / Aggressive / DryRun-Modi, Ledger, Orphaned-App-Data-Kategorie
- [x] Strukturiertes Logging + globaler Exception-Hook in beiden Apps
- [x] PyInstaller-Build + CI (GitHub Actions)
- [x] Smoke-Test in CI

### Noch offen / Roadmap

- [ ] **Windows Live-Test:** Mind. 10 End-to-End-Testfälle auf echtem Windows-System
- [ ] **Regressionsliste** für kritische Flows (Undo, Reboot-Queue, Restore)
- [ ] **Post-Reboot-Verifikation:** Auto-Verify + Differenzbericht nach deferred Actions
- [ ] **Relation Engine (Artefakte):** Installiert-vs.-Archiv-Vergleich mit Exact/Near/Weak-Matching
- [ ] **UWP-Modul** vollständig ausgebaut
- [ ] **Signierter Release-Build** (Code-Signing-Zertifikat)
- [ ] **Installierbarer Paketweg** (MSIX oder Inno Setup)
- [ ] **Import/Export JSON** stabil und rückwärtskompatibel dokumentiert
- [ ] **Einheitliche Action-IDs** im Ledger (für lückenlose Nachvollziehbarkeit)
- [ ] **TabulaRasa:** Scanner-Regelwerk erweitern (Shader-Caches, Browser-Caches, WinSxS)
- [ ] **Accessibility / HiDPI:** UI-Skalierung auf hochauflösenden Displays

### Bekannte Einschränkungen

- **Tabula** erfordert für den vollen Funktionsumfang Windows + Admin-Rechte. Auf Linux/macOS startet die GUI (customtkinter), aber Registry-Scan, Task-Scheduler-Analyse und Autorun-Triage sind **nicht verfügbar**.
- **TabulaRasa** startet auf Linux/macOS, aber Windows-spezifische Purge-Kategorien (Shader-Caches, AppData-Pfade) werden **nicht erkannt und sind nicht verfügbar**.
- Archive-Passwortprüfung unterstützt derzeit nur ZIP nativ; RAR und 7z benötigen die entsprechenden Python-Bibliotheken (`py7zr`, `rarfile`).
- Micro-App-Add-ons sind als „Nightly/Pre-Production" markiert und noch nicht vollständig getestet.

---

## Lizenz

Siehe [LICENSE](LICENSE).
