from __future__ import annotations

import json
from pathlib import Path
from tkinter import messagebox, ttk

import customtkinter as ctk

from gui.module_api import AppContext, BaseModule


class MicroAppsModule(BaseModule):
    module_id = "micro_apps"
    title = "Add-ons (Nightly)"

    def build(self, container, app, context: AppContext) -> None:
        ctk.CTkLabel(container, text="Übersicht der Add-ons (Pre-production/Nightly)", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=8)
        self.tree = ttk.Treeview(container, columns=("Name", "Kategorie", "Risiko", "Script", "Beschreibung"), show="headings", height=16)
        for col, width in [("Name", 220), ("Kategorie", 130), ("Risiko", 80), ("Script", 360), ("Beschreibung", 460)]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkButton(container, text="Katalog neu laden", command=self.load_catalog).pack(pady=6)
        ctk.CTkButton(container, text="Startbefehl kopieren", command=self.copy_command).pack(pady=2)
        self.load_catalog()

    def load_catalog(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        catalog_path = Path(__file__).resolve().parents[2] / "micro_apps" / "catalog.json"
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        for app in data.get("apps", []):
            self.tree.insert(
                "",
                "end",
                values=(app["name"], app["category"], app["risk"], app["script"], app["description"]),
            )

    def copy_command(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        script = self.tree.item(selected[0])["values"][3]
        cmd = f'python "{script}"'
        self.tree.clipboard_clear()
        self.tree.clipboard_append(cmd)
        messagebox.showinfo("Befehl", f"In die Zwischenablage kopiert:\n{cmd}")
