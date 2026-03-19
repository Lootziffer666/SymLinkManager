# Tabula Rasa – Purge safely. Reclaim space.

Tabula Rasa ist das destruktivere Schwester-Tool zu Tabula – klar getrennt, aber mit ähnlicher Sicherheits-Disziplin.

## Fokus

- **Scan:** Purge-Kandidaten wie Temp, Cache, Shader-Caches und Review-Kandidaten erkennen
- **Plan:** Safe Mode (RecycleBinPreferred) vs. Aggressive Mode (PermanentDelete)
- **Run:** Dry-run / Safe / Aggressive Ablauf mit Ledger
- **History:** Exportierbare Historie plus „Was würde ich heute löschen?“

## Besondere PRD-Anpassungen

- zwei explizite Delete-Modi: **Safe** und **Aggressive**
- **Orphaned App Data** als eigene, review-pflichtige Kategorie
- exportierbare Historie mit Tages-Rückblick

## Start

```bash
pip install -r ../Tabula/requirements.txt
python tabula_rasa.py
```
