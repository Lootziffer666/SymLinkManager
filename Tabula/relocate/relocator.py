from __future__ import annotations

from core.execution import ExecutionEngine
from core.models import LinkType, StorageItem


class Relocator:
    def __init__(self, engine: ExecutionEngine) -> None:
        self.engine = engine

    def preview(self, item: StorageItem, target_root: str, link_type: LinkType = LinkType.JUNCTION) -> str:
        return self.engine.preview_relocation(item, target_root, link_type)

    def plan(self, item: StorageItem, target_root: str, link_type: LinkType = LinkType.JUNCTION):
        return self.engine.record_relocation(item, target_root, link_type)
