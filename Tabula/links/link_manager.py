from __future__ import annotations

from core.execution import ExecutionEngine
from core.models import RelocationRecord


class LinkManager:
    def __init__(self, engine: ExecutionEngine) -> None:
        self.engine = engine

    def load_links(self) -> list[RelocationRecord]:
        return self.engine.relocation_ledger.load()

    def validate_all(self) -> list[RelocationRecord]:
        return self.engine.validate_links()
