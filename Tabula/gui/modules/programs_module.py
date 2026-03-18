from __future__ import annotations

from tkinter import messagebox, ttk

import customtkinter as ctk

from core.models import ActionPlan
from core.scanners import scan_installed_programs
from gui.module_api import AppContext, BaseModule


class ProgramsModule(BaseModule):
    module_id = "programs"
    title = "Programme"

    def build(self, container, app, context: AppContext) -> None:
        ctk.CTkLabel(container, text="Installierte Win32-Programme", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=8)

        self.prog_tree = ttk.Treeview(container, columns=("Name", "Größe", "Kategorie", "Risiko", "Publisher"), show="headings", height=18)
        for col, width in [("Name", 320), ("Größe", 90), ("Kategorie", 120), ("Risiko", 100), ("Publisher", 260)]:
            self.prog_tree.heading(col, text=col)
            self.prog_tree.column(col, width=width, anchor="w")
        self.prog_tree.pack(fill="both", expand=True, padx=10, pady=5)

        frame = ctk.CTkFrame(container)
        frame.pack(pady=10)
        ctk.CTkButton(frame, text="Programme scannen", command=self.scan).pack(side="left", padx=5)
        ctk.CTkButton(frame, text="Ausgewählte in Plan", fg_color="orange", command=lambda: self.add_selected(context)).pack(side="left", padx=5)

    def scan(self) -> None:
        for item in self.prog_tree.get_children():
            self.prog_tree.delete(item)
        for program in scan_installed_programs()[:1000]:
            self.prog_tree.insert(
                "",
                "end",
                values=(program.name[:70], f"{program.size_mb:.1f} MB", program.category, program.risk, program.publisher[:55]),
                tags=(program.uninstall_cmd,),
            )

    def add_selected(self, context: AppContext) -> None:
        selected = self.prog_tree.selection()
        for item in selected:
            values = self.prog_tree.item(item)["values"]
            uninstall_cmd = self.prog_tree.item(item)["tags"][0]
            if uninstall_cmd:
                size = float(str(values[1]).replace(" MB", ""))
                context.planner.add(
                    ActionPlan(
                        action_type="uninstall",
                        target=uninstall_cmd,
                        description=f"Programm deinstallieren: {values[0]}",
                        impact_mb=size,
                        risk=str(values[3]),
                    )
                )
        messagebox.showinfo("Plan", f"{len(selected)} Programme hinzugefügt")
