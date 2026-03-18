from __future__ import annotations

import os
from tkinter import StringVar, messagebox, ttk

import customtkinter as ctk

from core.models import ActionPlan
from core.scanners import scan_archives
from gui.module_api import AppContext, BaseModule


class ArchiveModule(BaseModule):
    module_id = "archives"
    title = "Archive"

    def build(self, container, app, context: AppContext) -> None:
        ctk.CTkLabel(container, text="Archive & Installer", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=8)

        self.archive_folder_var = StringVar(value=os.path.expanduser("~/Downloads"))
        ctk.CTkEntry(container, textvariable=self.archive_folder_var, width=500).pack(pady=5)
        ctk.CTkButton(container, text="Ordner scannen", command=self.scan).pack(pady=5)

        self.archive_tree = ttk.Treeview(container, columns=("Pfad", "Typ", "Größe", "Status", "Overlap"), show="headings", height=14)
        for col, width in [("Pfad", 500), ("Typ", 80), ("Größe", 80), ("Status", 140), ("Overlap", 80)]:
            self.archive_tree.heading(col, text=col)
            self.archive_tree.column(col, width=width, anchor="w")
        self.archive_tree.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkButton(container, text="Ausgewählte Archive in Plan", fg_color="red", command=lambda: self.add_selected(context)).pack(pady=8)

    def scan(self) -> None:
        for item in self.archive_tree.get_children():
            self.archive_tree.delete(item)
        for archive in scan_archives(self.archive_folder_var.get()):
            self.archive_tree.insert(
                "",
                "end",
                values=(archive.path, archive.file_type, f"{archive.size_mb:.1f} MB", archive.status, "Ja" if archive.overlap_installed else "Nein"),
            )

    def add_selected(self, context: AppContext) -> None:
        for item in self.archive_tree.selection():
            path = str(self.archive_tree.item(item)["values"][0])
            context.planner.add(
                ActionPlan(
                    action_type="delete",
                    target=f'del /f "{path}"',
                    description=f"Archiv löschen: {os.path.basename(path)}",
                    impact_mb=10.0,
                    risk="Medium",
                )
            )
        messagebox.showinfo("Plan", "Archive zum Plan hinzugefügt")
