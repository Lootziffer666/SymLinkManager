from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import customtkinter as ctk

from core.execution import ExecutionEngine
from core.models import LinkType, TabulaItem
from core.scanners import filter_items, scan_storage_map
from links.link_manager import LinkManager
from relocate.relocator import Relocator

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class TabulaApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tabula – Map. Move. Link.")
        self.geometry("1480x980")

        self.engine = ExecutionEngine()
        self.relocator = Relocator(self.engine)
        self.link_manager = LinkManager(self.engine)
        self.current_items: list[TabulaItem] = []
        self.filtered_items: list[TabulaItem] = []

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)
        for tab_name in ["Map", "Relocate", "Links", "History"]:
            self.tabview.add(tab_name)

        self._build_map_screen()
        self._build_relocate_screen()
        self._build_links_screen()
        self._build_history_screen()
        self.refresh_links()
        self.refresh_history()

    def _build_map_screen(self) -> None:
        tab = self.tabview.tab("Map")
        ctk.CTkLabel(tab, text="Storage Map – visibility before action", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=12)

        controls = ctk.CTkFrame(tab)
        controls.pack(fill="x", padx=12, pady=8)
        ctk.CTkButton(controls, text="Scan storage map", command=self.start_scan).pack(side="left", padx=6)
        self.risk_var = tk.StringVar(value="All")
        self.action_var = tk.StringVar(value="All")
        ctk.CTkOptionMenu(controls, values=["All", "Low", "Medium", "High"], variable=self.risk_var, command=lambda _v: self.apply_filter()).pack(side="left", padx=6)
        ctk.CTkOptionMenu(controls, values=["All", "Keep", "Purge", "Relocate", "Review"], variable=self.action_var, command=lambda _v: self.apply_filter()).pack(side="left", padx=6)

        columns = ("Name", "Kind", "Size", "Risk", "Action", "Owner", "Path")
        self.map_tree = ttk.Treeview(tab, columns=columns, show="headings", height=20)
        for col, width in zip(columns, [220, 130, 100, 90, 110, 140, 520]):
            self.map_tree.heading(col, text=col)
            self.map_tree.column(col, width=width, anchor="w")
        self.map_tree.pack(fill="both", expand=True, padx=12, pady=8)
        self.map_tree.bind("<<TreeviewSelect>>", self.show_detail)

        self.detail_text = ctk.CTkTextbox(tab, height=180)
        self.detail_text.pack(fill="x", padx=12, pady=8)
        ctk.CTkButton(tab, text="Use selected item in Relocate", fg_color="#17803d", command=self.prepare_relocation).pack(pady=6)

    def _build_relocate_screen(self) -> None:
        tab = self.tabview.tab("Relocate")
        ctk.CTkLabel(tab, text="Relocate – move bulky folders safely", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=12)
        self.selected_label = ctk.CTkLabel(tab, text="No item selected yet.")
        self.selected_label.pack(pady=6)

        path_frame = ctk.CTkFrame(tab)
        path_frame.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(path_frame, text="Target root:").pack(side="left", padx=6)
        self.target_var = tk.StringVar(value="D:/RelocatedCaches")
        ctk.CTkEntry(path_frame, textvariable=self.target_var, width=340).pack(side="left", padx=6)
        self.link_type_var = tk.StringVar(value=LinkType.JUNCTION.value)
        ctk.CTkOptionMenu(path_frame, values=[lt.value for lt in LinkType], variable=self.link_type_var).pack(side="left", padx=6)

        ctk.CTkButton(tab, text="Preview relocation", command=self.preview_relocation).pack(pady=6)
        ctk.CTkButton(tab, text="Record relocation plan", fg_color="#17803d", command=self.record_relocation_plan).pack(pady=6)
        self.preview_text = ctk.CTkTextbox(tab, height=360)
        self.preview_text.pack(fill="both", expand=True, padx=12, pady=8)

    def _build_links_screen(self) -> None:
        tab = self.tabview.tab("Links")
        ctk.CTkLabel(tab, text="Managed links", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=12)
        columns = ("Source", "Target", "Type", "Status", "Validated")
        self.links_tree = ttk.Treeview(tab, columns=columns, show="headings", height=18)
        for col, width in zip(columns, [360, 360, 90, 100, 100]):
            self.links_tree.heading(col, text=col)
            self.links_tree.column(col, width=width, anchor="w")
        self.links_tree.pack(fill="both", expand=True, padx=12, pady=8)
        ctk.CTkButton(tab, text="Validate all links", command=self.validate_links).pack(pady=6)

    def _build_history_screen(self) -> None:
        tab = self.tabview.tab("History")
        ctk.CTkLabel(tab, text="History & export", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=12)
        ctk.CTkButton(tab, text="Refresh history", command=self.refresh_history).pack(pady=6)
        ctk.CTkButton(tab, text="Export history JSON", command=self.export_history).pack(pady=6)
        self.history_text = ctk.CTkTextbox(tab, height=420)
        self.history_text.pack(fill="both", expand=True, padx=12, pady=8)

    def start_scan(self) -> None:
        self.current_items = scan_storage_map()
        self.apply_filter()

    def apply_filter(self) -> None:
        risk = self.risk_var.get()
        action = self.action_var.get()
        normalized_risk = "All" if risk == "All" else risk
        self.filtered_items = filter_items(self.current_items, risk=normalized_risk, action=action)
        for row in self.map_tree.get_children():
            self.map_tree.delete(row)
        for item in self.filtered_items:
            self.map_tree.insert("", "end", values=(item.display_name, item.kind.value, item.size_human, item.risk_level.value, item.recommended_action.value, item.owner_hint or "—", item.path))

    def _selected_item(self) -> TabulaItem | None:
        selection = self.map_tree.selection()
        if not selection:
            return None
        index = self.map_tree.index(selection[0])
        if index >= len(self.filtered_items):
            return None
        return self.filtered_items[index]

    def show_detail(self, _event=None) -> None:
        item = self._selected_item()
        if not item:
            return
        details = (
            f"Path: {item.path}\n"
            f"Kind: {item.kind.value}\n"
            f"Risk: {item.risk_level.value}\n"
            f"Recommended action: {item.recommended_action.value}\n"
            f"Size: {item.size_human} ({item.item_count or 0} files)\n"
            f"Owner: {item.owner_hint or 'Unknown'}\n"
            f"Detection: {item.source_type}\n"
            f"Notes: {item.notes or '—'}"
        )
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", details)

    def prepare_relocation(self) -> None:
        item = self._selected_item()
        if not item:
            messagebox.showinfo("Tabula", "Please select an item on the Map tab first.")
            return
        self.selected_item = item
        self.selected_label.configure(text=f"Selected: {item.display_name} ({item.size_human})")
        self.tabview.set("Relocate")
        self.preview_relocation()

    def preview_relocation(self) -> None:
        item = getattr(self, "selected_item", None)
        if not item:
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "Select an item from Map first.")
            return
        preview = self.relocator.preview(item, self.target_var.get(), LinkType(self.link_type_var.get()))
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", preview)

    def record_relocation_plan(self) -> None:
        item = getattr(self, "selected_item", None)
        if not item:
            messagebox.showinfo("Tabula", "Select an item from Map first.")
            return
        record = self.relocator.plan(item, self.target_var.get(), LinkType(self.link_type_var.get()))
        self.preview_text.insert("end", f"\n\nRecorded plan: {record.id}")
        self.refresh_links()
        self.refresh_history()
        messagebox.showinfo("Tabula", "Relocation plan recorded in the local ledger.")

    def refresh_links(self) -> None:
        for row in self.links_tree.get_children():
            self.links_tree.delete(row)
        for record in self.link_manager.load_links():
            self.links_tree.insert("", "end", values=(record.source_path, record.target_path, record.link_type.value, record.status, "Yes" if record.validated else "No"))

    def validate_links(self) -> None:
        self.link_manager.validate_all()
        self.refresh_links()
        self.refresh_history()
        messagebox.showinfo("Tabula", "Link validation complete.")

    def refresh_history(self) -> None:
        self.history_text.delete("1.0", "end")
        records = self.engine.ledger.load()
        if not records:
            self.history_text.insert("1.0", "No relocation history recorded yet.")
            return
        for record in records:
            self.history_text.insert("end", f"{record.created_at.isoformat()} | {record.source_path} -> {record.target_path} | {record.link_type.value} | {record.status}\n")

    def export_history(self) -> None:
        destination = Path(self.engine.base_dir) / "history_export.json"
        self.engine.ledger.export_json(destination)
        messagebox.showinfo("Tabula", f"History exported to {destination}")
