# Tabula Suite – Changelog

All notable changes are documented in this file.  
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added

#### Tabula (Map. Move. Link.)
- **Import text-list matching** – Programs module now accepts a user-supplied `.txt` file (one program name per line) and matches entries tolerantly against installed Win32 programs, ignoring bitness/version suffixes. Matched rows are highlighted and filterable via "Nur Import-Matches".
- **Execution timing** – Every action in the plan now carries an `execution_timing` field (`Now` / `AfterRelogin` / `AfterRestart`). The Plan & Execute module exposes a dropdown to set the timing for all queued actions. Deferred actions are serialised to `tabula_deferred_actions.json` and reported in the output log.
- **High-Risk double-confirm** – Clicking "JETZT AUSFÜHREN" with High/Critical risk actions in the plan now triggers a second confirmation dialog before proceeding.
- **System-critical blocklist** – `SafePlanner` now hard-blocks targets matching Windows System32, Defender, WindowsUpdate, SystemRestore, and other critical paths. The `rules/task-whitelist.txt` entries are also respected.
- **Archive password-list check** – Archive module accepts an optional user-provided password list file. ZIP archives are checked for password protection; if a list is supplied each password is tried in-memory (never logged). Result ("Password matched" / "No match") is shown in the Status column.
- **Startup logging** – `tabula.py` now calls `setup_logging()` and `install_global_excepthook()` on launch, writing structured logs to `Tabula/logs/tabula.log`. `TabulaRasa` has equivalent logging in `tabula_rasa.py`.

#### Tabula Rasa (Purge safely. Reclaim space.)
- No structural changes; logging wired at startup.

### Changed
- `ActionPlan.model_dump()` now includes `execution_timing` in its output, making plan exports backward-compatible (field defaults to `"Now"` when absent on import).
- Archive scan no longer calls `scan_installed_programs()` once per file; it caches the name list upfront, making large folder scans significantly faster.

---

## [0.2.0] – 2025-03 (prior branch: tabula-build)

### Added
- Tabula modular GUI with nine individually togglable modules (Programs, Archive, UWP & AI, Tasks & Services, Privacy, Duplicates, Add-ons, Plan & Execute, Module Manager).
- Tabula Rasa purge-focused companion tool with Safe / Aggressive / DryRun modes and full ledger history.
- Scheduled-task full inventory with critical-task detection.
- Autorun / Registry scanner with suspicious-pattern highlighting.
- Smart duplicate finder with Keep-Best scoring and DOCX/TXT merge.
- AI companion module (Ollama / CustomGPT integration).
- Micro-App Add-on catalog (`micro_apps/catalog.json`) with 12 pre-production add-ons.
- Profile system (`core_only.modules.json` / `full.modules.json`).

---

## [0.1.0] – Initial scaffolding

- Repository created with `Tabula/` and `TabulaRasa/` skeleton.
- Shared schemas, rules, and documentation layout established.
