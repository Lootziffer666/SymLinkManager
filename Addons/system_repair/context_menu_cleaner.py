from __future__ import annotations

import subprocess
import winreg

BLOCKED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Shell Extensions\Blocked"
KNOWN = {
    "Copilot": "CB3B0003-8088-4EDE-8769-8B354AB2FF8C",
    "Clipchamp": "8BCF599D-B158-450F-B4C2-430932F2AF2F",
}


def list_blocked() -> None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, BLOCKED_KEY)
        i = 0
        while True:
            name, value, _ = winreg.EnumValue(key, i)
            print(f"Blocked {name}: {value}")
            i += 1
    except OSError:
        print("Keine oder Ende der Blocked-Einträge.")


def safe_block(guid: str, label: str, execute: bool = False) -> None:
    cmd = f'reg add "HKCU\\{BLOCKED_KEY}" /v "{{{guid}}}" /t REG_SZ /d "{label}" /f'
    if execute:
        subprocess.run(cmd, shell=True, check=False)
        print("✅", label, "blockiert")
    else:
        print("[PREVIEW]", cmd)


if __name__ == "__main__":
    live = input("Echte Änderungen? (j/n): ").lower() == "j"
    for name, guid in KNOWN.items():
        if input(f"{name} blockieren? (j/n): ").lower() == "j":
            safe_block(guid, name, execute=live)
    list_blocked()
