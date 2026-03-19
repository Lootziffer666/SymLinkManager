from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import customtkinter as ctk

from scanners.known_paths import scan_known_paths
from scanners.rule_based import load_rule_packs
from shared.core.models import ExecutionMode, PurgeItem
from shared.engine.execution import ExecutionEngine

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class TabulaRasaApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tabula Rasa – Purge safely. Reclaim space.")
        self.geometry("1480x980")

        self.engine = ExecutionEngine()
        self.current_items: list[PurgeItem] = []

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)
        for tab_name in ["Scan", "Plan", "Run", "History"]:
            self.tabview.add(tab_name)

        self._build_scan_screen()
        self._build_plan_screen()
        self._build_run_screen()
        self._build_history_screen()
        self.refresh_history()

    def _build_scan_screen(self) -> None:
        tab = self.tabview.tab("Scan")
        ctk.CTkLabel(tab, text="Purge Map – disposable data first", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=12)
        ctk.CTkButton(tab, text="Scan purge candidates", command=self.start_scan).pack(pady=6)

        columns = ("Selected", "Name", "Kind", "Size", "Risk", "Action", "Review", "Path")
        self.scan_tree = ttk.Treeview(tab, columns=columns, show="headings", height=20)
        for col, width in zip(columns, [80, 220, 140, 100, 90, 100, 90, 480]):
            self.scan_tree.heading(col, text=col)
            self.scan_tree.column(col, width=width, anchor="w")
        self.scan_tree.pack(fill="both", expand=True, padx=12, pady=8)
        self.scan_tree.bind("<Double-1>", self.toggle_selected)
        self.scan_tree.bind("<<TreeviewSelect>>", self.show_details)

        self.detail_text = ctk.CTkTextbox(tab, height=180)
        self.detail_text.pack(fill="x", padx=12, pady=8)

    def _build_plan_screen(self) -> None:
        tab = self.tabview.tab("Plan")
        ctk.CTkLabel(tab, text="Plan – presets and deletion modes", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=12)
        button_frame = ctk.CTkFrame(tab)
        button_frame.pack(pady=8)
        ctk.CTkButton(button_frame, text="Safe Cleanup", command=lambda: self.apply_preset("safe")).pack(side="left", padx=6)
        ctk.CTkButton(button_frame, text="Aggressive Cleanup", command=lambda: self.apply_preset("aggressive")).pack(side="left", padx=6)
        ctk.CTkButton(button_frame, text="Orphaned App Data Review", command=lambda: self.apply_preset("orphaned")).pack(side="left", padx=6)
        self.plan_text = ctk.CTkTextbox(tab, height=360)
        self.plan_text.pack(fill="both", expand=True, padx=12, pady=8)
        self.mode_var = tk.StringVar(value=ExecutionMode.DRY_RUN.value)
        ctk.CTkOptionMenu(tab, values=[mode.value for mode in ExecutionMode], variable=self.mode_var).pack(pady=6)
        ctk.CTkButton(tab, text="Preview current plan", command=self.preview_plan).pack(pady=6)

    def _build_run_screen(self) -> None:
        tab = self.tabview.tab("Run")
        ctk.CTkLabel(tab, text="Run – dry-run first, safe mode preferred", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=12)
        ctk.CTkButton(tab, text="Execute plan", fg_color="#17803d", command=self.execute_plan).pack(pady=6)
        self.run_text = ctk.CTkTextbox(tab, height=420)
        self.run_text.pack(fill="both", expand=True, padx=12, pady=8)

    def _build_history_screen(self) -> None:
        tab = self.tabview.tab("History")
        ctk.CTkLabel(tab, text="History – ledger, export, re-check", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=12)
        ctk.CTkButton(tab, text="Refresh history", command=self.refresh_history).pack(pady=6)
        ctk.CTkButton(tab, text="Export JSON + CSV", command=self.export_history).pack(pady=6)
        ctk.CTkButton(tab, text='"What would I delete today?"', command=self.show_today_summary).pack(pady=6)
        self.history_text = ctk.CTkTextbox(tab, height=400)
        self.history_text.pack(fill="both", expand=True, padx=12, pady=8)

    def start_scan(self) -> None:
        self.current_items = scan_known_paths() + load_rule_packs()
        self.render_scan_items()

    def render_scan_items(self) -> None:
        for row in self.scan_tree.get_children():
            self.scan_tree.delete(row)
        for item in self.current_items:
            self.scan_tree.insert("", "end", values=("Yes" if item.selected else "No", item.display_name, item.kind.value, item.size_human, item.risk_level.value, item.recommended_action.value, "Yes" if item.review_required else "No", item.path))

    def toggle_selected(self, _event=None) -> None:
        selection = self.scan_tree.selection()
        if not selection:
            return
        index = self.scan_tree.index(selection[0])
        self.current_items[index].selected = not self.current_items[index].selected
        self.render_scan_items()

    def show_details(self, _event=None) -> None:
        selection = self.scan_tree.selection()
        if not selection:
            return
        index = self.scan_tree.index(selection[0])
        item = self.current_items[index]
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", f"Path: {item.path}\nKind: {item.kind.value}\nRisk: {item.risk_level.value}\nRecommended: {item.recommended_action.value}\nReview required: {'Yes' if item.review_required else 'No'}\nNotes: {item.notes or '—'}")

    def apply_preset(self, preset: str) -> None:
        for item in self.current_items:
            item.selected = False
            if preset == "safe":
                item.selected = item.risk_level.value == "Low" and not item.review_required
                self.mode_var.set(ExecutionMode.SAFE.value)
            elif preset == "aggressive":
                item.selected = item.recommended_action.value in {"Purge", "Review"}
                self.mode_var.set(ExecutionMode.AGGRESSIVE.value)
            elif preset == "orphaned":
                item.selected = item.kind.value in {"AppResidue", "OrphanedAppData"}
                self.mode_var.set(ExecutionMode.DRY_RUN.value)
        self.render_scan_items()
        self.plan_text.delete("1.0", "end")
        self.plan_text.insert("1.0", f"Preset applied: {preset}\nDouble-click rows in Scan to fine-tune selection.")

    def preview_plan(self) -> None:
        mode = ExecutionMode(self.mode_var.get())
        preview = self.engine.preview(self.current_items, mode)
        self.plan_text.delete("1.0", "end")
        self.plan_text.insert("1.0", preview)

    def execute_plan(self) -> None:
        mode = ExecutionMode(self.mode_var.get())
        if mode == ExecutionMode.AGGRESSIVE and not messagebox.askyesno("Tabula Rasa", "Aggressive mode permanently deletes data. Continue?"):
            return
        results = self.engine.execute(self.current_items, mode)
        self.run_text.delete("1.0", "end")
        self.run_text.insert("1.0", "\n".join(results) or "No items selected.")
        self.refresh_history()

    def refresh_history(self) -> None:
        self.history_text.delete("1.0", "end")
        runs = self.engine.ledger.load()
        if not runs:
            self.history_text.insert("1.0", "No purge runs recorded yet.")
            return
        for run in runs:
            self.history_text.insert("end", f"{run.started_at.isoformat()} | {run.mode.value} | selected={run.selected_item_count} | estimated={run.estimated_bytes}\n")

    def export_history(self) -> None:
        base = Path(self.engine.base_dir)
        json_path = self.engine.ledger.export_json(base / "history_export.json")
        csv_path = self.engine.ledger.export_csv(base / "history_export.csv")
        messagebox.showinfo("Tabula Rasa", f"Exported to {json_path} and {csv_path}")

    def show_today_summary(self) -> None:
        items = self.engine.what_would_delete_today()
        self.history_text.insert("end", "\nToday\'s replay:\n" + ("\n".join(items) if items else "No runs today."))
