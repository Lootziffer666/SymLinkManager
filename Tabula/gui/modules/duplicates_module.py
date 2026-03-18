from __future__ import annotations

import os
from tkinter import StringVar, messagebox, ttk

import customtkinter as ctk

from core.duplicate_finder import scan_duplicates, smart_merge_documents
from core.models import ActionPlan
from gui.module_api import AppContext, BaseModule


class DuplicatesModule(BaseModule):
    module_id = "duplicates"
    title = "Duplicates & Fusion"

    def build(self, container, app, context: AppContext) -> None:
        ctk.CTkLabel(container, text="Smart Duplicate Finder + Keep Best", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)

        self.dup_folder_var = StringVar(value=os.path.expanduser("~/Downloads"))
        ctk.CTkEntry(container, textvariable=self.dup_folder_var, width=500).pack(pady=5)
        ctk.CTkButton(container, text="Duplicates scannen", command=lambda: self.scan(context)).pack(pady=8)

        self.dup_tree = ttk.Treeview(container, columns=("Dateien", "Beste Datei", "Score", "Fusion möglich"), show="headings", height=12)
        for col, width in [("Dateien", 540), ("Beste Datei", 300), ("Score", 80), ("Fusion möglich", 110)]:
            self.dup_tree.heading(col, text=col)
            self.dup_tree.column(col, width=width, anchor="w")
        self.dup_tree.pack(fill="both", expand=True, padx=10, pady=5)

        frame = ctk.CTkFrame(container)
        frame.pack(pady=10)
        ctk.CTkButton(frame, text="Vorschau Fusion", fg_color="purple", command=lambda: self.preview_fusion(context)).pack(side="left", padx=5)
        ctk.CTkButton(frame, text="Keep Best in Plan", fg_color="green", command=lambda: self.add_to_plan(context)).pack(side="left", padx=5)

    def scan(self, context: AppContext) -> None:
        groups = scan_duplicates(self.dup_folder_var.get())
        context.state["duplicate_groups"] = groups
        for item in self.dup_tree.get_children():
            self.dup_tree.delete(item)
        for group in groups:
            files_str = ", ".join(f.name for f in group.files)[:100]
            best = group.best_file.name if group.best_file else "-"
            score = max(group.score_dict.values()) if group.score_dict else 0
            self.dup_tree.insert("", "end", values=(files_str, best, f"{score:.1f}", "JA" if group.fusion_possible else "Nein"))

    def preview_fusion(self, context: AppContext) -> None:
        selected = self.dup_tree.selection()
        if not selected:
            return
        groups = context.state.get("duplicate_groups", [])
        group = groups[self.dup_tree.index(selected[0])]
        if not group.fusion_possible or len(group.files) < 2:
            messagebox.showinfo("Info", "Fusion nur mit Text/DOCX/PDF möglich")
            return
        out, preview = smart_merge_documents(group.files[0], group.files[1])
        messagebox.showinfo("Fusion", f"Master-Datei: {out}\n\n{preview}")

    def add_to_plan(self, context: AppContext) -> None:
        selected = self.dup_tree.selection()
        groups = context.state.get("duplicate_groups", [])
        for item in selected:
            group = groups[self.dup_tree.index(item)]
            if not group.best_file:
                continue
            context.planner.add(
                ActionPlan(action_type="keep_merged", target=str(group.best_file), description=f"Keep Best: {group.best_file.name}", risk="Low")
            )
            for file_path in group.files:
                if file_path != group.best_file:
                    context.planner.add(
                        ActionPlan(
                            action_type="delete",
                            target=f'del /f "{file_path}"',
                            description=f"Duplikat löschen: {file_path.name}",
                            risk="Medium",
                        )
                    )
        messagebox.showinfo("Plan", f"{len(selected)} Duplikatgruppen hinzugefügt")
