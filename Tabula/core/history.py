from __future__ import annotations

import json
from pathlib import Path
from typing import Generic, Iterable, TypeVar

from .models import ActionRecord, RelocationRecord, SerializableDataclass

T = TypeVar("T", bound=SerializableDataclass)


class JsonLedger(Generic[T]):
    def __init__(self, path: Path, model_cls: type[T]) -> None:
        self.path = path
        self.model_cls = model_cls
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def load(self) -> list[T]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [self.model_cls.from_dict(row) for row in data]

    def save_all(self, rows: Iterable[T]) -> None:
        payload = [row.to_dict() for row in rows]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def append(self, row: T) -> None:
        rows = self.load()
        rows.append(row)
        self.save_all(rows)

    def export_json(self, destination: Path) -> Path:
        destination.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
        return destination


class RelocationLedger(JsonLedger[RelocationRecord]):
    def __init__(self, base_dir: Path) -> None:
        super().__init__(base_dir / "relocations.json", RelocationRecord)


class ActionLedger(JsonLedger[ActionRecord]):
    def __init__(self, base_dir: Path) -> None:
        super().__init__(base_dir / "actions.json", ActionRecord)
