from __future__ import annotations

import csv
import json
import os
import threading
from pathlib import Path
from tkinter import StringVar, filedialog, messagebox, ttk

import customtkinter as ctk

from core.models import ActionPlan
from core.scanners import filter_programs, scan_installed_programs
from gui.module_api import AppContext, BaseModule

_RISK_COLORS = {
    "Low": "#2ecc71",
    "Medium": "#f39c12",
    "High": "#e74c3c",
}


class ProgramsModule(BaseModule):
    module_id = "programs"
    title = "Programme"

    def build(self, container, app, context: AppContext) -> None:
        self._all_programs: list = []
        self._context = context

        ctk.CTkLabel(container, text="Installierte Win32-Programme", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=6)

        # --- Filter bar ---
        filter_frame = ctk.CTkFrame(container)
        filter_frame.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(filter_frame, text="Suche:").pack(side="left", padx=4)
        self.search_var = StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(filter_frame, textvariable=self.search_var, width=220).pack(side="left", padx=4)

        self.hide_ms_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(filter_frame, text="Microsoft ausbl.", variable=self.hide_ms_var, command=self._apply_filter).pack(side="left", padx=6)
        self.hide_rt_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(filter_frame, text="Runtimes ausbl.", variable=self.hide_rt_var, command=self._apply_filter).pack(side="left", padx=4)
        self.hide_drv_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(filter_frame, text="Treiber ausbl.", variable=self.hide_drv_var, command=self._apply_filter).pack(side="left", padx=4)
        self.large_only_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(filter_frame, text=">500 MB", variable=self.large_only_var, command=self._apply_filter).pack(side="left", padx=4)

        self.count_label = ctk.CTkLabel(filter_frame, text="0 Programme")
        self.count_label.pack(side="right", padx=8)

        # --- Treeview ---
        tree_frame = ctk.CTkFrame(container)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=4)

        self.prog_tree = ttk.Treeview(
            tree_frame,
            columns=("Name", "Größe", "Kategorie", "Risiko", "Publisher"),
            show="headings",
            height=16,
        )
        for col, width in [("Name", 320), ("Größe", 90), ("Kategorie", 120), ("Risiko", 90), ("Publisher", 260)]:
            self.prog_tree.heading(col, text=col, command=lambda c=col: self._sort_by(c))
            self.prog_tree.column(col, width=width, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.prog_tree.yview)
        self.prog_tree.configure(yscrollcommand=vsb.set)
        self.prog_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.prog_tree.tag_configure("risk_high", foreground="#e74c3c")
        self.prog_tree.tag_configure("risk_medium", foreground="#f39c12")
        self.prog_tree.tag_configure("risk_low", foreground="#2ecc71")
        self.prog_tree.bind("<<TreeviewSelect>>", self._show_detail)

        # --- Detail panel ---
        self.detail_box = ctk.CTkTextbox(container, height=100, wrap="word")
        self.detail_box.pack(fill="x", padx=10, pady=4)

        # --- Buttons ---
        btn_frame = ctk.CTkFrame(container)
        btn_frame.pack(pady=6)
        self.scan_btn = ctk.CTkButton(btn_frame, text="Programme scannen", command=self._scan_threaded)
        self.scan_btn.pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Ausgewählte in Plan", fg_color="orange", command=self._add_selected).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Uninstall-Skript", fg_color="#8e44ad", command=self._generate_script).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="CSV exportieren", command=self._export_csv).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="JSON exportieren", command=self._export_json).pack(side="left", padx=5)

        self.progress = ctk.CTkProgressBar(container, mode="indeterminate")

    # ------------------------------------------------------------------
    def _scan_threaded(self) -> None:
        self.scan_btn.configure(state="disabled")
        self.progress.pack(fill="x", padx=10, pady=2)
        self.progress.start()
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self) -> None:
        programs = scan_installed_programs()
        self._all_programs = programs
        self.prog_tree.after(0, self._finish_scan)

    def _finish_scan(self) -> None:
        self.progress.stop()
        self.progress.pack_forget()
        self.scan_btn.configure(state="normal")
        self._apply_filter()

    def _apply_filter(self) -> None:
        filtered = filter_programs(
            self._all_programs,
            query=self.search_var.get(),
            hide_microsoft=self.hide_ms_var.get(),
            hide_runtimes=self.hide_rt_var.get(),
            hide_drivers=self.hide_drv_var.get(),
            large_only=self.large_only_var.get(),
        )
        for item in self.prog_tree.get_children():
            self.prog_tree.delete(item)
        for prog in filtered[:2000]:
            risk_tag = f"risk_{prog.risk_level.value.lower()}"
            self.prog_tree.insert(
                "",
                "end",
                values=(
                    prog.raw_display_name[:70],
                    f"{prog.estimated_total_bytes / (1024*1024):.1f} MB",
                    prog.category.value,
                    prog.risk_level.value,
                    prog.publisher[:55],
                ),
                tags=(risk_tag,),
                iid=prog.id,
            )
        self.count_label.configure(text=f"{len(filtered)} Programme")

    def _sort_by(self, col: str) -> None:
        reverse = getattr(self, "_sort_reverse", False)
        self._sort_reverse = not reverse
        key_map = {
            "Name": lambda p: p.raw_display_name.lower(),
            "Größe": lambda p: p.estimated_total_bytes,
            "Kategorie": lambda p: p.category.value,
            "Risiko": lambda p: p.risk_level.value,
            "Publisher": lambda p: p.publisher.lower(),
        }
        key_fn = key_map.get(col, lambda p: "")
        self._all_programs.sort(key=key_fn, reverse=reverse)
        self._apply_filter()

    def _show_detail(self, _event=None) -> None:
        selection = self.prog_tree.selection()
        if not selection:
            return
        prog_id = selection[0]
        prog = next((p for p in self._all_programs if p.id == prog_id), None)
        if not prog:
            return
        detail = (
            f"Name: {prog.raw_display_name}\n"
            f"Version: {prog.display_version}  |  Publisher: {prog.publisher}\n"
            f"Kategorie: {prog.category.value}  |  Typ: {prog.record_type.value}  |  Risiko: {prog.risk_level.value}\n"
            f"Größe: {prog.estimated_total_human}  (Confidence: {prog.estimate_confidence})\n"
            f"Install-Pfad: {prog.install_location or '—'}\n"
            f"Uninstall: {prog.uninstall_string or '—'}\n"
            f"Lizenz: {prog.legal_status.value}"
            + (f"  →  {prog.legal_alternative_hint}" if prog.legal_alternative_hint else "")
            + ("\n" + f"Alternativen: {', '.join(prog.legal_alternative_candidates)}" if prog.legal_alternative_candidates else "")
        )
        self.detail_box.delete("1.0", "end")
        self.detail_box.insert("1.0", detail)

    def _add_selected(self) -> None:
        selected = self.prog_tree.selection()
        added = 0
        for item_id in selected:
            prog = next((p for p in self._all_programs if p.id == item_id), None)
            if prog is None:
                continue
            uninstall = prog.quiet_uninstall_string or prog.uninstall_string
            if not uninstall:
                continue
            self._context.planner.add(
                ActionPlan(
                    action_type="uninstall",
                    target=uninstall,
                    description=f"Programm deinstallieren: {prog.raw_display_name}",
                    impact_mb=prog.estimated_total_bytes / (1024 * 1024),
                    risk=prog.risk_level.value,
                    dry_run_preview=f"Würde deinstallieren: {prog.raw_display_name}",
                )
            )
            added += 1
        messagebox.showinfo("Plan", f"{added} Programme zum Plan hinzugefügt")

    def _generate_script(self) -> None:
        selected = self.prog_tree.selection()
        if not selected:
            messagebox.showwarning("Skript", "Bitte erst Programme auswählen.")
            return
        lines = ["# Tabula Uninstall-Skript (Dry-Run — bitte prüfen!)", "# Ausführen in PowerShell als Administrator", ""]
        for item_id in selected:
            prog = next((p for p in self._all_programs if p.id == item_id), None)
            if prog is None:
                continue
            cmd = prog.quiet_uninstall_string or prog.uninstall_string
            if cmd:
                lines.append(f"# {prog.raw_display_name}")
                lines.append(f"Start-Process -FilePath cmd.exe -ArgumentList '/c {cmd}' -Wait -NoNewWindow")
                lines.append("")
        out = filedialog.asksaveasfilename(
            title="Uninstall-Skript speichern",
            defaultextension=".ps1",
            filetypes=[("PowerShell", "*.ps1")],
            initialfile="tabula_uninstall.ps1",
        )
        if out:
            Path(out).write_text("\n".join(lines), encoding="utf-8")
            messagebox.showinfo("Skript", f"Gespeichert: {out}")

    def _export_csv(self) -> None:
        if not self._all_programs:
            messagebox.showwarning("Export", "Erst scannen.")
            return
        out = filedialog.asksaveasfilename(
            title="CSV exportieren",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="tabula_programmes.csv",
        )
        if not out:
            return
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["name", "version", "publisher", "category", "risk", "size_mb", "install_location"],
            )
            writer.writeheader()
            for prog in self._all_programs:
                writer.writerow({
                    "name": prog.raw_display_name,
                    "version": prog.display_version,
                    "publisher": prog.publisher,
                    "category": prog.category.value,
                    "risk": prog.risk_level.value,
                    "size_mb": round(prog.estimated_total_bytes / (1024 * 1024), 2),
                    "install_location": prog.install_location,
                })
        messagebox.showinfo("Export", f"CSV gespeichert: {out}")

    def _export_json(self) -> None:
        if not self._all_programs:
            messagebox.showwarning("Export", "Erst scannen.")
            return
        out = filedialog.asksaveasfilename(
            title="JSON exportieren",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="tabula_programmes.json",
        )
        if not out:
            return
        data = [
            {
                "name": prog.raw_display_name,
                "version": prog.display_version,
                "publisher": prog.publisher,
                "category": prog.category.value,
                "risk": prog.risk_level.value,
                "size_mb": round(prog.estimated_total_bytes / (1024 * 1024), 2),
                "install_location": prog.install_location,
                "uninstall_string": prog.uninstall_string,
            }
            for prog in self._all_programs
        ]
        Path(out).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        messagebox.showinfo("Export", f"JSON gespeichert: {out}")
