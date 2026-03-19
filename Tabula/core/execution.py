from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from .history import RelocationLedger
from .models import LinkType, RelocationRecord, TabulaItem
from .path_utils import is_protected


class ExecutionEngine:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = Path(base_dir or Path(__file__).resolve().parents[1] / "backups")
        self.log_dir = self.base_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = RelocationLedger(self.base_dir)

    def preview(self, item: TabulaItem, target_root: str, link_type: LinkType = LinkType.JUNCTION) -> str:
        destination = Path(target_root) / Path(item.path).name
        warnings = []
        if is_protected(item.path):
            warnings.append("Source is protected and cannot be relocated.")
        if destination.exists():
            warnings.append("Target already exists.")
        warning_text = "\n".join(f"- {warning}" for warning in warnings) or "- No blocking warnings detected."
        return (
            f"Source: {item.path}\n"
            f"Target: {destination}\n"
            f"Size: {item.size_human}\n"
            f"Link type: {link_type.value}\n"
            f"Warnings:\n{warning_text}"
        )

    def record_relocation(self, item: TabulaItem, target_root: str, link_type: LinkType) -> RelocationRecord:
        destination = Path(target_root) / Path(item.path).name
        record = RelocationRecord(
            id=str(uuid.uuid4())[:8],
            source_path=item.path,
            target_path=str(destination),
            link_type=link_type,
            created_at=datetime.now(),
            validated=False,
            validation_notes="Planned only in this environment.",
        )
        self.ledger.append(record)
        self._log({"event": "relocation_planned", **record.to_dict()})
        return record

    def validate_links(self) -> list[RelocationRecord]:
        records = self.ledger.load()
        for record in records:
            target_exists = Path(record.target_path).exists()
            record.validated = target_exists
            record.status = "Active" if target_exists else "Broken"
            record.validation_notes = "Target reachable." if target_exists else "Target missing in current environment."
        self.ledger.save_all(records)
        return records

    def _log(self, payload: dict) -> None:
        log_file = self.log_dir / f"run_{datetime.now():%Y%m%d}.log"
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": datetime.now().isoformat(), **payload}) + "\n")
