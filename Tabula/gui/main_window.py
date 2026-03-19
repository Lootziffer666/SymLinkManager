from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import customtkinter as ctk

from core.execution import ExecutionEngine
from core.models import ProgramEntry, RecommendedAction, StorageItem, LinkType
from core.scanners import build_purge_plan, filter_programs, filter_storage, relocation_candidates, scan_installed_programs, scan_storage_items
from links.link_manager import LinkManager
from relocate.relocator import Relocator

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class TabulaApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tabula – Find it. Clear it. Move it.")
        self.geometry("1920x1180")
        self.minsize(1600, 980)

        self._configure_styles()

        self.engine = ExecutionEngine()
        self.relocator = Relocator(self.engine)
        self.link_manager = LinkManager(self.engine)

        self.program_items: list[ProgramEntry] = []
        self.visible_program_items: list[ProgramEntry] = []
        self.storage_items: list[StorageItem] = []
        self.visible_storage_items: list[StorageItem] = []
        self.purge_items: list[StorageItem] = []
        self.selected_relocation_item: StorageItem | None = None

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=16)
        for tab_name in ["Inventory", "Purge", "Relocate", "Links", "History"]:
            self.tabview.add(tab_name)

        self._build_inventory_screen()
        self._build_purge_screen()
        self._build_relocate_screen()
        self._build_links_screen()
        self._build_history_screen()
        self.refresh_links()
        self.refresh_history()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", rowheight=34, font=("Segoe UI", 12))
        style.configure("Treeview.Heading", font=("Segoe UI", 12, "bold"))

    def _build_inventory_screen(self) -> None:
        tab = self.tabview.tab("Inventory")
        ctk.CTkLabel(tab, text="Inventory – software truth + storage truth", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(12, 6))

        controls = ctk.CTkFrame(tab)
        controls.pack(fill="x", padx=12, pady=8)
        ctk.CTkButton(controls, text="Scan Programs", width=180, height=38, command=self.scan_programs).pack(side="left", padx=6, pady=6)
        ctk.CTkButton(controls, text="Scan Storage", width=180, height=38, command=self.scan_storage).pack(side="left", padx=6, pady=6)
        ctk.CTkButton(controls, text="Scan Both", width=180, height=38, fg_color="#1f7a3f", command=self.scan_all).pack(side="left", padx=6, pady=6)

        self.program_query = tk.StringVar()
        self.hide_microsoft = tk.BooleanVar(value=True)
        self.hide_runtimes = tk.BooleanVar(value=True)
        self.hide_drivers = tk.BooleanVar(value=True)
        self.hide_hotfixes = tk.BooleanVar(value=True)
        self.large_only = tk.BooleanVar(value=False)
        self.storage_risk_var = tk.StringVar(value="All")
        self.storage_action_var = tk.StringVar(value="All")
        self.inventory_status = tk.StringVar(value="Run a scan to build the software and storage decision surface.")

        filter_bar = ctk.CTkFrame(tab)
        filter_bar.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkEntry(filter_bar, textvariable=self.program_query, width=260, placeholder_text="Search program names").pack(side="left", padx=6, pady=6)
        ctk.CTkButton(filter_bar, text="Apply Filters", width=150, command=self.apply_inventory_filters).pack(side="left", padx=6, pady=6)
        for text, var in [
            ("Hide Microsoft", self.hide_microsoft),
            ("Hide Runtimes", self.hide_runtimes),
            ("Hide Drivers", self.hide_drivers),
            ("Hide Hotfixes", self.hide_hotfixes),
            ("Large only", self.large_only),
        ]:
            ctk.CTkCheckBox(filter_bar, text=text, variable=var, command=self.apply_inventory_filters).pack(side="left", padx=8, pady=6)
        ctk.CTkOptionMenu(filter_bar, values=["All", "Low", "Medium", "High"], variable=self.storage_risk_var, command=lambda _v: self.apply_inventory_filters()).pack(side="right", padx=6, pady=6)
        ctk.CTkOptionMenu(filter_bar, values=["All", "Keep", "Purge", "Relocate", "Review"], variable=self.storage_action_var, command=lambda _v: self.apply_inventory_filters()).pack(side="right", padx=6, pady=6)

        ctk.CTkLabel(tab, textvariable=self.inventory_status, anchor="w", justify="left", font=ctk.CTkFont(size=14)).pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(tab, text="Programs", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=12)
        program_cols = ("Name", "Type", "Category", "Risk", "Estimated Size", "Legal", "Duplicates", "Install Path")
        self.program_tree = ttk.Treeview(tab, columns=program_cols, show="headings", height=10)
        for col, width in zip(program_cols, [280, 120, 130, 90, 120, 120, 90, 520]):
            self.program_tree.heading(col, text=col)
            self.program_tree.column(col, width=width, anchor="w")
        self.program_tree.pack(fill="both", expand=True, padx=12, pady=(4, 10))
        self.program_tree.bind("<<TreeviewSelect>>", self.show_program_detail)

        ctk.CTkLabel(tab, text="Storage candidates", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=12)
        storage_cols = ("Name", "Kind", "Risk", "Recommended", "Total", "Reclaimable", "Movable", "Owner", "Path")
        self.storage_tree = ttk.Treeview(tab, columns=storage_cols, show="headings", height=10)
        for col, width in zip(storage_cols, [220, 130, 90, 120, 110, 120, 120, 150, 520]):
            self.storage_tree.heading(col, text=col)
            self.storage_tree.column(col, width=width, anchor="w")
        self.storage_tree.pack(fill="both", expand=True, padx=12, pady=(4, 10))
        self.storage_tree.bind("<<TreeviewSelect>>", self.show_storage_detail)

        self.inventory_detail = ctk.CTkTextbox(tab, height=180, font=("Consolas", 14))
        self.inventory_detail.pack(fill="x", padx=12, pady=(0, 10))
        self.inventory_detail.insert("1.0", "No scan results yet.")

    def _build_purge_screen(self) -> None:
        tab = self.tabview.tab("Purge")
        ctk.CTkLabel(tab, text="Purge – clear what can go", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(12, 6))
        self.purge_status = tk.StringVar(value="Scan storage first, then choose a preset.")
        ctk.CTkLabel(tab, textvariable=self.purge_status, font=ctk.CTkFont(size=14)).pack(anchor="w", padx=12)

        preset_frame = ctk.CTkFrame(tab)
        preset_frame.pack(fill="x", padx=12, pady=8)
        for preset in ["Safe Cleanup", "Cache Reset", "Launcher Cleanup", "Residue Review", "Media Capture Review"]:
            ctk.CTkButton(preset_frame, text=preset, width=170, height=38, command=lambda p=preset: self.apply_purge_preset(p)).pack(side="left", padx=6, pady=6)
        ctk.CTkButton(preset_frame, text="Dry Run", width=140, height=38, fg_color="#386fa4", command=self.preview_purge).pack(side="right", padx=6, pady=6)
        ctk.CTkButton(preset_frame, text="Execute Plan", width=140, height=38, fg_color="#1f7a3f", command=self.execute_purge).pack(side="right", padx=6, pady=6)

        purge_cols = ("Name", "Kind", "Risk", "Recommended", "Total", "Reclaimable", "Movable", "Path")
        self.purge_tree = ttk.Treeview(tab, columns=purge_cols, show="headings", height=18)
        for col, width in zip(purge_cols, [220, 130, 90, 120, 110, 120, 120, 720]):
            self.purge_tree.heading(col, text=col)
            self.purge_tree.column(col, width=width, anchor="w")
        self.purge_tree.pack(fill="both", expand=True, padx=12, pady=8)

        self.purge_text = ctk.CTkTextbox(tab, height=200, font=("Consolas", 14))
        self.purge_text.pack(fill="x", padx=12, pady=(0, 10))

    def _build_relocate_screen(self) -> None:
        tab = self.tabview.tab("Relocate")
        ctk.CTkLabel(tab, text="Relocate – move what must stay", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(12, 6))
        self.relocate_status = tk.StringVar(value="Choose a storage item with meaningful movable size.")
        ctk.CTkLabel(tab, textvariable=self.relocate_status, font=ctk.CTkFont(size=14)).pack(anchor="w", padx=12)

        relocate_cols = ("Name", "Kind", "Risk", "Recommended", "Movable", "Owner", "Path")
        self.relocate_tree = ttk.Treeview(tab, columns=relocate_cols, show="headings", height=16)
        for col, width in zip(relocate_cols, [240, 130, 90, 120, 120, 150, 760]):
            self.relocate_tree.heading(col, text=col)
            self.relocate_tree.column(col, width=width, anchor="w")
        self.relocate_tree.pack(fill="both", expand=True, padx=12, pady=8)
        self.relocate_tree.bind("<<TreeviewSelect>>", self.on_relocate_selected)

        controls = ctk.CTkFrame(tab)
        controls.pack(fill="x", padx=12, pady=8)
        self.target_var = tk.StringVar(value="D:/TabulaRelocated")
        self.link_type_var = tk.StringVar(value=LinkType.JUNCTION.value)
        ctk.CTkLabel(controls, text="Target root:").pack(side="left", padx=6)
        ctk.CTkEntry(controls, textvariable=self.target_var, width=420).pack(side="left", padx=6)
        ctk.CTkOptionMenu(controls, values=[lt.value for lt in LinkType], variable=self.link_type_var).pack(side="left", padx=6)
        ctk.CTkButton(controls, text="Preview relocation", width=180, command=self.preview_relocation).pack(side="left", padx=6)
        ctk.CTkButton(controls, text="Record relocation", width=180, fg_color="#1f7a3f", command=self.record_relocation).pack(side="left", padx=6)

        self.relocate_text = ctk.CTkTextbox(tab, height=240, font=("Consolas", 14))
        self.relocate_text.pack(fill="x", padx=12, pady=(0, 10))

    def _build_links_screen(self) -> None:
        tab = self.tabview.tab("Links")
        ctk.CTkLabel(tab, text="Links – visible routing layer", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(12, 6))
        cols = ("Original Path", "Target Path", "Type", "Status", "Validated", "Owner")
        self.links_tree = ttk.Treeview(tab, columns=cols, show="headings", height=20)
        for col, width in zip(cols, [420, 420, 90, 100, 100, 220]):
            self.links_tree.heading(col, text=col)
            self.links_tree.column(col, width=width, anchor="w")
        self.links_tree.pack(fill="both", expand=True, padx=12, pady=8)
        ctk.CTkButton(tab, text="Validate all links", width=180, height=38, command=self.validate_links).pack(pady=(0, 10))

    def _build_history_screen(self) -> None:
        tab = self.tabview.tab("History")
        ctk.CTkLabel(tab, text="History – purge, relocate, link actions", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(12, 6))
        controls = ctk.CTkFrame(tab)
        controls.pack(fill="x", padx=12, pady=8)
        ctk.CTkButton(controls, text="Refresh history", width=160, command=self.refresh_history).pack(side="left", padx=6, pady=6)
        ctk.CTkButton(controls, text="Export relocations", width=160, command=self.export_relocations).pack(side="left", padx=6, pady=6)
        ctk.CTkButton(controls, text="Export actions", width=160, command=self.export_actions).pack(side="left", padx=6, pady=6)
        self.history_text = ctk.CTkTextbox(tab, height=720, font=("Consolas", 14))
        self.history_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))

    def scan_programs(self) -> None:
        self.program_items = scan_installed_programs()
        self.apply_inventory_filters()
        self._update_inventory_status()

    def scan_storage(self) -> None:
        self.storage_items = scan_storage_items()
        self.apply_inventory_filters()
        self._refresh_purge_screen()
        self._refresh_relocate_screen()
        self._update_inventory_status()

    def scan_all(self) -> None:
        self.scan_programs()
        self.scan_storage()
        self._update_inventory_status(force_text="Inventory refreshed: programs + storage candidates loaded.")

    def apply_inventory_filters(self) -> None:
        self.visible_program_items = filter_programs(
            self.program_items,
            query=self.program_query.get(),
            hide_microsoft=self.hide_microsoft.get(),
            hide_runtimes=self.hide_runtimes.get(),
            hide_drivers=self.hide_drivers.get(),
            hide_hotfixes=self.hide_hotfixes.get(),
            large_only=self.large_only.get(),
        )
        self.visible_storage_items = filter_storage(
            self.storage_items,
            risk=self.storage_risk_var.get(),
            action=self.storage_action_var.get(),
        )
        self._render_programs()
        self._render_storage()
        self._refresh_purge_screen()
        self._refresh_relocate_screen()
        self._update_inventory_status()

    def _render_programs(self) -> None:
        for row in self.program_tree.get_children():
            self.program_tree.delete(row)
        for item in self.visible_program_items:
            self.program_tree.insert(
                "",
                "end",
                values=(
                    item.raw_display_name,
                    item.record_type.value,
                    item.category.value,
                    item.risk_level.value,
                    item.estimated_total_human,
                    item.legal_status.value,
                    item.duplicate_count,
                    item.install_location,
                ),
            )

    def _render_storage(self) -> None:
        for row in self.storage_tree.get_children():
            self.storage_tree.delete(row)
        for item in self.visible_storage_items:
            self.storage_tree.insert(
                "",
                "end",
                values=(
                    item.display_name,
                    item.kind.value,
                    item.risk_level.value,
                    item.recommended_action.value,
                    self._fmt_bytes(item.total_bytes),
                    self._fmt_bytes(item.reclaimable_bytes),
                    self._fmt_bytes(item.movable_bytes),
                    item.owner_hint or "—",
                    item.path,
                ),
            )

    def _refresh_purge_screen(self) -> None:
        if not self.storage_items:
            return
        if not self.purge_items:
            self.purge_items = build_purge_plan(self.visible_storage_items or self.storage_items, "Safe Cleanup")
        self._render_purge_items()

    def _render_purge_items(self) -> None:
        for row in self.purge_tree.get_children():
            self.purge_tree.delete(row)
        for item in self.purge_items:
            self.purge_tree.insert(
                "",
                "end",
                values=(
                    item.display_name,
                    item.kind.value,
                    item.risk_level.value,
                    item.recommended_action.value,
                    self._fmt_bytes(item.total_bytes),
                    self._fmt_bytes(item.reclaimable_bytes),
                    self._fmt_bytes(item.movable_bytes),
                    item.path,
                ),
            )
        total = sum(item.reclaimable_bytes for item in self.purge_items)
        self.purge_status.set(f"{len(self.purge_items)} item(s) in purge plan • reclaimable {self._fmt_bytes(total)}")

    def apply_purge_preset(self, preset: str) -> None:
        source = self.visible_storage_items or self.storage_items
        self.purge_items = build_purge_plan(source, preset)
        self._render_purge_items()
        self.purge_text.delete("1.0", "end")
        self.purge_text.insert("1.0", f"Preset: {preset}\n\n" + self.engine.preview_purge(self.purge_items))

    def preview_purge(self) -> None:
        if not self.purge_items:
            self.purge_text.delete("1.0", "end")
            self.purge_text.insert("1.0", "No purge items selected yet. Scan storage and apply a preset first.")
            return
        self.purge_text.delete("1.0", "end")
        self.purge_text.insert("1.0", self.engine.preview_purge(self.purge_items))

    def execute_purge(self) -> None:
        if not self.purge_items:
            messagebox.showinfo("Tabula", "No purge plan selected yet.")
            return
        action = self.engine.record_purge(self.purge_items, dry_run=False)
        self.purge_text.insert("end", f"\n\nRecorded purge action: {action.id}")
        self.refresh_history()
        messagebox.showinfo("Tabula", "Purge action recorded in history.")

    def _refresh_relocate_screen(self) -> None:
        for row in self.relocate_tree.get_children():
            self.relocate_tree.delete(row)
        for item in relocation_candidates(self.visible_storage_items or self.storage_items):
            self.relocate_tree.insert(
                "",
                "end",
                values=(
                    item.display_name,
                    item.kind.value,
                    item.risk_level.value,
                    item.recommended_action.value,
                    self._fmt_bytes(item.movable_bytes),
                    item.owner_hint or "—",
                    item.path,
                ),
            )

    def on_relocate_selected(self, _event=None) -> None:
        selection = self.relocate_tree.selection()
        candidates = relocation_candidates(self.visible_storage_items or self.storage_items)
        if not selection:
            return
        index = self.relocate_tree.index(selection[0])
        if index >= len(candidates):
            return
        self.selected_relocation_item = candidates[index]
        self.relocate_status.set(
            f"Selected {self.selected_relocation_item.display_name} • movable {self._fmt_bytes(self.selected_relocation_item.movable_bytes)}"
        )
        self.preview_relocation()

    def preview_relocation(self) -> None:
        if not self.selected_relocation_item:
            self.relocate_text.delete("1.0", "end")
            self.relocate_text.insert("1.0", "Select a relocation candidate from the table first.")
            return
        preview = self.relocator.preview(self.selected_relocation_item, self.target_var.get(), LinkType(self.link_type_var.get()))
        self.relocate_text.delete("1.0", "end")
        self.relocate_text.insert("1.0", preview)

    def record_relocation(self) -> None:
        if not self.selected_relocation_item:
            messagebox.showinfo("Tabula", "Select a relocation candidate first.")
            return
        record = self.relocator.plan(self.selected_relocation_item, self.target_var.get(), LinkType(self.link_type_var.get()))
        self.relocate_text.insert("end", f"\n\nRecorded relocation: {record.id}")
        self.refresh_links()
        self.refresh_history()
        messagebox.showinfo("Tabula", "Relocation recorded in the ledger.")

    def refresh_links(self) -> None:
        for row in self.links_tree.get_children():
            self.links_tree.delete(row)
        for record in self.link_manager.load_links():
            self.links_tree.insert(
                "",
                "end",
                values=(record.source_path, record.target_path, record.link_type.value, record.status, "Yes" if record.validated else "No", record.owner_hint or "—"),
            )

    def validate_links(self) -> None:
        self.link_manager.validate_all()
        self.refresh_links()
        self.refresh_history()
        messagebox.showinfo("Tabula", "Link validation complete.")

    def refresh_history(self) -> None:
        self.history_text.delete("1.0", "end")
        relocations = self.engine.relocation_ledger.load()
        actions = self.engine.action_ledger.load()
        self.history_text.insert("end", "== Relocations ==\n")
        if not relocations:
            self.history_text.insert("end", "No relocation records yet.\n")
        for record in relocations:
            self.history_text.insert(
                "end",
                f"{record.created_at.isoformat()} | {record.source_path} -> {record.target_path} | {record.link_type.value} | {record.status} | {record.owner_hint}\n",
            )
        self.history_text.insert("end", "\n== Actions ==\n")
        if not actions:
            self.history_text.insert("end", "No action records yet.\n")
        for action in actions:
            self.history_text.insert(
                "end",
                f"{action.started_at.isoformat()} | {action.action_type.value} | {action.status.value} | bytes={self._fmt_bytes(action.bytes_affected)} | {action.notes}\n",
            )

    def export_relocations(self) -> None:
        destination = Path(self.engine.base_dir) / "relocations_export.json"
        self.engine.relocation_ledger.export_json(destination)
        messagebox.showinfo("Tabula", f"Relocations exported to {destination}")

    def export_actions(self) -> None:
        destination = Path(self.engine.base_dir) / "actions_export.json"
        self.engine.action_ledger.export_json(destination)
        messagebox.showinfo("Tabula", f"Actions exported to {destination}")

    def show_program_detail(self, _event=None) -> None:
        selection = self.program_tree.selection()
        if not selection:
            return
        index = self.program_tree.index(selection[0])
        if index >= len(self.visible_program_items):
            return
        item = self.visible_program_items[index]
        details = (
            f"Raw name: {item.raw_display_name}\n"
            f"Normalized: {item.normalized_name}\n"
            f"Record type: {item.record_type.value}\n"
            f"Category: {item.category.value}\n"
            f"Risk: {item.risk_level.value}\n"
            f"Install path: {item.install_location or '—'}\n"
            f"Estimated install: {self._fmt_bytes(item.estimated_install_bytes)}\n"
            f"Estimated cache: {self._fmt_bytes(item.estimated_cache_bytes)}\n"
            f"Estimated total: {item.estimated_total_human}\n"
            f"Legal status: {item.legal_status.value}\n"
            f"Alternative hint: {item.legal_alternative_hint or '—'}\n"
            f"Alternatives: {', '.join(item.legal_alternative_candidates) or '—'}\n"
            f"Estimate notes: {item.estimate_notes or '—'}"
        )
        self.inventory_detail.delete("1.0", "end")
        self.inventory_detail.insert("1.0", details)

    def show_storage_detail(self, _event=None) -> None:
        selection = self.storage_tree.selection()
        if not selection:
            return
        index = self.storage_tree.index(selection[0])
        if index >= len(self.visible_storage_items):
            return
        item = self.visible_storage_items[index]
        details = (
            f"Path: {item.path}\n"
            f"Kind: {item.kind.value}\n"
            f"Risk: {item.risk_level.value}\n"
            f"Recommended action: {item.recommended_action.value}\n"
            f"Total size: {self._fmt_bytes(item.total_bytes)}\n"
            f"Reclaimable: {self._fmt_bytes(item.reclaimable_bytes)}\n"
            f"Movable: {self._fmt_bytes(item.movable_bytes)}\n"
            f"Owner hint: {item.owner_hint or '—'}\n"
            f"Source: {item.source}\n"
            f"Notes: {item.notes or '—'}"
        )
        self.inventory_detail.delete("1.0", "end")
        self.inventory_detail.insert("1.0", details)

    def _update_inventory_status(self, force_text: str | None = None) -> None:
        if force_text:
            self.inventory_status.set(force_text)
            return
        self.inventory_status.set(
            f"Programs: {len(self.visible_program_items)}/{len(self.program_items)} visible • "
            f"Storage: {len(self.visible_storage_items)}/{len(self.storage_items)} visible • "
            f"Purge-ready: {sum(1 for item in self.storage_items if item.recommended_action == RecommendedAction.PURGE)} • "
            f"Relocate-ready: {len(relocation_candidates(self.storage_items))}"
        )

    @staticmethod
    def _fmt_bytes(size: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024
        return f"{size} B"
