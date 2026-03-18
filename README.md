# SymLinkManager — Regelwerk/Blueprint

Dieses Repository enthält aktuell das technische Regelwerk v1.1 als Umsetzungsbasis sowie den Prototyp **Tabula**.

## Inhalte

- `docs/regelwerk_v1.1.md` — Feinkonzept inkl. Datenmodell, Safety-Regeln, Workflows und MVP-Iterationen.
- `rules/whitelist.txt` — Startwerte für Schutzregeln.
- `rules/blacklist.txt` — Startwerte für Markierungsregeln.
- `rules/task-whitelist.txt` — geschützte Task-Muster (kritische Systemaufgaben).
- `rules/task-blacklist.txt` — Triage-Kandidaten für unkritische Updater-/Helper-Tasks.
- `schemas/*.schema.json` — JSON-Schemas für zentrale Datenobjekte.
- `claude.md` — ergebnisoffener Anforderungskatalog (was das Tool können soll), ohne technische Vorgehensvorgaben.
- `Tabula/` — modulares Barebone-Desktoptool (GUI-Host + einzeln zuschaltbare Module).
- `Tabula/micro_apps/catalog.json` — zentrale Übersicht aller Mikro-Apps (Add-ons/Plugins-Rubrik).
- `Addons/` — Standalone-Script-Sammlungen (`maintenance`, `system_repair`, `ai_shell`).

## Tabula (Kurz)
- Modulkonfiguration über `Tabula/modules.json`
- Modul-Host in `Tabula/gui/main_window.py`
- GUI-Module in `Tabula/gui/modules/`
- Requirements als Overview + pro Modul in `Tabula/requirements*.txt` und `Tabula/requirements/*.txt`
- Smoke-Test in `Tabula/scripts/smoke_test.py`
- AI Companion Hinweise in `Tabula/ai_companion/CUSTOMGPT_SETUP.md`

