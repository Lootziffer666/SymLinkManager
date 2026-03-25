# Tabula Suite

Die Codebasis ist jetzt entlang der Produktidentität aufgeteilt:

## Tabula
**Map. Move. Link.**

Tabula ist das konservative Tool für Storage-Analyse, sichere Relocation-Planung und Link-Management.
Start:

```bash
python Tabula/tabula.py
```

## Tabula Rasa
**Purge safely. Reclaim space.**

Tabula Rasa ist das Cleanup-Schwester-Tool für purge-orientierte Workflows mit Safe/Aggressive-Modi, Review-Zwang für Orphaned App Data und exportierbarem Ledger.
Start:

```bash
python TabulaRasa/tabula_rasa.py
```

## Als Executable bauen

Beide Anwendungen können mit PyInstaller in eigenständige Executables kompiliert werden.

### Voraussetzungen

```bash
pip install -r Tabula/requirements.txt
pip install -r Tabula/requirements/build.txt
```

### Beide bauen (Verzeichnis-Bundle)

```bash
python build_executables.py
```

### Einzeln bauen

```bash
python build_executables.py tabula
python build_executables.py tabularasa
```

### Einzelne .exe (langsamer Start, einfacher zu verteilen)

```bash
python build_executables.py --onefile
```

Die Ergebnisse liegen unter `dist/Tabula/` bzw. `dist/TabulaRasa/`.
