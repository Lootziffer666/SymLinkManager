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

_APP_ROOT = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Theme palette helpers
# ---------------------------------------------------------------------------
THEME_LIGHT = "light"
THEME_DARK = "dark"

# Light: white/red  |  Dark: anthracite/orange
_PALETTE = {
    THEME_LIGHT: {
        "bg": "#FFFFFF",
        "bg_secondary": "#F2F2F2",
        "accent": "#D32F2F",
        "accent_hover": "#B71C1C",
        "accent_text": "#FFFFFF",
        "text": "#1A1A1A",
        "text_muted": "#555555",
        "border": "#CCCCCC",
        "tree_bg": "#FFFFFF",
        "tree_fg": "#1A1A1A",
        "tree_heading_bg": "#F2F2F2",
        "tree_heading_fg": "#D32F2F",
        "tree_select_bg": "#FFCDD2",
        "tree_select_fg": "#1A1A1A",
        "risk_high": "#C62828",
        "risk_medium": "#E65100",
        "risk_low": "#2E7D32",
        "import_match_bg": "#FCE4EC",
        "ctk_mode": "light",
    },
    THEME_DARK: {
        "bg": "#2B2B2B",
        "bg_secondary": "#333333",
        "accent": "#F5A623",
        "accent_hover": "#E6951A",
        "accent_text": "#1A1A1A",
        "text": "#F0F0F0",
        "text_muted": "#AAAAAA",
        "border": "#444444",
        "tree_bg": "#2B2B2B",
        "tree_fg": "#F0F0F0",
        "tree_heading_bg": "#333333",
        "tree_heading_fg": "#F5A623",
        "tree_select_bg": "#4A3F2A",
        "tree_select_fg": "#F0F0F0",
        "risk_high": "#EF5350",
        "risk_medium": "#F5A623",
        "risk_low": "#66BB6A",
        "import_match_bg": "#3A3020",
        "ctk_mode": "dark",
    },
}

_current_theme: str = THEME_DARK


def get_palette() -> dict:
    return _PALETTE[_current_theme]


def set_theme(mode: str) -> None:
    global _current_theme
    _current_theme = mode
    ctk.set_appearance_mode(_PALETTE[mode]["ctk_mode"])


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
        self.geometry("1400x900")
        self.minsize(900, 600)

        set_theme(THEME_DARK)
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

        # Theme toggle button in the title bar area
        top_bar = ctk.CTkFrame(self, height=36)
        top_bar.pack(fill="x", padx=0, pady=0)
        top_bar.pack_propagate(False)

        pal = get_palette()
        self._theme_btn = ctk.CTkButton(
            top_bar,
            text="☀ Light" if _current_theme == THEME_DARK else "🌙 Dark",
            width=90,
            height=28,
            fg_color=pal["accent"],
            hover_color=pal["accent_hover"],
            text_color=pal["accent_text"],
            command=self._toggle_theme,
        )
        self._theme_btn.pack(side="right", padx=8, pady=4)

        # Create tab view
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=8, pady=(0, 8))

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

    def _toggle_theme(self) -> None:
        global _current_theme
        new_mode = THEME_LIGHT if _current_theme == THEME_DARK else THEME_DARK
        set_theme(new_mode)
        self._configure_styles()
        pal = get_palette()
        label = "☀ Light" if new_mode == THEME_DARK else "🌙 Dark"
        self._theme_btn.configure(
            text=label,
            fg_color=pal["accent"],
            hover_color=pal["accent_hover"],
            text_color=pal["accent_text"],
        )
        # Notify modules that support theme refresh
        for mod in self._active_modules:
            if hasattr(mod, "on_theme_change"):
                try:
                    mod.on_theme_change()
                except Exception:
                    pass

    def _configure_styles(self) -> None:
        pal = get_palette()
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure(
            "Treeview",
            background=pal["tree_bg"],
            foreground=pal["tree_fg"],
            fieldbackground=pal["tree_bg"],
            rowheight=30,
            font=("Segoe UI", 11),
        )
        style.configure(
            "Treeview.Heading",
            background=pal["tree_heading_bg"],
            foreground=pal["tree_heading_fg"],
            font=("Segoe UI", 11, "bold"),
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", pal["tree_select_bg"])],
            foreground=[("selected", pal["tree_select_fg"])],
        )
