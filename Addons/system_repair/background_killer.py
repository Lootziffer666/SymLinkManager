from __future__ import annotations

import psutil
import subprocess

TARGET_PROCS = ["CrossDeviceResume.exe"]
TARGET_SERVICES = ["W32Time", "DiagTrack"]


def scan_and_stop(execute: bool = False) -> None:
    for proc in psutil.process_iter(["name", "pid"]):
        name = (proc.info.get("name") or "").lower()
        if any(t.lower() == name for t in [p.lower() for p in TARGET_PROCS]):
            if execute:
                proc.kill()
                print("✅ Prozess gestoppt:", proc.info)
            else:
                print("[PREVIEW] Würde Prozess stoppen:", proc.info)

    for svc in TARGET_SERVICES:
        cmd = f'Set-Service -Name "{svc}" -StartupType Manual'
        if execute:
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=False)
            print("✅ Service angepasst:", svc)
        else:
            print("[PREVIEW]", cmd)


if __name__ == "__main__":
    scan_and_stop(execute=input("Echte Ausführung? (j/n): ").lower() == "j")
