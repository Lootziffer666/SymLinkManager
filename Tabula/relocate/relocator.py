from __future__ import annotations

from core.execution import ExecutionEngine
from core.models import LinkType, TabulaItem


class Relocator:
    def __init__(self, engine: ExecutionEngine) -> None:
        self.engine = engine

    def preview(self, item: TabulaItem, target_root: str, link_type: LinkType = LinkType.JUNCTION) -> str:
        return self.engine.preview(item, target_root, link_type)

    def plan(self, item: TabulaItem, target_root: str, link_type: LinkType = LinkType.JUNCTION):
        return self.engine.record_relocation(item, target_root, link_type)
