from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path

BACKUP_DIR = Path("UpdateGuard_Backups")
BACKUP_DIR.mkdir(exist_ok=True)


def create_update_snapshot() -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / ts
    backup.mkdir(exist_ok=True)
    subprocess.run(["reg", "export", "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate", str(backup / "WindowsUpdate.reg"), "/y"], check=False)
    subprocess.run(["powershell", "-NoProfile", "-Command", f"Get-Service wuauserv,bits,cryptsvc | Out-File -FilePath '{backup / 'services.txt'}'"], check=False)
    print("✅ Snapshot:", backup)
    return backup


def safe_update_reset(execute: bool = False) -> None:
    cmds = [
        'Stop-Service -Name wuauserv -Force',
        'Stop-Service -Name bits -Force',
        'Rename-Item -Path "$env:SystemRoot\\SoftwareDistribution" -NewName "SoftwareDistribution.old" -ErrorAction SilentlyContinue',
        'Start-Service -Name bits',
        'Start-Service -Name wuauserv',
    ]
    for c in cmds:
        if execute:
            subprocess.run(["powershell", "-NoProfile", "-Command", c], check=False)
            print("[EXEC]", c)
        else:
            print("[PREVIEW]", c)


if __name__ == "__main__":
    choice = input("1=Snapshot 2=Reset(Preview): ")
    if choice == "1":
        create_update_snapshot()
    else:
        safe_update_reset(execute=input("Echt ausführen? (j/n): ").lower() == "j")
