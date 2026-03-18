from __future__ import annotations

from tkinter import messagebox, ttk

import customtkinter as ctk

from core.scanners import scan_scheduled_tasks
from core.services import create_service_preset
from gui.module_api import AppContext, BaseModule


class TasksServicesModule(BaseModule):
    module_id = "tasks_services"
    title = "Tasks & Services"

    def build(self, container, app, context: AppContext) -> None:
        ctk.CTkLabel(container, text="Scheduled Tasks und Service-Presets", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=8)

        self.tasks_tree = ttk.Treeview(container, columns=("Name", "Pfad", "Enabled", "Critical"), show="headings", height=13)
        for col, width in [("Name", 280), ("Pfad", 420), ("Enabled", 90), ("Critical", 90)]:
            self.tasks_tree.heading(col, text=col)
            self.tasks_tree.column(col, width=width, anchor="w")
        self.tasks_tree.pack(fill="both", expand=True, padx=10, pady=5)

        frame = ctk.CTkFrame(container)
        frame.pack(pady=8)
        ctk.CTkButton(frame, text="Tasks scannen", command=self.scan).pack(side="left", padx=5)
        ctk.CTkButton(frame, text="Gaming-Preset", command=lambda: self.apply_preset(context, "Gaming")).pack(side="left", padx=5)
        ctk.CTkButton(frame, text="Minimal-Preset", command=lambda: self.apply_preset(context, "Minimal")).pack(side="left", padx=5)

    def scan(self) -> None:
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)
        for task in scan_scheduled_tasks():
            self.tasks_tree.insert("", "end", values=(task.name, task.path, task.enabled, task.is_critical))

    def apply_preset(self, context: AppContext, mode: str) -> None:
        for action in create_service_preset(mode):
            context.planner.add(action)
        messagebox.showinfo("Preset", f"{mode}-Preset hinzugefügt")
