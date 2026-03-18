from __future__ import annotations

import subprocess


def safe_repair_onedrive(execute: bool = False) -> None:
    cmds = [
        'Get-AppxPackage Microsoft.OneDrive | ForEach-Object { Add-AppxPackage -Register "$($_.InstallLocation)\\AppXManifest.xml" -DisableDevelopmentMode }',
        '$env:SystemRoot + "\\System32\\OneDriveSetup.exe"',
    ]
    for c in cmds:
        if execute:
            subprocess.run(["powershell", "-NoProfile", "-Command", c], check=False)
            print("[EXEC]", c)
        else:
            print("[PREVIEW]", c)


if __name__ == "__main__":
    safe_repair_onedrive(execute=input("Echte Reparatur? (j/n): ").lower() == "j")
