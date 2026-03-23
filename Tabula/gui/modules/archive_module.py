from __future__ import annotations

import os
from pathlib import Path
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

        pwd_frame = ctk.CTkFrame(container)
        pwd_frame.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(pwd_frame, text="Passwort-Datei (optional):").pack(side="left", padx=4)
        self.pwd_file_var = StringVar(value="")
        ctk.CTkEntry(pwd_frame, textvariable=self.pwd_file_var, width=380,
                     placeholder_text="Pfad zur eigenen Passwortliste (eine Zeile = ein Passwort)").pack(side="left", padx=4)
        ctk.CTkButton(pwd_frame, text="Durchsuchen", width=110, command=self._browse_password_file).pack(side="left", padx=4)

        ctk.CTkButton(container, text="Ordner scannen", command=self.scan).pack(pady=5)

        self.archive_tree = ttk.Treeview(
            container,
            columns=("Pfad", "Typ", "Größe", "Status", "Overlap", "Passwort"),
            show="headings",
            height=14,
        )
        for col, width in [("Pfad", 480), ("Typ", 80), ("Größe", 80), ("Status", 140), ("Overlap", 80), ("Passwort", 90)]:
            self.archive_tree.heading(col, text=col)
            self.archive_tree.column(col, width=width, anchor="w")
        self.archive_tree.pack(fill="both", expand=True, padx=10, pady=5)

        # Color tags
        self.archive_tree.tag_configure("pwd_protected", foreground="#e74c3c")
        self.archive_tree.tag_configure("overlap", foreground="#f39c12")

        ctk.CTkButton(container, text="Ausgewählte Archive in Plan", fg_color="red",
                      command=lambda: self.add_selected(context)).pack(pady=8)

    def _browse_password_file(self) -> None:
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Passwortliste öffnen",
            filetypes=[("Textdateien", "*.txt"), ("Alle Dateien", "*.*")],
        )
        if path:
            self.pwd_file_var.set(path)

    def _load_password_list(self) -> list[str]:
        """Load passwords from the user-provided file. Never logged."""
        pwd_file = self.pwd_file_var.get().strip()
        if not pwd_file:
            return []
        try:
            return [line.strip() for line in Path(pwd_file).read_text(encoding="utf-8").splitlines() if line.strip()]
        except Exception as exc:
            messagebox.showwarning("Passwortliste", f"Datei nicht lesbar: {exc}\nArchiv-Scan wird ohne Passwortprüfung fortgesetzt.")
            return []

    def scan(self) -> None:
        for item in self.archive_tree.get_children():
            self.archive_tree.delete(item)
        passwords = self._load_password_list()
        for archive in scan_archives(self.archive_folder_var.get(), password_list=passwords or None):
            pwd_label = "Ja" if archive.password_protected else "Nein"
            tag = "pwd_protected" if archive.password_protected else ("overlap" if archive.overlap_installed else "")
            self.archive_tree.insert(
                "",
                "end",
                values=(
                    archive.path,
                    archive.file_type,
                    f"{archive.size_mb:.1f} MB",
                    archive.status + (f" – {archive.notes}" if archive.notes else ""),
                    "Ja" if archive.overlap_installed else "Nein",
                    pwd_label,
                ),
                tags=(tag,) if tag else (),
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
