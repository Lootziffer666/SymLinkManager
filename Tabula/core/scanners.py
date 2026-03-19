from __future__ import annotations

import os
import re
from pathlib import Path

from .models import (
    LegalStatus,
    ProgramCategory,
    ProgramEntry,
    ProgramRecordType,
    ProgramSourceType,
    RecommendedAction,
    RiskLevel,
    StorageItem,
    StorageKind,
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


def scan_installed_programs() -> list[ProgramEntry]:
    if winreg is None:
        return []

    hive_map = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
    programs: dict[str, ProgramEntry] = {}

    for hive_name, subkey in PROGRAM_KEYS:
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


def scan_storage_items() -> list[StorageItem]:
    items = [item for item in (_storage_item_from_spec(spec) for spec in STORAGE_TARGETS) if item]
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
