from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .models import FolderKind, RecommendedAction, RiskLevel, TabulaItem
from .path_utils import expand_windows_path, folder_size, format_bytes, is_protected

SCAN_TARGETS = [
    {
        "display_name": "Temp",
        "path": "%LOCALAPPDATA%\\Temp",
        "kind": FolderKind.TEMP,
        "risk": RiskLevel.LOW,
        "action": RecommendedAction.PURGE,
        "owner": "Windows / apps",
        "source": "KnownPath",
        "notes": "Temporary files that are usually safe to clear.",
    },
    {
        "display_name": "NVIDIA DXCache",
        "path": "%LOCALAPPDATA%\\NVIDIA\\DXCache",
        "kind": FolderKind.SHADER_CACHE,
        "risk": RiskLevel.LOW,
        "action": RecommendedAction.RELOCATE,
        "owner": "NVIDIA",
        "source": "KnownPath",
        "notes": "Large shader caches are usually safe to relocate or rebuild.",
    },
    {
        "display_name": "Steam HTML Cache",
        "path": "%LOCALAPPDATA%\\Steam\\htmlcache",
        "kind": FolderKind.CACHE,
        "risk": RiskLevel.MEDIUM,
        "action": RecommendedAction.RELOCATE,
        "owner": "Steam",
        "source": "RuleBased",
        "notes": "Launcher cache that grows quickly and is often a strong relocation candidate.",
    },
    {
        "display_name": "Screenshots",
        "path": "%USERPROFILE%\\Pictures\\Screenshots",
        "kind": FolderKind.SCREENSHOTS,
        "risk": RiskLevel.MEDIUM,
        "action": RecommendedAction.REVIEW,
        "owner": "User media",
        "source": "Heuristic",
        "notes": "Media is usually worth reviewing before purge or relocation.",
    },
]


def _build_item(spec: dict) -> TabulaItem | None:
    raw_path = spec["path"]
    full_path = Path(expand_windows_path(raw_path))
    if not full_path.exists() or is_protected(str(full_path)):
        return None
    size_bytes, item_count = folder_size(full_path)
    return TabulaItem(
        id=str(full_path),
        display_name=spec["display_name"],
        path=str(full_path),
        normalized_path=str(full_path).lower(),
        source_type=spec["source"],
        owner_hint=spec.get("owner"),
        kind=spec["kind"],
        risk_level=spec["risk"],
        recommended_action=spec["action"],
        size_bytes=size_bytes,
        size_human=format_bytes(size_bytes),
        item_count=item_count,
        confidence="High" if size_bytes else "Medium",
        notes=spec.get("notes"),
    )


def scan_storage_map() -> list[TabulaItem]:
    items = [item for item in (_build_item(spec) for spec in SCAN_TARGETS) if item]
    return sorted(items, key=lambda item: item.size_bytes, reverse=True)


def filter_items(items: Iterable[TabulaItem], *, risk: str = "All", action: str = "All") -> list[TabulaItem]:
    result = list(items)
    if risk != "All":
        result = [item for item in result if item.risk_level.value == risk]
    if action != "All":
        result = [item for item in result if item.recommended_action.value == action]
    return result
