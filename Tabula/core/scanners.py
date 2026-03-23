from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from .models import (
    ArchiveItem,
    AutorunEntry,
    LegalStatus,
    ProgramCategory,
    ProgramEntry,
    ProgramRecordType,
    ProgramSourceType,
    RecommendedAction,
    RiskLevel,
    StorageItem,
    StorageKind,
    TaskEntry,
    UWPEntry,
)
from .path_utils import expand_windows_path, folder_size, format_bytes, is_protected

try:
    import winreg  # type: ignore
except ImportError:
    winreg = None

PROGRAM_KEYS = [
    ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]

STORAGE_TARGETS = [
    {
        "display_name": "Temp",
        "path": r"%LOCALAPPDATA%\Temp",
        "kind": StorageKind.TEMP,
        "risk": RiskLevel.LOW,
        "action": RecommendedAction.PURGE,
        "owner": "Windows / apps",
        "source": "KnownPath",
        "notes": "Classic temp clutter. Good purge candidate.",
        "reclaimable_ratio": 1.0,
        "movable_ratio": 0.0,
    },
    {
        "display_name": "NVIDIA DXCache",
        "path": r"%LOCALAPPDATA%\NVIDIA\DXCache",
        "kind": StorageKind.SHADER_CACHE,
        "risk": RiskLevel.LOW,
        "action": RecommendedAction.PURGE,
        "owner": "NVIDIA",
        "source": "KnownPath",
        "notes": "Shader cache is rebuildable; purge first, relocate if it regrows aggressively.",
        "reclaimable_ratio": 1.0,
        "movable_ratio": 1.0,
    },
    {
        "display_name": "Steam HTML Cache",
        "path": r"%LOCALAPPDATA%\Steam\htmlcache",
        "kind": StorageKind.CACHE,
        "risk": RiskLevel.LOW,
        "action": RecommendedAction.PURGE,
        "owner": "Steam",
        "source": "RuleBased",
        "notes": "Large launcher cache; good purge and relocation candidate.",
        "reclaimable_ratio": 1.0,
        "movable_ratio": 1.0,
    },
    {
        "display_name": "Screenshots",
        "path": r"%USERPROFILE%\Pictures\Screenshots",
        "kind": StorageKind.SCREENSHOTS,
        "risk": RiskLevel.MEDIUM,
        "action": RecommendedAction.RELOCATE,
        "owner": "User media",
        "source": "KnownPath",
        "notes": "Usually worth moving off SSD rather than deleting blindly.",
        "reclaimable_ratio": 0.3,
        "movable_ratio": 1.0,
    },
    {
        "display_name": "Captures",
        "path": r"%USERPROFILE%\Videos\Captures",
        "kind": StorageKind.CAPTURES,
        "risk": RiskLevel.MEDIUM,
        "action": RecommendedAction.RELOCATE,
        "owner": "User captures",
        "source": "KnownPath",
        "notes": "Capture archives are often bulky and better moved than purged.",
        "reclaimable_ratio": 0.25,
        "movable_ratio": 1.0,
    },
    {
        "display_name": "Gradle Caches",
        "path": r"%USERPROFILE%\.gradle\caches",
        "kind": StorageKind.CACHE,
        "risk": RiskLevel.LOW,
        "action": RecommendedAction.PURGE,
        "owner": "Gradle",
        "source": "KnownPath",
        "notes": "Gradle dependency caches in the user profile.",
        "reclaimable_ratio": 1.0,
        "movable_ratio": 1.0,
    },
    {
        "display_name": "Gradle Wrapper Dists",
        "path": r"%USERPROFILE%\.gradle\wrapper\dists",
        "kind": StorageKind.CACHE,
        "risk": RiskLevel.MEDIUM,
        "action": RecommendedAction.RELOCATE,
        "owner": "Gradle",
        "source": "KnownPath",
        "notes": "Large wrapper distributions; often better moved than kept on the SSD.",
        "reclaimable_ratio": 0.5,
        "movable_ratio": 1.0,
    },
    {
        "display_name": "Python Pip Cache",
        "path": r"%LOCALAPPDATA%\pip\Cache",
        "kind": StorageKind.CACHE,
        "risk": RiskLevel.LOW,
        "action": RecommendedAction.PURGE,
        "owner": "Python / pip",
        "source": "KnownPath",
        "notes": "pip package cache under the user profile.",
        "reclaimable_ratio": 1.0,
        "movable_ratio": 1.0,
    },
    {
        "display_name": "Python User Cache",
        "path": r"%USERPROFILE%\.cache\pip",
        "kind": StorageKind.CACHE,
        "risk": RiskLevel.LOW,
        "action": RecommendedAction.PURGE,
        "owner": "Python / pip",
        "source": "KnownPath",
        "notes": "Unix-style pip cache occasionally present on Windows developer setups.",
        "reclaimable_ratio": 1.0,
        "movable_ratio": 1.0,
    },
    {
        "display_name": "UV Cache",
        "path": r"%LOCALAPPDATA%\uv\cache",
        "kind": StorageKind.CACHE,
        "risk": RiskLevel.LOW,
        "action": RecommendedAction.PURGE,
        "owner": "Python / uv",
        "source": "KnownPath",
        "notes": "uv cache is rebuildable and usually safe to clear.",
        "reclaimable_ratio": 1.0,
        "movable_ratio": 1.0,
    },
]


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


def _program_record_type(name: str, publisher: str) -> ProgramRecordType:
    lower_name = name.lower()
    lower_publisher = publisher.lower()
    if any(term in lower_name for term in ["security update", "hotfix", "kb"]):
        return ProgramRecordType.HOTFIX
    if any(term in lower_name for term in ["driver", "nvidia", "amd", "intel"]) or "driver" in lower_publisher:
        return ProgramRecordType.DRIVER
    if any(term in lower_name for term in ["runtime", "redistributable", "visual c++", ".net"]):
        return ProgramRecordType.RUNTIME
    if "microsoft" in lower_publisher or lower_name.startswith("microsoft "):
        return ProgramRecordType.MICROSOFT
    return ProgramRecordType.APP if name else ProgramRecordType.UNKNOWN


def _program_category(name: str) -> ProgramCategory:
    lower_name = name.lower()
    if any(term in lower_name for term in ["steam", "epic", "gog", "ubisoft", "ea app"]):
        return ProgramCategory.LAUNCHER
    if any(term in lower_name for term in ["photoshop", "adobe", "davinci", "blender"]):
        return ProgramCategory.CREATIVE
    if any(term in lower_name for term in ["visual studio", "pycharm", "sdk", "git"]):
        return ProgramCategory.DEVTOOL
    if any(term in lower_name for term in ["game", "vr", "playtest", "elden", "cyberpunk"]):
        return ProgramCategory.GAME
    if any(term in lower_name for term in ["driver", "runtime", "redistributable"]):
        return ProgramCategory.SYSTEM_COMPONENT
    if any(term in lower_name for term in ["backup", "cleaner", "tool", "manager"]):
        return ProgramCategory.UTILITY
    return ProgramCategory.OTHER


def _legal_hint(name: str) -> tuple[LegalStatus, str, list[str]]:
    lower_name = name.lower()
    if "steam" in lower_name:
        return LegalStatus.FREE, "Steam itself is free; focus on game/data size instead.", []
    if any(term in lower_name for term in ["discord", "obs", "7-zip", "vlc", "gimp"]):
        return LegalStatus.FREE, "Already free software.", []
    if any(term in lower_name for term in ["photoshop", "office", "adobe"]):
        return LegalStatus.PAID_TRIAL, "Paid software family; review whether a free alternative would fit.", ["GIMP", "LibreOffice", "Photopea"]
    if any(term in lower_name for term in ["winrar"]):
        return LegalStatus.PAID_TRIAL, "Functional free alternative available.", ["7-Zip", "PeaZip"]
    return LegalStatus.UNKNOWN, "", []


def _estimate_program_bytes(install_path: str) -> tuple[int, int, int, int, int, str, str]:
    install_dir = Path(install_path) if install_path else Path()
    install_bytes, _ = folder_size(install_dir) if install_path else (0, 0)
    user_data_bytes = 0
    cache_bytes = 0
    capture_bytes = 0
    total = install_bytes + user_data_bytes + cache_bytes + capture_bytes
    confidence = "High" if install_bytes else "Low"
    notes = "Install path sized directly." if install_bytes else "Install location missing or inaccessible."
    return install_bytes, user_data_bytes, cache_bytes, capture_bytes, total, confidence, notes


def scan_installed_programs(progress_callback: Callable[[str, str], None] | None = None) -> list[ProgramEntry]:
    if winreg is None:
        return []

    hive_map = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
    programs: dict[str, ProgramEntry] = {}

    for hive_name, subkey in PROGRAM_KEYS:
        if progress_callback:
            progress_callback("Registry scan", f"{hive_name}\\{subkey}")
        try:
            reg_key = winreg.OpenKey(hive_map[hive_name], subkey)
        except OSError:
            continue

        for index in range(winreg.QueryInfoKey(reg_key)[0]):
            try:
                entry_name = winreg.EnumKey(reg_key, index)
                entry_key = winreg.OpenKey(reg_key, entry_name)
                raw_name = _safe_query_value(entry_key, "DisplayName")
                if not raw_name:
                    continue
                publisher = _safe_query_value(entry_key, "Publisher")
                version = _safe_query_value(entry_key, "DisplayVersion")
                install_location = _safe_query_value(entry_key, "InstallLocation")
                uninstall_string = _safe_query_value(entry_key, "UninstallString")
                quiet_uninstall_string = _safe_query_value(entry_key, "QuietUninstallString")

                if progress_callback and index % 25 == 0:
                    progress_callback("Sizing program", install_location or raw_name)
                normalized = normalize_name(raw_name)
                install_bytes, user_data_bytes, cache_bytes, capture_bytes, total, confidence, notes = _estimate_program_bytes(install_location)
                record_type = _program_record_type(raw_name, publisher)
                category = _program_category(raw_name)
                legal_status, legal_hint, legal_alternatives = _legal_hint(raw_name)
                risk = RiskLevel.HIGH if record_type in {ProgramRecordType.DRIVER, ProgramRecordType.MICROSOFT} else RiskLevel.MEDIUM

                if normalized in programs:
                    programs[normalized].duplicate_count += 1
                    programs[normalized].duplicate_sources.append(f"{hive_name}:{subkey}")
                    continue

                programs[normalized] = ProgramEntry(
                    id=normalized or entry_name,
                    raw_display_name=raw_name,
                    normalized_name=normalized,
                    display_version=version,
                    publisher=publisher,
                    source_type=ProgramSourceType.WIN32,
                    record_type=record_type,
                    category=category,
                    risk_level=risk,
                    install_location=install_location,
                    uninstall_string=uninstall_string,
                    quiet_uninstall_string=quiet_uninstall_string,
                    estimated_install_bytes=install_bytes,
                    estimated_user_data_bytes=user_data_bytes,
                    estimated_cache_bytes=cache_bytes,
                    estimated_capture_bytes=capture_bytes,
                    estimated_total_bytes=total,
                    estimated_total_human=format_bytes(total),
                    estimate_confidence=confidence,
                    estimate_notes=notes,
                    legal_status=legal_status,
                    legal_alternative_hint=legal_hint,
                    legal_alternative_candidates=legal_alternatives,
                    duplicate_count=0,
                    duplicate_sources=[f"{hive_name}:{subkey}"],
                )
            except Exception:
                continue

    return sorted(programs.values(), key=lambda item: item.estimated_total_bytes, reverse=True)


def _storage_item_from_spec(spec: dict) -> StorageItem | None:
    full_path = Path(expand_windows_path(spec["path"]))
    if not full_path.exists() or is_protected(str(full_path)):
        return None
    total_bytes, _ = folder_size(full_path)
    reclaimable = int(total_bytes * spec.get("reclaimable_ratio", 0.0))
    movable = int(total_bytes * spec.get("movable_ratio", 0.0))
    return StorageItem(
        id=str(full_path),
        display_name=spec["display_name"],
        path=str(full_path),
        owner_hint=spec.get("owner"),
        kind=spec["kind"],
        source=spec["source"],
        risk_level=spec["risk"],
        recommended_action=spec["action"],
        reclaimable_bytes=reclaimable,
        movable_bytes=movable,
        total_bytes=total_bytes,
        human_size=format_bytes(total_bytes),
        confidence="High" if total_bytes else "Medium",
        notes=spec.get("notes", ""),
    )


def scan_storage_items(progress_callback: Callable[[str, str], None] | None = None) -> list[StorageItem]:
    items: list[StorageItem] = []
    for spec in STORAGE_TARGETS:
        if progress_callback:
            progress_callback("Storage scan", spec["path"])
        item = _storage_item_from_spec(spec)
        if item:
            items.append(item)
    return sorted(items, key=lambda item: item.total_bytes, reverse=True)


def filter_programs(
    items: list[ProgramEntry],
    *,
    query: str = "",
    hide_microsoft: bool = True,
    hide_runtimes: bool = True,
    hide_drivers: bool = True,
    hide_hotfixes: bool = True,
    large_only: bool = False,
) -> list[ProgramEntry]:
    query_norm = normalize_name(query) if query else ""
    result = []
    for item in items:
        if hide_microsoft and item.record_type == ProgramRecordType.MICROSOFT:
            continue
        if hide_runtimes and item.record_type == ProgramRecordType.RUNTIME:
            continue
        if hide_drivers and item.record_type == ProgramRecordType.DRIVER:
            continue
        if hide_hotfixes and item.record_type == ProgramRecordType.HOTFIX:
            continue
        if large_only and item.estimated_total_bytes < 500 * 1024 * 1024:
            continue
        if query_norm and query_norm not in item.normalized_name:
            continue
        result.append(item)
    return result


def filter_storage(items: list[StorageItem], *, risk: str = "All", action: str = "All") -> list[StorageItem]:
    result = list(items)
    if risk != "All":
        result = [item for item in result if item.risk_level.value == risk]
    if action != "All":
        result = [item for item in result if item.recommended_action.value == action]
    return result


def build_purge_plan(items: list[StorageItem], preset: str) -> list[StorageItem]:
    if preset == "Safe Cleanup":
        return [item for item in items if item.recommended_action == RecommendedAction.PURGE and item.risk_level == RiskLevel.LOW]
    if preset == "Cache Reset":
        return [item for item in items if item.kind in {StorageKind.CACHE, StorageKind.SHADER_CACHE, StorageKind.TEMP}]
    if preset == "Launcher Cleanup":
        return [item for item in items if item.owner_hint and any(name in item.owner_hint.lower() for name in ["steam", "epic", "launcher"])]
    if preset == "Residue Review":
        return [item for item in items if item.recommended_action in {RecommendedAction.PURGE, RecommendedAction.REVIEW}]
    if preset == "Media Capture Review":
        return [item for item in items if item.kind in {StorageKind.SCREENSHOTS, StorageKind.CAPTURES}]
    return items


def relocation_candidates(items: list[StorageItem]) -> list[StorageItem]:
    return [
        item
        for item in items
        if item.recommended_action in {RecommendedAction.RELOCATE, RecommendedAction.REVIEW}
        and item.movable_bytes > 0
        and item.kind not in {StorageKind.SAVE_DATA, StorageKind.INSTALL_DATA}
    ]


# ---------------------------------------------------------------------------
# Scheduled Tasks Scanner
# ---------------------------------------------------------------------------

_TASK_CRITICAL_PATTERNS = [
    "windows update", "defender", "antimalware", "security", "autochk",
    "system restore", "registry backup", "windows backup", "disk diagnostic",
    "uefi", "bios", "bitlocker", "shadow copy",
]

_TASK_WHITELIST_PATTERNS = [
    "adobe", "ccleaner", "steam", "epic", "origin", "uplay", "ubisoft",
    "google update", "chrome update", "firefox update", "java update",
    "nvidia", "amd", "realtek", "malwarebytes", "recuva", "teamviewer",
    "dropbox", "onedrive sync", "zoom", "discord",
]


def _is_task_critical(name: str, path: str) -> bool:
    combined = (name + " " + path).lower()
    return any(pattern in combined for pattern in _TASK_CRITICAL_PATTERNS)


def scan_scheduled_tasks() -> list[TaskEntry]:
    """Scan Windows scheduled tasks using schtasks.exe. Falls back to empty list on non-Windows."""
    tasks: list[TaskEntry] = []
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/fo", "CSV", "/v"],
            capture_output=True, text=True, timeout=30, errors="replace",
        )
        if result.returncode != 0:
            return tasks

        lines = result.stdout.splitlines()
        if not lines:
            return tasks

        headers: list[str] = []
        for line in lines:
            row = [c.strip('"') for c in line.split('","')]
            if not headers:
                if "TaskName" in line or "Aufgabenname" in line:
                    headers = row
                continue
            if len(row) < 2 or not row[0]:
                continue
            row_map: dict[str, str] = dict(zip(headers, row))

            name = row_map.get("Task To Run", row_map.get("Aufgabe", "")).strip()
            task_name_col = row_map.get("TaskName", row_map.get("Aufgabenname", "")).strip()
            if not task_name_col:
                continue

            # Use the last path segment as the display name
            display = task_name_col.split("\\")[-1] or task_name_col
            enabled_raw = row_map.get("Scheduled Task State", row_map.get("Status der geplanten Aufgabe", "Enabled")).lower()
            enabled = "enabled" in enabled_raw or "aktiviert" in enabled_raw
            status = row_map.get("Status", "Unknown")
            last_run = row_map.get("Last Run Time", row_map.get("Letzte Ausführungszeit", ""))
            next_run = row_map.get("Next Run Time", row_map.get("Nächste Ausführungszeit", ""))
            run_as = row_map.get("Run As User", row_map.get("Ausführen als Benutzer", ""))
            description = row_map.get("Comment", row_map.get("Kommentar", ""))

            tasks.append(
                TaskEntry(
                    name=display,
                    path=task_name_col,
                    enabled=enabled,
                    is_critical=_is_task_critical(display, task_name_col),
                    last_run=last_run,
                    next_run=next_run,
                    status=status,
                    description=description[:120],
                    run_as=run_as,
                )
            )
    except Exception:
        pass

    # De-duplicate by path
    seen: set[str] = set()
    unique: list[TaskEntry] = []
    for task in tasks:
        if task.path not in seen:
            seen.add(task.path)
            unique.append(task)
    return unique


# ---------------------------------------------------------------------------
# Archive / Installer Scanner
# ---------------------------------------------------------------------------

_ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z", ".gz", ".tar", ".bz2", ".xz", ".zst"}
_INSTALLER_EXTENSIONS = {".msi", ".exe", ".cab", ".iso", ".appx", ".msix"}

_KNOWN_INSTALLER_PATTERNS = [
    "setup", "install", "installer", "update", "upgrade", "patch",
    "vcredist", "dotnet", "directx", "_x64", "_x86",
]


def _is_installer_exe(filename: str) -> bool:
    lower = filename.lower()
    return any(pattern in lower for pattern in _KNOWN_INSTALLER_PATTERNS)


def _classify_archive(path: Path) -> str:
    """Return a human-readable status/classification."""
    ext = path.suffix.lower()
    name_lower = path.name.lower()
    if ext in _ARCHIVE_EXTENSIONS:
        return "Archive"
    if ext == ".iso":
        return "Disk Image"
    if ext in {".appx", ".msix"}:
        return "UWP Package"
    if ext == ".msi":
        return "MSI Installer"
    if ext == ".exe" and _is_installer_exe(path.name):
        return "EXE Installer"
    if ext == ".exe":
        return "Executable"
    return "Unknown"


def scan_archives(folder_path: str) -> list[ArchiveItem]:
    """Walk a folder and classify archive / installer files."""
    folder = Path(folder_path)
    if not folder.exists():
        return []

    all_extensions = _ARCHIVE_EXTENSIONS | _INSTALLER_EXTENSIONS
    items: list[ArchiveItem] = []

    for file in sorted(folder.rglob("*")):
        if not file.is_file():
            continue
        if file.suffix.lower() not in all_extensions:
            continue
        try:
            size_bytes = file.stat().st_size
        except OSError:
            continue

        file_type = _classify_archive(file)
        size_mb = size_bytes / (1024 * 1024)

        # Very lightweight overlap check: name-based heuristic only
        overlap = False
        if winreg is not None:
            name_clean = re.sub(r"[_\-\s]", "", file.stem.lower())
            overlap = any(
                name_clean in normalize_name(prog.raw_display_name).replace(" ", "")
                for prog in scan_installed_programs()[:200]
            ) if name_clean else False

        items.append(
            ArchiveItem(
                path=str(file),
                file_type=file_type,
                size_mb=round(size_mb, 2),
                status=file_type,
                overlap_installed=overlap,
            )
        )

    return sorted(items, key=lambda a: a.size_mb, reverse=True)


# ---------------------------------------------------------------------------
# UWP / AppX Scanner
# ---------------------------------------------------------------------------

_AI_PACKAGE_KEYWORDS = [
    "recall", "copilot", "windowsai", "aicomponent", "cortana",
    "bing", "clipchamp", "onedrive", "xbox", "yourphone", "gethelp",
]


def scan_uwp_apps() -> list[UWPEntry]:
    """List installed UWP / AppX packages. Returns empty list on non-Windows."""
    apps: list[UWPEntry] = []
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-AppxPackage | Select-Object Name,PackageFullName,PublisherDisplayName,InstallLocation,Version | ConvertTo-Csv -NoTypeInformation"],
            capture_output=True, text=True, timeout=30, errors="replace",
        )
        if result.returncode != 0:
            return apps

        lines = result.stdout.strip().splitlines()
        if len(lines) < 2:
            return apps

        headers = [h.strip('"') for h in lines[0].split(",")]
        for line in lines[1:]:
            parts = [p.strip('"') for p in line.split(",")]
            row = dict(zip(headers, parts))
            name = row.get("Name", "").strip()
            fullname = row.get("PackageFullName", "").strip()
            if not name or not fullname:
                continue
            publisher = row.get("PublisherDisplayName", "").strip()
            location = row.get("InstallLocation", "").strip()
            version = row.get("Version", "").strip()
            is_ai = any(kw in name.lower() for kw in _AI_PACKAGE_KEYWORDS)
            apps.append(
                UWPEntry(
                    name=name,
                    package_fullname=fullname,
                    is_ai_related=is_ai,
                    publisher=publisher,
                    install_location=location,
                    version=version,
                )
            )
    except Exception:
        pass
    return apps


# ---------------------------------------------------------------------------
# Autorun / Registry Scanner
# ---------------------------------------------------------------------------

_AUTORUN_KEYS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon",
]

_AUTORUN_SUSPICIOUS_PATTERNS = [
    "temp\\", "appdata\\local\\temp", "%temp%", "cmd.exe /c",
    "powershell -enc", "regsvr32", "rundll32", "mshta",
]


def scan_autoruns() -> list[AutorunEntry]:
    """Scan common Windows autorun registry locations."""
    entries: list[AutorunEntry] = []
    if winreg is None:
        return entries

    hive_map = {
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
        "HKCU": winreg.HKEY_CURRENT_USER,
    }

    for hive_name, hive in hive_map.items():
        for subkey in _AUTORUN_KEYS:
            try:
                key = winreg.OpenKey(hive, subkey)
            except OSError:
                continue
            count = winreg.QueryInfoKey(key)[1]
            for i in range(count):
                try:
                    value_name, data, _ = winreg.EnumValue(key, i)
                    command = str(data)
                    is_suspicious = any(p in command.lower() for p in _AUTORUN_SUSPICIOUS_PATTERNS)
                    entries.append(
                        AutorunEntry(
                            name=value_name,
                            location=f"{hive_name}\\{subkey}",
                            entry_type="Registry",
                            command=command,
                            enabled=True,
                            is_suspicious=is_suspicious,
                            risk="High" if is_suspicious else "Low",
                            notes="Suspicious autorun detected." if is_suspicious else "",
                        )
                    )
                except OSError:
                    continue

    # Also scan startup folders
    for startup_path in [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "StartUp",
    ]:
        if startup_path.exists():
            for file in startup_path.iterdir():
                if file.is_file():
                    entries.append(
                        AutorunEntry(
                            name=file.name,
                            location=str(startup_path),
                            entry_type="StartupFolder",
                            command=str(file),
                            enabled=True,
                            is_suspicious=False,
                            risk="Low",
                        )
                    )

    return entries


# ---------------------------------------------------------------------------
# Benchmark snapshot
# ---------------------------------------------------------------------------

def benchmark_snapshot() -> dict:
    """Take a lightweight system resource snapshot."""
    try:
        import psutil
        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.5)
        disk = psutil.disk_usage("/")
        return {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "ram_percent": ram.percent,
            "ram_total_gb": round(ram.total / (1024 ** 3), 2),
            "ram_used_gb": round(ram.used / (1024 ** 3), 2),
            "cpu_percent": cpu,
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
            "disk_used_gb": round(disk.used / (1024 ** 3), 2),
            "disk_free_gb": round(disk.free / (1024 ** 3), 2),
        }
    except ImportError:
        return {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "ram_percent": 0.0,
            "cpu_percent": 0.0,
            "disk_free_gb": 0.0,
        }
