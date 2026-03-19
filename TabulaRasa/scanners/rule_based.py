from __future__ import annotations

from pathlib import Path

import yaml

from shared.core.models import PurgeItem, PurgeKind, RecommendedAction, RiskLevel
from shared.core.path_utils import expand_windows_path, folder_size, format_bytes, is_protected


def load_rule_packs() -> list[PurgeItem]:
    rule_file = Path(__file__).resolve().parents[1] / "shared" / "rule_packs" / "default.yaml"
    if not rule_file.exists():
        return []
    with rule_file.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    items: list[PurgeItem] = []
    for rule in data.get("rules", []):
        full_path = Path(expand_windows_path(rule.get("path", "")))
        if not str(full_path) or not full_path.exists() or is_protected(str(full_path)):
            continue
        size_bytes = folder_size(full_path)
        items.append(
            PurgeItem(
                id=str(full_path),
                display_name=rule["name"],
                path=str(full_path),
                kind=PurgeKind(rule.get("kind", PurgeKind.UNKNOWN.value)),
                risk_level=RiskLevel(rule.get("risk", RiskLevel.MEDIUM.value)),
                recommended_action=RecommendedAction(rule.get("action", RecommendedAction.REVIEW.value)),
                size_bytes=size_bytes,
                size_human=format_bytes(size_bytes),
                detection_source="RuleBased",
                notes=rule.get("notes"),
                review_required=bool(rule.get("review_required", False)),
            )
        )
    return sorted(items, key=lambda item: item.size_bytes, reverse=True)
