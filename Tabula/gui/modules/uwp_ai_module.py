from __future__ import annotations

from tkinter import messagebox, ttk

import customtkinter as ctk

from core.ai_protection import create_recall_protection_plan
from core.debloat import create_safe_debloat_plan
from core.scanners import scan_uwp_apps
from gui.module_api import AppContext, BaseModule


class UwpAiModule(BaseModule):
    module_id = "uwp_ai"
    title = "UWP & AI"

    def build(self, container, app, context: AppContext) -> None:
        ctk.CTkLabel(container, text="UWP-Apps und AI-Schutz", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=8)

        self.uwp_tree = ttk.Treeview(container, columns=("Name", "Package", "AI-related"), show="headings", height=18)
        for col, width in [("Name", 280), ("Package", 640), ("AI-related", 100)]:
            self.uwp_tree.heading(col, text=col)
            self.uwp_tree.column(col, width=width, anchor="w")
        self.uwp_tree.pack(fill="both", expand=True, padx=10, pady=5)

        frame = ctk.CTkFrame(container)
        frame.pack(pady=10)
        ctk.CTkButton(frame, text="UWP scannen", command=self.scan).pack(side="left", padx=5)
        ctk.CTkButton(frame, text="Ausgewählte UWP in Plan", command=lambda: self.add_selected(context)).pack(side="left", padx=5)
        ctk.CTkButton(frame, text="Recall/Copilot Schutz", fg_color="#c0392b", command=lambda: self.add_protection(context)).pack(side="left", padx=5)

    def scan(self) -> None:
        for item in self.uwp_tree.get_children():
            self.uwp_tree.delete(item)
        for app in scan_uwp_apps():
            self.uwp_tree.insert("", "end", values=(app.name, app.package_fullname, "JA" if app.is_ai_related else "Nein"))

    def add_selected(self, context: AppContext) -> None:
        packages = [self.uwp_tree.item(i)["values"][1] for i in self.uwp_tree.selection()]
        for action in create_safe_debloat_plan(packages):
            context.planner.add(action)
        messagebox.showinfo("Plan", f"{len(packages)} UWP-Aktionen hinzugefügt")

    def add_protection(self, context: AppContext) -> None:
        for action in create_recall_protection_plan():
            context.planner.add(action)
        messagebox.showinfo("Plan", "Recall/Copilot-Schutz hinzugefügt")
