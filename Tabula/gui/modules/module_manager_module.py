from __future__ import annotations

import json
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from gui.module_api import AppContext, BaseModule


class ModuleManagerModule(BaseModule):
    module_id = "module_manager"
    title = "Module"

    def build(self, container, app, context: AppContext) -> None:
        ctk.CTkLabel(container, text="Barebone-Modulmanager", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=8)
        ctk.CTkLabel(
            container,
            text=(
                "Module können einzeln aktiviert/deaktiviert werden.\n"
                "Änderungen werden in modules.json gespeichert und nach Neustart geladen."
            ),
        ).pack(pady=2)

        self.app = app
        self.vars: dict[str, ctk.BooleanVar] = {}
        list_frame = ctk.CTkScrollableFrame(container, width=920, height=420)
        list_frame.pack(padx=12, pady=12, fill="both", expand=True)

        for module in app.available_modules:
            if module["id"] == self.module_id:
                continue
            value = bool(app.module_config.get(module["id"], True))
            var = ctk.BooleanVar(value=value)
            self.vars[module["id"]] = var
            label = f"{module['title']} ({module['id']})"
            if module["id"] == "micro_apps":
                label += " [Pre-production/Nightly]"
            ctk.CTkCheckBox(
                list_frame,
                text=label,
                variable=var,
            ).pack(anchor="w", pady=4)

        ctk.CTkButton(container, text="Konfiguration speichern", command=self.save).pack(pady=6)

    def save(self) -> None:
        for module_id, var in self.vars.items():
            self.app.module_config[module_id] = bool(var.get())
        config_path = Path(__file__).resolve().parents[2] / "modules.json"
        config_path.write_text(json.dumps(self.app.module_config, indent=2, ensure_ascii=False), encoding="utf-8")
        messagebox.showinfo("Module", "Gespeichert. Bitte Tabula neu starten, um Tabs neu zu laden.")
