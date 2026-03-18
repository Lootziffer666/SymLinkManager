from __future__ import annotations

import subprocess
import winreg
from pathlib import Path

ROOTS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
]


def _safe_val(key, name: str) -> str:
    try:
        return str(winreg.QueryValueEx(key, name)[0])
    except Exception:
        return ""


def scan_orphaned_arp() -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for hive, path in ROOTS:
        try:
            k = winreg.OpenKey(hive, path)
        except OSError:
            continue
        for i in range(winreg.QueryInfoKey(k)[0]):
            try:
                sub = winreg.EnumKey(k, i)
                sk = winreg.OpenKey(k, sub)
                name = _safe_val(sk, "DisplayName") or sub
                uninstall = _safe_val(sk, "UninstallString")
                if not uninstall:
                    continue
                exe = uninstall.split('"')[1] if '"' in uninstall else uninstall.split()[0]
                if exe and not Path(exe).exists():
                    out.append((name, path, sub))
            except Exception:
                continue
    return out


def clean_safe(orphaned: list[tuple[str, str, str]], execute: bool = False) -> None:
    for name, base, sub in orphaned:
        cmd = ["reg", "delete", f"HKLM\\{base}\\{sub}", "/f"]
        if not execute:
            print("[PREVIEW]", name, "->", " ".join(cmd))
        else:
            subprocess.run(cmd, check=False)
            print("✅ Gelöscht:", name)


if __name__ == "__main__":
    items = scan_orphaned_arp()
    print(f"Gefunden: {len(items)} orphaned ARP-Einträge")
    clean_safe(items, execute=input("Echt löschen? (j/n): ").lower() == "j")
