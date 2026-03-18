from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from core.privacy import create_telemetry_preset
from gui.module_api import AppContext, BaseModule


class PrivacyModule(BaseModule):
    module_id = "privacy"
    title = "Privacy"

    def build(self, container, app, context: AppContext) -> None:
        ctk.CTkLabel(container, text="Privacy-Presets", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        frame = ctk.CTkFrame(container)
        frame.pack(pady=20)

        ctk.CTkButton(frame, text="Balanced", width=180, command=lambda: self.apply(context, "Balanced")).pack(side="left", padx=8)
        ctk.CTkButton(frame, text="Strict", width=180, command=lambda: self.apply(context, "Strict")).pack(side="left", padx=8)
        ctk.CTkButton(frame, text="Paranoid", width=180, fg_color="#e74c3c", command=lambda: self.apply(context, "Paranoid")).pack(side="left", padx=8)

    def apply(self, context: AppContext, preset: str) -> None:
        for action in create_telemetry_preset(preset):
            context.planner.add(action)
        messagebox.showinfo("Privacy", f"{preset}-Preset hinzugefügt")
