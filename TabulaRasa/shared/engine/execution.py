from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from shared.core.models import ExecutionMode, PurgeItem, PurgeRun
from shared.engine.history import PurgeLedger


class ExecutionEngine:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = Path(base_dir or Path(__file__).resolve().parents[2] / "backups")
        self.log_dir = self.base_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = PurgeLedger(self.base_dir)
        self.current_run: PurgeRun | None = None

    def start_run(self, mode: ExecutionMode) -> PurgeRun:
        run = PurgeRun(
            id=str(uuid.uuid4())[:8],
            started_at=datetime.now(),
            mode=mode,
            log_path=str(self.log_dir / f"run_{datetime.now():%Y%m%d_%H%M%S}.log"),
        )
        self.current_run = run
        self._log({"event": "run_started", "mode": mode.value}, run.log_path)
        return run

    def preview(self, items: list[PurgeItem], mode: ExecutionMode) -> str:
        selected = [item for item in items if item.selected]
        total = sum(item.size_bytes for item in selected)
        return (
            f"Selected items: {len(selected)}\n"
            f"Estimated reclaim: {total / (1024 ** 3):.2f} GB\n"
            f"Mode: {mode.value}\n"
            f"Review-required items: {sum(1 for item in selected if item.review_required)}"
        )

    def execute(self, items: list[PurgeItem], mode: ExecutionMode) -> list[str]:
        run = self.start_run(mode)
        selected = [item for item in items if item.selected]
        run.selected_item_count = len(selected)
        run.estimated_bytes = sum(item.size_bytes for item in selected)
        results: list[str] = []
        for item in selected:
            action_label = "Recycle" if mode == ExecutionMode.SAFE else "Delete" if mode == ExecutionMode.AGGRESSIVE else "DryRun"
            results.append(f"[{action_label}] {item.display_name} -> {item.path}")
        run.deleted_bytes = 0 if mode == ExecutionMode.DRY_RUN else run.estimated_bytes
        run.finished_at = datetime.now()
        self.ledger.append(run)
        self._log({"event": "run_finished", **run.to_dict()}, run.log_path)
        return results

    def what_would_delete_today(self) -> list[str]:
        today = datetime.now().date()
        results = []
        for run in self.ledger.load():
            if run.started_at.date() == today:
                results.append(f"{run.id} | {run.mode.value} | {run.estimated_bytes}")
        return results

    def _log(self, payload: dict, log_path: str) -> None:
        with Path(log_path).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": datetime.now().isoformat(), **payload}) + "\n")
