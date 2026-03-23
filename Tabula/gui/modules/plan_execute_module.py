from __future__ import annotations

import json
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.benchmarks import compare_benchmarks
from core.models import ActionPlan, ExecutionTiming
from core.scanners import benchmark_snapshot
from gui.module_api import AppContext, BaseModule


class PlanExecuteModule(BaseModule):
    module_id = "plan_execute"
    title = "Plan & Execute"

    def build(self, container, app, context: AppContext) -> None:
        self.context = context
        ctk.CTkLabel(container, text="Plan & sichere Ausführung", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        self.preview_box = ctk.CTkTextbox(container, height=350, wrap="word")
        self.preview_box.pack(fill="both", expand=True, padx=15, pady=8)

        # Execution timing selector
        timing_frame = ctk.CTkFrame(container)
        timing_frame.pack(pady=4)
        ctk.CTkLabel(timing_frame, text="Ausführungszeitpunkt:").pack(side="left", padx=6)
        self.timing_var = ctk.StringVar(value=ExecutionTiming.NOW.value)
        ctk.CTkOptionMenu(
            timing_frame,
            values=[t.value for t in ExecutionTiming],
            variable=self.timing_var,
        ).pack(side="left", padx=6)

        frame = ctk.CTkFrame(container)
        frame.pack(pady=12)
        ctk.CTkButton(frame, text="Vorschau", command=self.update_preview).pack(side="left", padx=6)
        ctk.CTkButton(frame, text="Dry-Run", fg_color="green", command=lambda: self.execute(True)).pack(side="left", padx=6)
        ctk.CTkButton(frame, text="JETZT AUSFÜHREN", fg_color="#c0392b", command=lambda: self.execute(False)).pack(side="left", padx=6)
        ctk.CTkButton(frame, text="Undo", command=self.undo).pack(side="left", padx=6)

        plan_io = ctk.CTkFrame(container)
        plan_io.pack(pady=8)
        ctk.CTkButton(plan_io, text="Plan exportieren", command=self.export_plan).pack(side="left", padx=6)
        ctk.CTkButton(plan_io, text="Plan JSON importieren", command=self.import_plan).pack(side="left", padx=6)
        ctk.CTkButton(plan_io, text="Plan leeren", command=self.clear_plan).pack(side="left", padx=6)

        bench = ctk.CTkFrame(container)
        bench.pack(pady=10)
        ctk.CTkButton(bench, text="Benchmark vorher", command=self.take_before).pack(side="left", padx=8)
        ctk.CTkButton(bench, text="Benchmark nachher", command=self.compare_after).pack(side="left", padx=8)

        self.bench_result = ctk.CTkTextbox(container, height=120)
        self.bench_result.pack(fill="x", padx=15, pady=5)

    def _apply_timing_to_plan(self) -> None:
        """Apply the currently selected execution timing to all plan actions."""
        timing = self.timing_var.get()
        for action in self.context.planner.plan:
            action.execution_timing = timing

    def update_preview(self) -> None:
        self._apply_timing_to_plan()
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", self.context.planner.preview())

    def execute(self, dry_run: bool) -> None:
        if not self.context.planner.plan:
            messagebox.showwarning("Plan leer", "Füge zuerst Aktionen hinzu")
            return

        self._apply_timing_to_plan()

        if not dry_run:
            high_risk = self.context.planner.high_risk_count()
            # First confirmation
            if not messagebox.askyesno("Warnung", "Wirklich ausführen?"):
                return
            # Second confirmation required for any High/Critical risk actions
            if high_risk > 0:
                if not messagebox.askyesno(
                    "⚠️ HIGH RISK – Zweite Bestätigung erforderlich",
                    f"{high_risk} Aktion(en) haben Risikostufe HIGH oder CRITICAL.\n\n"
                    "Diese Aktionen können nicht einfach rückgängig gemacht werden.\n\n"
                    "Wirklich fortfahren?",
                ):
                    return

        results = self.context.planner.execute(dry_run=dry_run)
        self.preview_box.insert("end", "\n\n=== ERGEBNIS ===\n" + "\n".join(results))
        self.preview_box.see("end")

    def export_plan(self) -> None:
        if not self.context.planner.plan:
            messagebox.showwarning("Plan leer", "Kein Plan zum Exportieren vorhanden")
            return

        payload = {
            "plan_name": "Tabula Exported Plan",
            "actions": [action.model_dump() for action in self.context.planner.plan],
        }
        out = filedialog.asksaveasfilename(
            title="Plan exportieren",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="tabula_plan_export.json",
        )
        if not out:
            return
        Path(out).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        messagebox.showinfo("Plan", f"Plan exportiert: {out}")

    def import_plan(self) -> None:
        src = filedialog.askopenfilename(title="Plan JSON importieren", filetypes=[("JSON", "*.json")])
        if not src:
            return

        try:
            payload = json.loads(Path(src).read_text(encoding="utf-8"))
            actions = payload.get("actions", [])
            imported = 0
            for action_obj in actions:
                if not isinstance(action_obj, dict):
                    continue
                try:
                    self.context.planner.add(ActionPlan(**action_obj))
                    imported += 1
                except Exception:
                    # tolerate partial imports
                    continue
            self.update_preview()
            messagebox.showinfo("Plan", f"{imported} Aktionen importiert aus {src}")
        except Exception as exc:
            messagebox.showerror("Import fehlgeschlagen", str(exc))

    def clear_plan(self) -> None:
        if messagebox.askyesno("Plan leeren", "Wirklich alle geplanten Aktionen löschen?"):
            self.context.planner.clear()
            self.update_preview()

    def undo(self) -> None:
        msg = self.context.planner.undo_last_snapshot()
        self.preview_box.insert("end", f"\n\nUNDO: {msg}")
        messagebox.showinfo("Undo", msg)

    def take_before(self) -> None:
        self.context.state["before_benchmark"] = benchmark_snapshot()
        before = self.context.state["before_benchmark"]
        messagebox.showinfo("Benchmark", f"Vorher aufgenommen um {before['timestamp']}")

    def compare_after(self) -> None:
        before = self.context.state.get("before_benchmark")
        if not before:
            messagebox.showerror("Fehler", "Erst vorher Benchmark aufnehmen")
            return
        text = compare_benchmarks(before, benchmark_snapshot())
        self.bench_result.delete("1.0", "end")
        self.bench_result.insert("1.0", text)
