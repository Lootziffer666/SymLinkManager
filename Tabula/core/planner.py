from __future__ import annotations

import datetime as _dt
import shlex
import subprocess
from pathlib import Path
from typing import List

from .models import ActionPlan


class SafePlanner:
    def __init__(self) -> None:
        self.plan: List[ActionPlan] = []
        self.backup_dir = Path("tabula_backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.protected_markers = {
            "tabula.py",
            "modules.json",
            "micro_apps/catalog.json",
            "Tabula/gui",
            "Tabula/core",
            "Tabula/addons",
        }

    def add(self, action: ActionPlan) -> None:
        self.plan.append(action)

    def clear(self) -> None:
        self.plan.clear()

    def preview(self) -> str:
        if not self.plan:
            return "Keine Aktionen im Plan."
        total_mb = sum(a.impact_mb for a in self.plan)
        reboot = any(a.requires_reboot for a in self.plan)
        lines = [f"• {a.description} ({a.risk})" for a in self.plan]
        return (
            f"Geplanter Impact: {len(self.plan)} Aktionen • ~{total_mb:.1f} MB\n"
            f"Neustart erforderlich: {'JA' if reboot else 'Nein'}\n\n"
            + "\n".join(lines)
        )

    def create_snapshot(self) -> Path:
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        reg_file = self.backup_dir / f"snapshot_{ts}.reg"
        subprocess.run(["reg", "export", "HKLM", str(reg_file), "/y"], check=False, capture_output=True)
        return reg_file

    def _is_self_protected_action(self, action: ActionPlan) -> bool:
        if action.action_type not in {"delete", "uninstall", "powershell", "reg", "task", "service"}:
            return False

        target = action.target.replace("\\", "/")
        if any(marker.replace("\\", "/") in target for marker in self.protected_markers):
            return True

        # destructive shell snippets with quoted paths
        lowered = target.lower()
        destructive = any(token in lowered for token in [" del ", "del /", "remove-item", "rd /", "rmdir "])
        if destructive:
            try:
                for token in shlex.split(target):
                    normalized = token.replace("\\", "/")
                    if any(marker.replace("\\", "/") in normalized for marker in self.protected_markers):
                        return True
            except Exception:
                return any(marker.lower() in lowered for marker in [m.lower() for m in self.protected_markers])

        return False

    def execute(self, dry_run: bool = True) -> list[str]:
        results: list[str] = []
        if not dry_run:
            snapshot = self.create_snapshot()
            results.append(f"✅ Snapshot erstellt: {snapshot.name}")

        for action in self.plan:
            try:
                if self._is_self_protected_action(action):
                    results.append(f"🛡️ GEBLOCKT (Self-Protection): {action.description}")
                    continue

                if dry_run:
                    preview = action.dry_run_preview or action.description
                    results.append(f"[DRY-RUN] {preview}")
                    continue

                if action.action_type in {"powershell", "service", "task", "reg"}:
                    cmd = ["powershell", "-NoProfile", "-Command", action.target]
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
                elif action.action_type == "keep_merged":
                    results.append(f"✅ Merge gespeichert: {action.description}")
                else:
                    subprocess.run(action.target, shell=True, check=True, capture_output=True, text=True)
                results.append(f"✅ Erfolgreich: {action.description}")
            except Exception as exc:
                results.append(f"❌ FEHLER: {action.description} → {exc}")
        return results

    def undo_last_snapshot(self) -> str:
        snaps = sorted(self.backup_dir.glob("*.reg"))
        if not snaps:
            return "Kein Snapshot gefunden."
        latest = snaps[-1]
        subprocess.run(["reg", "import", str(latest)], check=False, capture_output=True)
        return f"Undo gestartet: {latest.name} (manuelle Prüfung empfohlen)"
