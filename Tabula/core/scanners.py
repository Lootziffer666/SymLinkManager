from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

import psutil

from .models import ArchiveEntry, ProgramEntry, ScheduledTaskEntry, UWPEntry

try:
    import winreg  # type: ignore
except ImportError:  # non-Windows environments
    winreg = None


def normalize_name(name: str) -> str:
    clean = re.sub(r"\((32|64)-bit\)", "", name, flags=re.IGNORECASE)
    clean = re.sub(r"\b(x64|x86|version\s*[\d\.]+)\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"[^\w\s-]", " ", clean)
    return " ".join(clean.lower().split())


def _safe_query_value(key, value_name: str, default: str = "") -> str:
    try:
        return str(winreg.QueryValueEx(key, value_name)[0]).strip()
    except Exception:
        return default


def estimate_real_size(path: str) -> float:
    if not path:
        return 0.0
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return 0.0

    total = 0
    try:
        for root, _, files in os.walk(path):
            for fname in files:
                fpath = Path(root) / fname
                try:
                    total += fpath.stat().st_size
                except OSError:
                    continue
    except Exception:
        return 0.0
    return round(total / (1024 * 1024), 1)


def guess_category(name: str, publisher: str) -> str:
    n = name.lower()
    p = publisher.lower()
    if any(x in n for x in ["steam", "epic", "gog", "ubisoft", "ea app"]):
        return "Launcher"
    if any(x in n for x in ["demo", "playtest", "game", "vr", "rivals"]):
        return "Game"
    if any(x in n for x in ["driver", "nvidia", "amd", "intel"]) or "driver" in p:
        return "Driver"
    if any(x in n for x in ["runtime", "redistributable", "visual c++", ".net"]):
        return "Runtime"
    if "microsoft" in p:
        return "Microsoft"
    return "Application"


def scan_installed_programs() -> list[ProgramEntry]:
    if winreg is None:
        return []

    programs: list[ProgramEntry] = []
    seen: dict[str, ProgramEntry] = {}
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for hive, path in keys:
        try:
            reg_key = winreg.OpenKey(hive, path)
        except OSError:
            continue

        for i in range(winreg.QueryInfoKey(reg_key)[0]):
            try:
                sub_name = winreg.EnumKey(reg_key, i)
                skey = winreg.OpenKey(reg_key, sub_name)
                name = _safe_query_value(skey, "DisplayName")
                if not name:
                    continue

                publisher = _safe_query_value(skey, "Publisher")
                version = _safe_query_value(skey, "DisplayVersion")
                install_dir = _safe_query_value(skey, "InstallLocation")
                uninstall_cmd = _safe_query_value(skey, "UninstallString")

                size_mb = estimate_real_size(install_dir)
                category = guess_category(name, publisher)
                risk = "Critical" if category in {"Driver", "Microsoft"} else "Medium"
                is_system = category in {"Driver", "Microsoft", "Runtime"}

                norm = normalize_name(name)
                if norm in seen:
                    seen[norm].is_duplicate = True
                    continue

                entry = ProgramEntry(
                    name=name,
                    publisher=publisher,
                    version=version,
                    install_dir=install_dir,
                    uninstall_cmd=uninstall_cmd,
                    size_mb=size_mb,
                    confidence="High" if size_mb > 0 else "Low",
                    category=category,
                    risk=risk,
                    is_system=is_system,
                )
                programs.append(entry)
                seen[norm] = entry
            except Exception:
                continue

    programs.sort(key=lambda p: (p.risk, p.name.lower()))
    return programs


def _powershell_json(command: str) -> list[dict]:
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=30,
    )
    out = proc.stdout.strip()
    if not out:
        return []
    try:
        data = json.loads(out)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return []


def scan_uwp_apps() -> list[UWPEntry]:
    rows = _powershell_json(
        "Get-AppxPackage -AllUsers | "
        "Select-Object Name,PackageFullName | ConvertTo-Json -Depth 3"
    )
    apps: list[UWPEntry] = []
    for row in rows:
        name = str(row.get("Name", "")).strip()
        pkg = str(row.get("PackageFullName", "")).strip()
        if not name or not pkg:
            continue
        is_ai = any(k in name.lower() for k in ["copilot", "recall", "widgets", "clipchamp", "bing"])
        apps.append(UWPEntry(name=name, package_fullname=pkg, is_ai_related=is_ai))
    return apps


def scan_archives(folder_path: str) -> list[ArchiveEntry]:
    folder = Path(folder_path)
    if not folder.exists():
        return []

    entries: list[ArchiveEntry] = []
    exts = {".zip", ".rar", ".7z", ".msi", ".exe"}

    for file in folder.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in exts:
            continue

        status = "Unklar"
        pw_needed = False
        if file.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(file) as zf:
                    zf.infolist()
                status = "Öffnbar"
            except RuntimeError:
                status = "Verschlüsselt"
                pw_needed = True
            except Exception:
                status = "Defekt"
        elif file.suffix.lower() == ".7z":
            try:
                import py7zr  # lazy

                with py7zr.SevenZipFile(file, mode="r") as zf:
                    zf.getnames()
                status = "Öffnbar"
            except Exception as exc:
                if "password" in str(exc).lower():
                    status = "Verschlüsselt"
                    pw_needed = True
                else:
                    status = "Defekt"
        else:
            status = "Gefunden"

        entries.append(
            ArchiveEntry(
                path=str(file),
                file_type=file.suffix.lower().replace(".", "").upper(),
                size_mb=round(file.stat().st_size / (1024 * 1024), 1),
                status=status,
                overlap_installed=any(x in file.name.lower() for x in ["setup", "installer", "update"]),
                password_needed=pw_needed,
            )
        )

    return entries


def scan_scheduled_tasks() -> list[ScheduledTaskEntry]:
    rows = _powershell_json(
        "Get-ScheduledTask | Select-Object TaskName,TaskPath,State | ConvertTo-Json -Depth 3"
    )
    tasks: list[ScheduledTaskEntry] = []
    for row in rows:
        name = str(row.get("TaskName", "")).strip()
        path = str(row.get("TaskPath", "")).strip()
        state = str(row.get("State", "Unknown"))
        if not name:
            continue
        critical = "\\microsoft\\windows\\" in path.lower()
        tasks.append(
            ScheduledTaskEntry(
                name=name,
                path=path,
                enabled=state.lower() != "disabled",
                state=state,
                is_critical=critical,
                orphaned=False,
                risk="Critical" if critical else "Medium",
            )
        )
    return tasks


def benchmark_snapshot() -> dict:
    return {
        "ram_percent": psutil.virtual_memory().percent,
        "cpu_percent": psutil.cpu_percent(interval=1.0),
        "disk_free_gb": round(psutil.disk_usage("C:\\").free / (1024**3), 1),
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
    }
