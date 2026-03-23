from __future__ import annotations

import threading
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

        tree_frame = ctk.CTkFrame(container)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("Name", "Pfad", "Enabled", "Kritisch", "Status", "Letzter Run", "Ausführen als")
        self.tasks_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=16)
        for col, width in [("Name", 220), ("Pfad", 280), ("Enabled", 80), ("Kritisch", 80), ("Status", 100), ("Letzter Run", 140), ("Ausführen als", 140)]:
            self.tasks_tree.heading(col, text=col)
            self.tasks_tree.column(col, width=width, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tasks_tree.yview)
        self.tasks_tree.configure(yscrollcommand=vsb.set)
        self.tasks_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Color coding
        self.tasks_tree.tag_configure("critical", foreground="#e74c3c")
        self.tasks_tree.tag_configure("disabled", foreground="#7f8c8d")
        self.tasks_tree.tag_configure("enabled", foreground="#2ecc71")

        self.tasks_tree.bind("<<TreeviewSelect>>", self._show_detail)

        # Detail panel
        self.detail_box = ctk.CTkTextbox(container, height=80, wrap="word")
        self.detail_box.pack(fill="x", padx=10, pady=4)

        frame = ctk.CTkFrame(container)
        frame.pack(pady=8)
        self.scan_btn = ctk.CTkButton(frame, text="Tasks scannen", command=self._scan_threaded)
        self.scan_btn.pack(side="left", padx=5)
        ctk.CTkButton(frame, text="Gaming-Preset", command=lambda: self.apply_preset(context, "Gaming")).pack(side="left", padx=5)
        ctk.CTkButton(frame, text="Minimal-Preset", command=lambda: self.apply_preset(context, "Minimal")).pack(side="left", padx=5)

        self.progress = ctk.CTkProgressBar(container, mode="indeterminate")
        self._all_tasks: list = []

    def _scan_threaded(self) -> None:
        self.scan_btn.configure(state="disabled")
        self.progress.pack(fill="x", padx=10, pady=2)
        self.progress.start()
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self) -> None:
        tasks = scan_scheduled_tasks()
        self._all_tasks = tasks
        self.tasks_tree.after(0, self._finish_scan)

    def _finish_scan(self) -> None:
        self.progress.stop()
        self.progress.pack_forget()
        self.scan_btn.configure(state="normal")
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)
        for task in self._all_tasks:
            if task.is_critical:
                tag = "critical"
            elif not task.enabled:
                tag = "disabled"
            else:
                tag = "enabled"
            self.tasks_tree.insert(
                "",
                "end",
                values=(
                    task.name[:50],
                    task.path[:60],
                    "Ja" if task.enabled else "Nein",
                    "⚠️ JA" if task.is_critical else "Nein",
                    task.status[:20],
                    task.last_run[:20],
                    task.run_as[:30],
                ),
                tags=(tag,),
                iid=task.path,
            )

    def _show_detail(self, _event=None) -> None:
        selection = self.tasks_tree.selection()
        if not selection:
            return
        task_path = selection[0]
        task = next((t for t in self._all_tasks if t.path == task_path), None)
        if not task:
            return
        detail = (
            f"Pfad: {task.path}\n"
            f"Status: {task.status}  |  Enabled: {'Ja' if task.enabled else 'Nein'}  |  Kritisch: {'JA' if task.is_critical else 'Nein'}\n"
            f"Ausführen als: {task.run_as or '—'}  |  Letzter Run: {task.last_run or '—'}  |  Nächster Run: {task.next_run or '—'}\n"
            f"Beschreibung: {task.description or '—'}"
        )
        self.detail_box.delete("1.0", "end")
        self.detail_box.insert("1.0", detail)

    def apply_preset(self, context: AppContext, mode: str) -> None:
        for action in create_service_preset(mode):
            context.planner.add(action)
        messagebox.showinfo("Preset", f"{mode}-Preset hinzugefügt")
