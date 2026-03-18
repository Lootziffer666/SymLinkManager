from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path

BACKUP_DIR = Path("TrueUndo_Backups")
BACKUP_DIR.mkdir(exist_ok=True)


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=False, capture_output=True, text=True)


def create_snapshot(description: str) -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    name = description.strip().replace(" ", "_") or "snapshot"
    backup = BACKUP_DIR / f"{ts}_{name}"
    backup.mkdir(exist_ok=True)

    _run(["reg", "export", "HKLM", str(backup / "HKLM.reg"), "/y"])
    _run(["reg", "export", "HKCU", str(backup / "HKCU.reg"), "/y"])
    _run([
        "powershell",
        "-NoProfile",
        "-Command",
        f"Get-AppxPackage -AllUsers | Export-Clixml -Path '{backup / 'Appx.xml'}'",
    ])
    _run([
        "powershell",
        "-NoProfile",
        "-Command",
        f"Get-Service | Export-Clixml -Path '{backup / 'Services.xml'}'",
    ])
    print(f"✅ SNAPSHOT ERSTELLT: {backup}")
    return backup


def restore_snapshot(backup_folder: Path) -> None:
    if not backup_folder.exists():
        print("❌ Backup nicht gefunden")
        return
    _run(["reg", "import", str(backup_folder / "HKLM.reg")])
    _run(["reg", "import", str(backup_folder / "HKCU.reg")])
    print(f"✅ RESTORE ABGESCHLOSSEN: {backup_folder}")


def list_backups() -> list[Path]:
    return sorted(BACKUP_DIR.glob("*"))


if __name__ == "__main__":
    mode = input("1=Snapshot 2=Restore 3=Liste: ").strip()
    if mode == "1":
        create_snapshot(input("Beschreibung: "))
    elif mode == "2":
        entries = list_backups()
        for i, p in enumerate(entries, 1):
            print(f"{i}: {p}")
        idx = int(input("Nummer: ")) - 1
        restore_snapshot(entries[idx])
    else:
        for p in list_backups():
            print(p)
