from __future__ import annotations

import json
import logging
import traceback
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from core.planner import SafePlanner
from gui.module_api import AppContext
from gui.module_registry import MODULES

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class TabulaApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tabula – Barebone Host")
        self.geometry("1420x940")

        icon_path = Path(__file__).resolve().parents[1] / "tabula_icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.context = AppContext(planner=SafePlanner())
        self.module_config = self._load_module_config()
        self.available_modules = [{"id": cls.module_id, "title": cls.title, "class": cls} for cls in MODULES]

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)

        self._mount_modules()

        self.report_callback_exception = self._report_callback_exception


    def _load_module_config(self) -> dict[str, bool]:
        config_path = Path(__file__).resolve().parents[1] / "modules.json"
        if config_path.exists():
            return json.loads(config_path.read_text(encoding="utf-8"))
        defaults = {cls.module_id: True for cls in MODULES}
        defaults["module_manager"] = True
        defaults["plan_execute"] = True
        config_path.write_text(json.dumps(defaults, indent=2, ensure_ascii=False), encoding="utf-8")
        return defaults

    def _mount_modules(self) -> None:
        for module_cls in MODULES:
            module_id = module_cls.module_id
            enabled = bool(self.module_config.get(module_id, True))
            if not enabled and module_id not in {"module_manager", "plan_execute"}:
                continue

            self.tabview.add(module_cls.title)
            container = self.tabview.tab(module_cls.title)
            module_cls().build(container=container, app=self, context=self.context)

    def _report_callback_exception(self, exc, val, tb) -> None:
        logging.getLogger("tabula.gui").error(
            "Unhandled Tk callback exception: %s\n%s",
            val,
            "".join(traceback.format_exception(exc, val, tb)),
        )
        messagebox.showerror("Tabula Crash", "Ein GUI-Fehler wurde protokolliert. Siehe Tabula/logs/tabula.log")


if __name__ == "__main__":
    app = TabulaApp()
    app.mainloop()
