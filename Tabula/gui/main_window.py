from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk

from core.planner import SafePlanner
from gui.module_api import AppContext, BaseModule
from gui.module_registry import MODULES

_APP_ROOT = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


def _load_module_config() -> dict[str, bool]:
    config_path = _APP_ROOT / "modules.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("modules.json unreadable, using defaults: %s", exc)
    return {}


class TabulaApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tabula – Find it. Clear it. Move it.")
        self.geometry("1920x1180")
        self.minsize(1600, 980)

        self._configure_styles()

        # Module configuration
        self.module_config: dict[str, bool] = _load_module_config()

        # Build available module list from registry
        self.available_modules: list[dict] = [
            {"id": mod_cls.module_id, "title": mod_cls.title, "cls": mod_cls}
            for mod_cls in MODULES
        ]

        # Shared planner and context
        planner = SafePlanner()
        self.context = AppContext(planner=planner)

        # Create tab view
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=16)

        # Instantiate and build enabled modules
        self._active_modules: list[BaseModule] = []
        for mod_info in self.available_modules:
            mod_id = mod_info["id"]
            if not self.module_config.get(mod_id, True):
                continue
            tab = self.tabview.add(mod_info["title"])
            try:
                instance = mod_info["cls"]()
                instance.build(tab, self, self.context)
                self._active_modules.append(instance)
            except Exception as exc:
                logger.exception("Failed to build module %s", mod_id)
                ctk.CTkLabel(
                    tab,
                    text=f"Modul '{mod_info['title']}' konnte nicht geladen werden:\n{exc}",
                    text_color="red",
                ).pack(pady=20)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", rowheight=34, font=("Segoe UI", 12))
        style.configure("Treeview.Heading", font=("Segoe UI", 12, "bold"))
