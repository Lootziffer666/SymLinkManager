from __future__ import annotations

import os
import shutil
from pathlib import Path

RECALL_PATH = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Recall"))


def scan_recall_storage(execute: bool = False) -> None:
    if not RECALL_PATH.exists():
        print("Recall-Pfad nicht vorhanden.")
        return
    size_gb = sum(f.stat().st_size for f in RECALL_PATH.rglob("*") if f.is_file()) / (1024**3)
    print(f"Recall belegt: {size_gb:.2f} GB")
    if execute:
        shutil.rmtree(RECALL_PATH, ignore_errors=True)
        print("✅ Recall-Speicher entfernt")
    else:
        print(f"[PREVIEW] Würde löschen: {RECALL_PATH}")


if __name__ == "__main__":
    scan_recall_storage(execute=input("Löschen? (j/n): ").lower() == "j")
