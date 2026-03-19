from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from .history import ActionLedger, RelocationLedger
from .models import ActionRecord, ActionStatus, ActionType, LinkType, RelocationRecord, StorageItem
from .path_utils import is_protected


class ExecutionEngine:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = Path(base_dir or Path(__file__).resolve().parents[1] / "backups")
        self.log_dir = self.base_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.relocation_ledger = RelocationLedger(self.base_dir)
        self.action_ledger = ActionLedger(self.base_dir)

    def preview_relocation(self, item: StorageItem, target_root: str, link_type: LinkType = LinkType.JUNCTION) -> str:
        destination = Path(target_root) / Path(item.path).name
        warnings = []
        if is_protected(item.path):
            warnings.append("Source is protected and should only be moved with explicit review.")
        if destination.exists():
            warnings.append("Target already exists.")
        if not item.movable_bytes:
            warnings.append("This item currently has no movable bytes classified.")
        warning_text = "\n".join(f"- {warning}" for warning in warnings) or "- No blocking warnings detected."
        return (
            f"Source: {item.path}\n"
            f"Target: {destination}\n"
            f"Movable size: {item.human_size}\n"
            f"Link type: {link_type.value}\n"
            f"Warnings:\n{warning_text}"
        )

    def record_relocation(self, item: StorageItem, target_root: str, link_type: LinkType) -> RelocationRecord:
        destination = Path(target_root) / Path(item.path).name
        record = RelocationRecord(
            id=str(uuid.uuid4())[:8],
            source_path=item.path,
            target_path=str(destination),
            link_type=link_type,
            created_at=datetime.now(),
            owner_hint=item.owner_hint or item.display_name,
            validated=False,
            validation_notes="Planned only in this environment.",
        )
        self.relocation_ledger.append(record)
        self.record_action(
            action_type=ActionType.RELOCATE,
            status=ActionStatus.DRY_RUN,
            source_path=item.path,
            target_path=str(destination),
            bytes_affected=item.movable_bytes or item.total_bytes,
            notes=f"Relocation planned for {item.display_name}.",
        )
        self._log({"event": "relocation_planned", **record.to_dict()})
        return record

    def preview_purge(self, items: list[StorageItem]) -> str:
        selected = [item for item in items if item.recommended_action in {item.recommended_action.PURGE, item.recommended_action.REVIEW}]
        reclaimable = sum(item.reclaimable_bytes for item in selected)
        return (
            f"Selected purge candidates: {len(selected)}\n"
            f"Estimated reclaimable size: {reclaimable / (1024 ** 3):.2f} GB\n"
            f"High-risk review items: {sum(1 for item in selected if item.risk_level.value == 'High')}"
        )

    def record_purge(self, items: list[StorageItem], *, dry_run: bool) -> ActionRecord:
        reclaimable = sum(item.reclaimable_bytes for item in items)
        action = self.record_action(
            action_type=ActionType.PURGE,
            status=ActionStatus.DRY_RUN if dry_run else ActionStatus.SUCCESS,
            bytes_affected=reclaimable,
            notes=f"Purge {'preview' if dry_run else 'execution'} for {len(items)} item(s).",
        )
        self._log({"event": "purge_recorded", **action.to_dict()})
        return action

    def record_action(
        self,
        *,
        action_type: ActionType,
        status: ActionStatus,
        source_path: str = "",
        target_path: str = "",
        bytes_affected: int = 0,
        notes: str = "",
    ) -> ActionRecord:
        action = ActionRecord(
            id=str(uuid.uuid4())[:8],
            action_type=action_type,
            started_at=datetime.now(),
            finished_at=datetime.now(),
            status=status,
            source_path=source_path,
            target_path=target_path,
            bytes_affected=bytes_affected,
            notes=notes,
        )
        self.action_ledger.append(action)
        return action

    def validate_links(self) -> list[RelocationRecord]:
        records = self.relocation_ledger.load()
        for record in records:
            target_exists = Path(record.target_path).exists()
            record.validated = target_exists
            record.status = "Active" if target_exists else "Broken"
            record.validation_notes = "Target reachable." if target_exists else "Target missing in current environment."
        self.relocation_ledger.save_all(records)
        return records

    def _log(self, payload: dict) -> None:
        log_file = self.log_dir / f"run_{datetime.now():%Y%m%d}.log"
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": datetime.now().isoformat(), **payload}) + "\n")
