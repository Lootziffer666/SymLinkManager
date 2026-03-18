# Tabula – Fix my mess. Safely.

Lokales Windows-Tool für Analyse und sichere Aufräum-Pläne.

## Installation
### 1) Vollinstallation (Windows)
```bash
pip install -r requirements.txt
```

### 2) Modulare Installation (einzeln)
```bash
# nur GUI + Basis
pip install -r requirements/gui.txt

# Core-Funktionen (Archive, Duplicate etc.)
pip install -r requirements/core.txt

# AI Companion lokal
pip install -r requirements/ai_companion.txt

# nur auf Windows nötig
pip install -r requirements/windows.txt
```

### 3) Start
```bash
python tabula.py
```


## Barebone GUI + modulare Architektur
Tabula läuft als **Barebone-Host**. Jedes Feature ist ein eigenes GUI-Modul, einzeln aktivierbar über `modules.json` bzw. den Tab **Module**.

## Add-ons / Plugins
Keine Week-Aufteilung mehr in der Oberfläche: Alle Mikro-Tools laufen über die Add-on-Rubrik.

- Katalog: `Tabula/micro_apps/catalog.json`
- Script-Sammlungen:
  - `Addons/maintenance/`
  - `Addons/system_repair/`
  - `Addons/ai_shell/`

## Selbstschutz gegen Selbstlöschung
Der Planner blockiert destruktive Aktionen gegen Tabula-eigene Dateien/Pfade (z. B. `tabula.py`, `modules.json`, `micro_apps/catalog.json`) und markiert sie als geschützt.

## Debugging & Smoke-Test
- Smoke-Test ausführen: `python scripts/smoke_test.py`
- Crash-/Debug-Log: `Tabula/logs/tabula.log`
- GUI-Callback-Crashes werden automatisch protokolliert und mit Hinweisfenster gemeldet.

## AI Companion (ohne Grok-API)
- `Tabula/ai_companion/CUSTOMGPT_SETUP.md` enthält exakte CustomGPT-Anweisungen.
- `Tabula/ai_companion/tabula_ai_companion_ollama.py` bietet eine lokale Ollama-Option.
- CustomGPT läuft mit Upload-Gate: **Kein Upload = kein Service**; Fragebogen startet erst nach Initialexport.
- Companion berücksichtigt Modul-Aktivierungen und erzeugt nur Aktionen für aktivierte Module.

## USP: Optionaler AI Companion
- Tabula-Kern bleibt Offline-Only.
- CustomGPT/Ollama ist optional und liefert Plan-JSONs, die im Tab **Plan & Execute** direkt über `Plan JSON importieren` eingelesen werden können.
