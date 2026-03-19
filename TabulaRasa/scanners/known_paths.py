from __future__ import annotations

from pathlib import Path

from shared.core.models import PurgeItem, PurgeKind, RecommendedAction, RiskLevel
from shared.core.path_utils import expand_windows_path, folder_size, format_bytes, is_protected

KNOWN_PATHS = [
    {
        "display_name": "Windows Temp",
        "path": "%TEMP%",
        "kind": PurgeKind.TEMP,
        "risk": RiskLevel.LOW,
        "action": RecommendedAction.PURGE,
        "notes": "Classic temp files.",
        "review_required": False,
    },
    {
        "display_name": "NVIDIA DXCache",
        "path": "%LOCALAPPDATA%\\NVIDIA\\DXCache",
        "kind": PurgeKind.SHADER_CACHE,
        "risk": RiskLevel.LOW,
        "action": RecommendedAction.PURGE,
        "notes": "Shader cache can be rebuilt.",
        "review_required": False,
    },
    {
        "display_name": "Screenshots",
        "path": "%USERPROFILE%\\Pictures\\Screenshots",
        "kind": PurgeKind.SCREENSHOTS,
        "risk": RiskLevel.MEDIUM,
        "action": RecommendedAction.REVIEW,
        "notes": "Review screenshots before deleting.",
        "review_required": True,
    },
]


def scan_known_paths() -> list[PurgeItem]:
    items: list[PurgeItem] = []
    for spec in KNOWN_PATHS:
        full_path = Path(expand_windows_path(spec["path"]))
        if not full_path.exists() or is_protected(str(full_path)):
            continue
        size_bytes = folder_size(full_path)
        items.append(
            PurgeItem(
                id=str(full_path),
                display_name=spec["display_name"],
                path=str(full_path),
                kind=spec["kind"],
                risk_level=spec["risk"],
                recommended_action=spec["action"],
                size_bytes=size_bytes,
                size_human=format_bytes(size_bytes),
                detection_source="KnownPath",
                notes=spec["notes"],
                review_required=spec["review_required"],
            )
        )
    return sorted(items, key=lambda item: item.size_bytes, reverse=True)
