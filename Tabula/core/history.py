from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import RelocationRecord


class RelocationLedger:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.base_dir / "relocations.json"
        if not self.registry_path.exists():
            self.registry_path.write_text("[]", encoding="utf-8")

    def load(self) -> list[RelocationRecord]:
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        return [RelocationRecord.from_dict(row) for row in data]

    def save_all(self, records: Iterable[RelocationRecord]) -> None:
        payload = [record.to_dict() for record in records]
        self.registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def append(self, record: RelocationRecord) -> None:
        records = self.load()
        records.append(record)
        self.save_all(records)

    def export_json(self, destination: Path) -> Path:
        destination.write_text(self.registry_path.read_text(encoding="utf-8"), encoding="utf-8")
        return destination
