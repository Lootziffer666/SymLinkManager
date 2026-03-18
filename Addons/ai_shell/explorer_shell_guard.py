from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path


BACKUP_ROOT = Path("ShellGuard_Backups")
BACKUP_ROOT.mkdir(exist_ok=True)


def snapshot_shell() -> Path:
    ts = BACKUP_ROOT / dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    ts.mkdir(exist_ok=True)
    subprocess.run(["reg", "export", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer", str(ts / "Explorer.reg"), "/y"], check=False)
    print("✅ Shell-Snapshot:", ts)
    return ts


def safe_reset_context(execute: bool = False) -> None:
    cmds = ["taskkill /f /im explorer.exe", "start explorer.exe"]
    for c in cmds:
        if execute:
            subprocess.run(c, shell=True, check=False)
            print("[EXEC]", c)
        else:
            print("[PREVIEW]", c)


if __name__ == "__main__":
    choice = input("1=Snapshot 2=Context Reset: ")
    if choice == "1":
        snapshot_shell()
    else:
        safe_reset_context(execute=input("Echt ausführen? (j/n): ").lower() == "j")
