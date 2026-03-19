from __future__ import annotations

import csv
import json
from pathlib import Path

from shared.core.models import PurgeRun


class PurgeLedger:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.base_dir / "history.json"
        if not self.ledger_path.exists():
            self.ledger_path.write_text("[]", encoding="utf-8")

    def load(self) -> list[PurgeRun]:
        data = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        return [PurgeRun.from_dict(entry) for entry in data]

    def save(self, runs: list[PurgeRun]) -> None:
        self.ledger_path.write_text(json.dumps([run.to_dict() for run in runs], indent=2), encoding="utf-8")

    def append(self, run: PurgeRun) -> None:
        runs = self.load()
        runs.append(run)
        self.save(runs)

    def export_json(self, destination: Path) -> Path:
        destination.write_text(self.ledger_path.read_text(encoding="utf-8"), encoding="utf-8")
        return destination

    def export_csv(self, destination: Path) -> Path:
        runs = self.load()
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["id", "started_at", "finished_at", "mode", "selected_item_count", "estimated_bytes", "deleted_bytes", "skipped_count", "failed_count", "log_path"])
            writer.writeheader()
            for run in runs:
                writer.writerow(run.to_dict())
        return destination
