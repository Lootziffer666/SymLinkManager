from __future__ import annotations

import csv
import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import StringVar, filedialog, messagebox, ttk

import customtkinter as ctk

from core.models import ActionPlan
from core import settings as _settings
from core.scanners import filter_programs, match_import_list, scan_installed_programs
from gui.module_api import AppContext, BaseModule

_MAX_PATH_CHIP_LENGTH = 40  # characters; longer paths are condensed to Drive:\…\LastFolder


def _pal():
    from gui.main_window import get_palette
    return get_palette()


class _ProgressWindow(ctk.CTkToplevel):
    """Small floating window showing scan progress."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Tabula – Scan läuft …")
        self.geometry("400x110")
        self.resizable(False, False)
        self.grab_set()

        self._label = ctk.CTkLabel(self, text="Starte Scan …", wraplength=380, anchor="w")
        self._label.pack(fill="x", padx=16, pady=(14, 6))

        self._sub = ctk.CTkLabel(self, text="", wraplength=380, anchor="w",
                                 font=ctk.CTkFont(size=10))
        self._sub.pack(fill="x", padx=16, pady=0)

        self._bar = ctk.CTkProgressBar(self, mode="indeterminate")
        self._bar.pack(fill="x", padx=16, pady=(8, 12))
        self._bar.start()

    def update_status(self, stage: str, detail: str) -> None:
        self._label.configure(text=stage)
        short_detail = detail[:60] + "…" if len(detail) > 60 else detail
        self._sub.configure(text=short_detail)
        self.update_idletasks()

    def close(self) -> None:
        self._bar.stop()
        self.grab_release()
        self.destroy()


class ProgramsModule(BaseModule):
    module_id = "programs"
    title = "Programme"

    def build(self, container, app, context: AppContext) -> None:
        self._all_programs: list = []
        self._import_matches: dict[str, str] = {}
        self._context = context
        self._app = app
        self._container = container

        ctk.CTkLabel(
            container,
            text="Installierte Win32-Programme",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(pady=(8, 4))

        # --- Filter bar ---
        filter_frame = ctk.CTkFrame(container)
        filter_frame.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(filter_frame, text="Suche:").pack(side="left", padx=4)
        self.search_var = StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(filter_frame, textvariable=self.search_var, width=200).pack(side="left", padx=4)

        self.hide_ms_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(filter_frame, text="Microsoft ausbl.", variable=self.hide_ms_var,
                        command=self._apply_filter).pack(side="left", padx=4)
        self.hide_rt_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(filter_frame, text="Runtimes ausbl.", variable=self.hide_rt_var,
                        command=self._apply_filter).pack(side="left", padx=4)
        self.hide_drv_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(filter_frame, text="Treiber ausbl.", variable=self.hide_drv_var,
                        command=self._apply_filter).pack(side="left", padx=4)
        self.large_only_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(filter_frame, text=">500 MB", variable=self.large_only_var,
                        command=self._apply_filter).pack(side="left", padx=4)
        self.show_import_only_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(filter_frame, text="Nur Import-Matches", variable=self.show_import_only_var,
                        command=self._apply_filter).pack(side="left", padx=4)

        self.count_label = ctk.CTkLabel(filter_frame, text="0 Programme")
        self.count_label.pack(side="right", padx=8)

        # --- Extra search paths bar ---
        extra_frame = ctk.CTkFrame(container)
        extra_frame.pack(fill="x", padx=10, pady=(2, 0))

        ctk.CTkLabel(extra_frame, text="📁 Extra-Suchpfade:").pack(side="left", padx=(4, 6))

        # Scrollable path-chip area
        self._extra_paths_frame = ctk.CTkFrame(extra_frame, fg_color="transparent")
        self._extra_paths_frame.pack(side="left", fill="x", expand=True, padx=2)

        ctk.CTkButton(
            extra_frame,
            text="+ Pfad hinzufügen",
            width=130,
            height=26,
            command=self._add_extra_path,
        ).pack(side="right", padx=4, pady=2)

        # Load persisted extra paths and render chips
        self._extra_paths: list[str] = _settings.load().get("extra_search_paths", [])
        self._render_path_chips()

        # --- Select all / none bar ---
        sel_bar = ctk.CTkFrame(container)
        sel_bar.pack(fill="x", padx=10, pady=(0, 2))
        ctk.CTkButton(sel_bar, text="☑ Alle auswählen", width=140, height=26,
                      command=self._select_all).pack(side="left", padx=4, pady=2)
        ctk.CTkButton(sel_bar, text="☐ Auswahl aufheben", width=160, height=26,
                      command=self._select_none).pack(side="left", padx=4, pady=2)
        self.sel_count_label = ctk.CTkLabel(sel_bar, text="0 ausgewählt")
        self.sel_count_label.pack(side="right", padx=8)

        # --- Treeview ---
        tree_frame = ctk.CTkFrame(container)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=4)

        cols = ("✓", "Name", "Größe", "Kategorie", "Risiko", "Publisher", "Installiert am", "Import")
        self.prog_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=16)

        col_widths = [("✓", 30), ("Name", 280), ("Größe", 90), ("Kategorie", 120),
                      ("Risiko", 80), ("Publisher", 220), ("Installiert am", 110), ("Import", 60)]
        for col, width in col_widths:
            anchor = "center" if col in ("✓", "Risiko", "Größe", "Import", "Installiert am") else "w"
            self.prog_tree.heading(col, text=col, command=lambda c=col: self._sort_by(c))
            self.prog_tree.column(col, width=width, anchor=anchor, stretch=(col == "Name"))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.prog_tree.yview)
        self.prog_tree.configure(yscrollcommand=vsb.set)
        self.prog_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._apply_tree_tags()
        self.prog_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # --- Detail panel ---
        self.detail_box = ctk.CTkTextbox(container, height=90, wrap="word")
        self.detail_box.pack(fill="x", padx=10, pady=4)

        # --- Buttons ---
        btn_frame = ctk.CTkFrame(container)
        btn_frame.pack(pady=6)
        self.scan_btn = ctk.CTkButton(btn_frame, text="Programme scannen", command=self._scan_threaded)
        self.scan_btn.pack(side="left", padx=5)
        pal = _pal()
        ctk.CTkButton(btn_frame, text="Ausgewählte in Plan",
                      fg_color=pal["accent"], text_color=pal["accent_text"],
                      command=self._add_selected).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Uninstall-Skript", fg_color="#8e44ad",
                      command=self._generate_script).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Importliste laden", fg_color="#2980b9",
                      command=self._load_import_list).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="CSV exportieren",
                      command=self._export_csv).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="JSON exportieren",
                      command=self._export_json).pack(side="left", padx=5)

        self._progress_win: _ProgressWindow | None = None

    # ------------------------------------------------------------------
    def _apply_tree_tags(self) -> None:
        pal = _pal()
        self.prog_tree.tag_configure("risk_high", foreground=pal["risk_high"])
        self.prog_tree.tag_configure("risk_medium", foreground=pal["risk_medium"])
        self.prog_tree.tag_configure("risk_low", foreground=pal["risk_low"])
        self.prog_tree.tag_configure("import_match", background=pal["import_match_bg"])

    def on_theme_change(self) -> None:
        self._apply_tree_tags()

    # ------------------------------------------------------------------
    # Extra search paths management
    # ------------------------------------------------------------------
    def _render_path_chips(self) -> None:
        """Redraw the row of path chips inside _extra_paths_frame."""
        for w in self._extra_paths_frame.winfo_children():
            w.destroy()
        if not self._extra_paths:
            ctk.CTkLabel(
                self._extra_paths_frame,
                text="(keine)",
                text_color="gray",
                font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=2)
            return
        for path in self._extra_paths:
            chip = ctk.CTkFrame(self._extra_paths_frame, corner_radius=6)
            chip.pack(side="left", padx=3, pady=2)
            # Show "Drive:\…\last_folder" so the relevant parts are always visible
            p = Path(path)
            parts = p.parts
            if len(path) <= _MAX_PATH_CHIP_LENGTH:
                short = path
            elif len(parts) >= 2:
                short = str(Path(parts[0])) + "\\…\\" + parts[-1]
            else:
                short = "…" + path[-(  _MAX_PATH_CHIP_LENGTH - 3):]
            lbl = ctk.CTkLabel(chip, text=short, font=ctk.CTkFont(size=11))
            lbl.pack(side="left", padx=(6, 2))
            # Show full path in tooltip on hover (via bind on label)
            lbl.bind("<Enter>", lambda e, fp=path: self._show_path_tooltip(e, fp))
            lbl.bind("<Leave>", lambda e: self._hide_path_tooltip())
            ctk.CTkButton(
                chip,
                text="×",
                width=22,
                height=22,
                fg_color="transparent",
                hover_color="#884444",
                command=lambda p=path: self._remove_extra_path(p),
            ).pack(side="left", padx=(0, 4))

    def _show_path_tooltip(self, event, full_path: str) -> None:
        try:
            if hasattr(self, "_tooltip") and self._tooltip:
                self._tooltip.destroy()
            tw = tk.Toplevel()
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{event.x_root + 8}+{event.y_root + 8}")
            tk.Label(tw, text=full_path, background="#333333", foreground="#FFFFFF",
                     relief="solid", borderwidth=1, font=("Segoe UI", 9)).pack()
            self._tooltip = tw
        except Exception:
            pass

    def _hide_path_tooltip(self) -> None:
        try:
            if hasattr(self, "_tooltip") and self._tooltip:
                self._tooltip.destroy()
                self._tooltip = None
        except Exception:
            pass

    def _add_extra_path(self) -> None:
        chosen = filedialog.askdirectory(title="Extra-Suchpfad hinzufügen (z. B. F:\\Installer)")
        if not chosen:
            return
        chosen = str(Path(chosen))
        if chosen not in self._extra_paths:
            self._extra_paths.append(chosen)
            self._save_extra_paths()
            self._render_path_chips()

    def _remove_extra_path(self, path: str) -> None:
        if path in self._extra_paths:
            self._extra_paths.remove(path)
            self._save_extra_paths()
            self._render_path_chips()

    def _save_extra_paths(self) -> None:
        data = _settings.load()
        data["extra_search_paths"] = self._extra_paths
        _settings.save(data)

    # ------------------------------------------------------------------
    def _scan_threaded(self) -> None:
        self.scan_btn.configure(state="disabled")
        self._progress_win = _ProgressWindow(self._container)
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_progress(self, stage: str, detail: str) -> None:
        def _update() -> None:
            if self._progress_win and self._progress_win.winfo_exists():
                self._progress_win.update_status(stage, detail)

        if self._progress_win and self._progress_win.winfo_exists():
            self._progress_win.after(0, _update)

    def _scan_worker(self) -> None:
        extra = [Path(p) for p in self._extra_paths if p]
        programs = scan_installed_programs(
            progress_callback=self._scan_progress,
            extra_paths=extra if extra else None,
        )
        self._all_programs = programs
        self.prog_tree.after(0, self._finish_scan)

    def _finish_scan(self) -> None:
        if self._progress_win and self._progress_win.winfo_exists():
            self._progress_win.close()
        self._progress_win = None
        self.scan_btn.configure(state="normal")
        self._apply_filter()

    # ------------------------------------------------------------------
    def _load_import_list(self) -> None:
        src = filedialog.askopenfilename(
            title="Importliste laden (eine Zeile = ein Programmname)",
            filetypes=[("Textdateien", "*.txt"), ("Alle Dateien", "*.*")],
        )
        if not src:
            return
        if not self._all_programs:
            messagebox.showwarning("Import", "Bitte zuerst Programme scannen.")
            return
        try:
            lines = [line.strip() for line in Path(src).read_text(encoding="utf-8").splitlines() if line.strip()]
        except Exception as exc:
            messagebox.showerror("Import", f"Datei nicht lesbar: {exc}")
            return
        self._import_matches = match_import_list(self._all_programs, lines)
        matched = sum(1 for v in self._import_matches.values() if v)
        self._apply_filter()
        messagebox.showinfo(
            "Import",
            f"{len(lines)} Einträge geladen • {matched} Treffer von {len(self._all_programs)} installierten Programmen",
        )

    # ------------------------------------------------------------------
    def _apply_filter(self) -> None:
        filtered = filter_programs(
            self._all_programs,
            query=self.search_var.get(),
            hide_microsoft=self.hide_ms_var.get(),
            hide_runtimes=self.hide_rt_var.get(),
            hide_drivers=self.hide_drv_var.get(),
            large_only=self.large_only_var.get(),
        )
        if self.show_import_only_var.get() and self._import_matches:
            matched_ids = set(self._import_matches.values()) - {""}
            filtered = [p for p in filtered if p.id in matched_ids]

        prev_selected = set(self.prog_tree.selection())
        for item in self.prog_tree.get_children():
            self.prog_tree.delete(item)

        for prog in filtered[:2000]:
            risk_tag = f"risk_{prog.risk_level.value.lower()}"
            is_import_match = bool(self._import_matches) and prog.id in set(self._import_matches.values()) - {""}
            tags = (risk_tag, "import_match") if is_import_match else (risk_tag,)
            is_checked = prog.id in prev_selected
            self.prog_tree.insert(
                "",
                "end",
                values=(
                    "☑" if is_checked else "☐",
                    prog.raw_display_name[:70],
                    f"{prog.estimated_total_bytes / (1024 * 1024):.1f} MB",
                    prog.category.value,
                    prog.risk_level.value,
                    prog.publisher[:50],
                    prog.installed_at or "—",
                    "✓" if is_import_match else "",
                ),
                tags=tags,
                iid=prog.id,
            )
            if is_checked:
                self.prog_tree.selection_add(prog.id)

        self.count_label.configure(text=f"{len(filtered)} Programme")
        self._update_sel_count()

    def _on_tree_select(self, _event=None) -> None:
        """Toggle checkbox visual and show detail."""
        selection = self.prog_tree.selection()
        # Update checkbox column for all visible items
        for iid in self.prog_tree.get_children():
            vals = list(self.prog_tree.item(iid, "values"))
            vals[0] = "☑" if iid in selection else "☐"
            self.prog_tree.item(iid, values=vals)
        self._update_sel_count()
        self._show_detail()

    def _update_sel_count(self) -> None:
        n = len(self.prog_tree.selection())
        self.sel_count_label.configure(text=f"{n} ausgewählt")

    def _select_all(self) -> None:
        children = self.prog_tree.get_children()
        self.prog_tree.selection_set(children)
        for iid in children:
            vals = list(self.prog_tree.item(iid, "values"))
            vals[0] = "☑"
            self.prog_tree.item(iid, values=vals)
        self._update_sel_count()

    def _select_none(self) -> None:
        self.prog_tree.selection_remove(self.prog_tree.get_children())
        for iid in self.prog_tree.get_children():
            vals = list(self.prog_tree.item(iid, "values"))
            vals[0] = "☐"
            self.prog_tree.item(iid, values=vals)
        self._update_sel_count()

    def _sort_by(self, col: str) -> None:
        reverse = getattr(self, "_sort_reverse", False)
        self._sort_reverse = not reverse
        key_map = {
            "Name": lambda p: p.raw_display_name.lower(),
            "Größe": lambda p: p.estimated_total_bytes,
            "Kategorie": lambda p: p.category.value,
            "Risiko": lambda p: p.risk_level.value,
            "Publisher": lambda p: p.publisher.lower(),
            "Import": lambda p: p.id in set(self._import_matches.values()) - {""},
            "Installiert am": lambda p: p.installed_at or "",
        }
        key_fn = key_map.get(col, lambda p: "")
        self._all_programs.sort(key=key_fn, reverse=reverse)
        self._apply_filter()

    def _show_detail(self, _event=None) -> None:
        selection = self.prog_tree.selection()
        if not selection:
            return
        prog_id = selection[-1]  # show most-recently-selected item
        prog = next((p for p in self._all_programs if p.id == prog_id), None)
        if not prog:
            return
        import_note = ""
        if self._import_matches:
            matched_line = next((k for k, v in self._import_matches.items() if v == prog.id), None)
            if matched_line:
                import_note = f"\nImport-Match: \"{matched_line}\""
        detail = (
            f"Name: {prog.raw_display_name}\n"
            f"Version: {prog.display_version}  |  Publisher: {prog.publisher}\n"
            f"Kategorie: {prog.category.value}  |  Typ: {prog.record_type.value}  |  Risiko: {prog.risk_level.value}\n"
            f"Größe: {prog.estimated_total_human}  (Confidence: {prog.estimate_confidence})\n"
            f"Installiert am: {prog.installed_at or '—'}  |  Zuletzt genutzt: {prog.last_used_at or '—'}\n"
            f"Install-Pfad: {prog.install_location or '—'}\n"
            f"Uninstall: {prog.uninstall_string or '—'}\n"
            f"Lizenz: {prog.legal_status.value}"
            + (f"  →  {prog.legal_alternative_hint}" if prog.legal_alternative_hint else "")
            + ("\n" + f"Alternativen: {', '.join(prog.legal_alternative_candidates)}" if prog.legal_alternative_candidates else "")
            + import_note
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
                fieldnames=["name", "version", "publisher", "category", "risk",
                            "size_mb", "install_location", "installed_at", "last_used_at"],
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
                    "installed_at": prog.installed_at,
                    "last_used_at": prog.last_used_at,
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
                "installed_at": prog.installed_at,
                "last_used_at": prog.last_used_at,
            }
            for prog in self._all_programs
        ]
        Path(out).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        messagebox.showinfo("Export", f"JSON gespeichert: {out}")
