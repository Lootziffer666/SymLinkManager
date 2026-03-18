# claude.md — Produktauftrag für Claude Code (ergebnisoffen)

> Dieses Dokument beschreibt **nur** was das Tool können soll.  
> **Wie** Claude Code es technisch umsetzt (Architektur, Stack, Reihenfolge, interne Designs), entscheidet Claude Code selbst.

---

## 1) Zielbild

Baue ein lokales Windows-Desktoptool, das ein über Jahre gewachsenes System wieder wartbar macht, ohne Neuinstallation.

Das Tool soll helfen bei:

1. chaotischen installierten Programmen,
2. unübersichtlichen Archiv-/Installer-Beständen,
3. zu vielen geplanten Aufgaben,
4. problematischen Autostarts/Registry-Einträgen,
5. riskanten Aufräumaktionen (durch sichere Planung, Vorschau, Rücknahmefähigkeit).

---

## 2) Muss-Funktionen

### 2.1 Installierte Programme (Win32)

- Programme aus den relevanten Uninstall-Quellen erkennen.
- Dubletten/uneinheitliche Anzeigenamen sinnvoll zusammenführen.
- Kategorien und Risikostufen vergeben (z. B. App, Runtime, Treiber, Hotfix, Microsoft, Launcher, Game, Utility …).
- Filter/Presets anbieten (z. B. „nur Games + Launcher“, „High Risk ausblenden“).
- Eigene Import-Textlisten matchen können (tolerant gegen Bitness-/Versionszusätze).
- Uninstall-Skripte erzeugen (prüfbar), bevor etwas ausgeführt wird.
- CSV/JSON-Export bereitstellen.

### 2.2 Größen- und Relevanzhilfe

- realistischere Größenabschätzung als die Windows-Standardangabe anbieten,
- inklusive Installationsordner und – soweit plausibel – Nutzerdaten/Screenshots/Caches,
- mit Confidence-/Hinweisfeld, damit unsichere Schätzungen erkennbar sind.

### 2.3 Archive-/Installer-Infocheck

- ZIP/RAR/7z/MSI/EXE erfassen und kurz einordnen („was ist das ungefähr?“), ohne blindes Ausführen.
- Erkennen, ob etwas vermutlich bereits installiert ist oder funktional überlappt.
- Passwortlistenprüfung für verschlüsselte Archive unterstützen (nur mit nutzereigener Passwortliste).
- Ergebnisse vorsortierbar machen (z. B. „öffnbar“, „kein Treffer“, „defekt“, „unklar“).

### 2.4 Task Scheduler Analyse

- Geplante Aufgaben vollständig inventarisieren.
- Verständlich markieren, was systemkritisch vs. optional/prüfenswert ist.
- Verwaiste/defekte/unverfügbare Aufgaben hervorheben.
- Sichere Vorschläge machen, ohne kritische Systemfunktionen pauschal abzuschalten.

### 2.5 Autoruns/Registry Analyse

- Relevante Autostart- und Hook-Bereiche prüfen.
- Auffällige oder potenziell riskante Einträge markieren.
- Sicherheits-/Policy-relevante Einträge sichtbar machen (z. B. Einträge, die Admin-Tools blockieren).

### 2.6 Sichere Ausführung

- Jede Änderung zuerst als Plan/Vorschau zeigen.
- Dry-Run/WhatIf-Modus.
- Logging/Snapshots vor und nach Änderungen.
- Rücknahme-/Undo-Möglichkeit, soweit technisch machbar.
- Aktionen einplanbar für „jetzt“, „nach Relogin“, „nach Neustart“.

---

## 3) Sicherheits- und Compliance-Anforderungen

- Keine Piracy-/Crack-/Keygen-Unterstützung.
- Keine stillen, nicht nachvollziehbaren Auto-Fixes.
- Keine pauschale Entfernung kritischer Systemkomponenten ohne klare Nutzerentscheidung und Warnung.
- Keine unnötige Cloudpflicht/Telemetrie.
- Sensible Daten (z. B. Passwortlisten) schützen und nicht im Klartext in Logs ausgeben.

---

## 4) UX-Anforderungen

- Die Oberfläche soll auch bei großen Datenmengen nutzbar bleiben.
- Risiko und Auswirkung jeder Aktion müssen verständlich sein.
- Vorschläge sind hilfreich, aber nicht bevormundend.
- Standardverhalten konservativ/sicher.
- Vor kritischen Schritten klare Warnung und Bestätigung.

---

## 5) Vergleichbarkeit / Transparenz

Am Ende soll Claude Code liefern:

1. lauffähiges Ergebnis,
2. nachvollziehbare Dokumentation der Entscheidungen,
3. Test-/Validierungsnachweise,
4. offene Punkte/Risiken,
5. klare Anleitung, wie ein Nutzer sicher mit dem Tool arbeitet.

---

## 6) Freiheitsklausel für Claude Code

Claude Code darf **frei entscheiden**:
- welche Architektur,
- welche interne Modulaufteilung,
- welche Implementierungsreihenfolge,
- welche UI-Technik,
- welche Heuristiken im Detail,

solange die oben genannten Fähigkeiten und Sicherheitsanforderungen erfüllt werden.
