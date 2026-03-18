from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.planner import SafePlanner


@dataclass
class AppContext:
    planner: SafePlanner
    state: dict[str, Any] = field(default_factory=dict)


class BaseModule:
    module_id = "base"
    title = "Base"

    def build(self, container, app, context: AppContext) -> None:  # pragma: no cover - interface
        raise NotImplementedError
