from __future__ import annotations

from tkinter import messagebox, ttk

import customtkinter as ctk

from core.privacy import create_telemetry_preset
from core.scanners import scan_autoruns
from gui.module_api import AppContext, BaseModule


class PrivacyModule(BaseModule):
    module_id = "privacy"
    title = "Privacy"

    def build(self, container, app, context: AppContext) -> None:
        ctk.CTkLabel(container, text="Privacy & Autoruns", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=8)

        # Autorun treeview
        self.autorun_tree = ttk.Treeview(
            container,
            columns=("Name", "Typ", "Speicherort", "Risiko", "Befehl"),
            show="headings",
            height=14,
        )
        for col, width in [("Name", 200), ("Typ", 100), ("Speicherort", 300), ("Risiko", 70), ("Befehl", 420)]:
            self.autorun_tree.heading(col, text=col)
            self.autorun_tree.column(col, width=width, anchor="w")
        self.autorun_tree.pack(fill="both", expand=True, padx=10, pady=5)

        # Color tags
        self.autorun_tree.tag_configure("high_risk", foreground="#e74c3c")
        self.autorun_tree.tag_configure("low_risk", foreground="#2ecc71")

        ctk.CTkButton(container, text="Autoruns scannen", command=self.scan_autoruns).pack(pady=4)

        # Privacy presets
        ctk.CTkLabel(container, text="Privacy-Presets", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(10, 4))
        frame = ctk.CTkFrame(container)
        frame.pack(pady=4)
        ctk.CTkButton(frame, text="Balanced", width=180, command=lambda: self.apply(context, "Balanced")).pack(side="left", padx=8)
        ctk.CTkButton(frame, text="Strict", width=180, command=lambda: self.apply(context, "Strict")).pack(side="left", padx=8)
        ctk.CTkButton(frame, text="Paranoid", width=180, fg_color="#e74c3c", command=lambda: self.apply(context, "Paranoid")).pack(side="left", padx=8)

    def scan_autoruns(self) -> None:
        for item in self.autorun_tree.get_children():
            self.autorun_tree.delete(item)
        entries = scan_autoruns()
        for entry in entries:
            tag = "high_risk" if entry.is_suspicious else "low_risk"
            self.autorun_tree.insert(
                "",
                "end",
                values=(
                    entry.name[:60],
                    entry.entry_type,
                    entry.location[:80],
                    entry.risk,
                    entry.command[:100],
                ),
                tags=(tag,),
            )
        messagebox.showinfo("Autoruns", f"{len(entries)} Einträge gefunden — {sum(1 for e in entries if e.is_suspicious)} verdächtig")

    def apply(self, context: AppContext, preset: str) -> None:
        for action in create_telemetry_preset(preset):
            context.planner.add(action)
        messagebox.showinfo("Privacy", f"{preset}-Preset hinzugefügt")
