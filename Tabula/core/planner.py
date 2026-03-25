from __future__ import annotations

import datetime as _dt
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List

from .models import ActionPlan, ExecutionTiming

# ---------------------------------------------------------------------------
# Load system-critical blocklist from rules/
# ---------------------------------------------------------------------------

_RULES_DIR = (Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]) / "rules"


def _load_rules_lines(filename: str) -> list[str]:
    """Return non-empty, non-comment lines from a rules text file."""
    path = _RULES_DIR / filename
    if not path.exists():
        return []
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped.lower())
    return lines


_TASK_WHITELIST: list[str] = _load_rules_lines("task-whitelist.txt")
_TASK_BLACKLIST: list[str] = _load_rules_lines("task-blacklist.txt")
_PROGRAM_WHITELIST: list[str] = _load_rules_lines("whitelist.txt")

# Hard-block patterns (these paths must NEVER be modified without explicit admin intent)
_SYSTEM_BLOCK_PATTERNS: list[str] = [
    "\\windows\\system32\\",
    "\\windows\\syswow64\\",
    "\\windows\\winsxs\\",
    "\\microsoft\\windows defender\\",
    "\\microsoft\\windows\\windowsupdate",
    "\\microsoft\\windows\\updateorchestrator",
    "\\microsoft\\windows\\waasmedic",
    "\\microsoft\\windows\\systemrestore",
]

_DEFERRED_ACTIONS_FILE = Path("tabula_deferred_actions.json")


class SafePlanner:
    def __init__(self) -> None:
        self.plan: List[ActionPlan] = []
        self.backup_dir = Path("tabula_backups")
        self.backup_dir.mkdir(exist_ok=True)
        # Self-protection: these path fragments must not be targeted by delete/uninstall
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
        high_risk = [a for a in self.plan if a.risk in {"High", "Critical"}]
        now_count = sum(1 for a in self.plan if a.execution_timing == ExecutionTiming.NOW.value)
        relogin_count = sum(1 for a in self.plan if a.execution_timing == ExecutionTiming.AFTER_RELOGIN.value)
        restart_count = sum(1 for a in self.plan if a.execution_timing == ExecutionTiming.AFTER_RESTART.value)
        lines = [
            f"• [{a.execution_timing}] {a.description} ({a.risk})"
            + (" ⚠️ HIGH RISK" if a.risk in {"High", "Critical"} else "")
            for a in self.plan
        ]
        timing_summary = f"Sofort: {now_count} | Nach Re-Login: {relogin_count} | Nach Neustart: {restart_count}"
        return (
            f"Geplanter Impact: {len(self.plan)} Aktionen • ~{total_mb:.1f} MB\n"
            f"Neustart erforderlich: {'JA' if reboot else 'Nein'}\n"
            f"Zeitplan: {timing_summary}\n"
            f"High-Risk Aktionen: {len(high_risk)}\n\n"
            + "\n".join(lines)
        )

    def high_risk_count(self) -> int:
        return sum(1 for a in self.plan if a.risk in {"High", "Critical"})

    def create_snapshot(self) -> Path:
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        reg_file = self.backup_dir / f"snapshot_{ts}.reg"
        subprocess.run(["reg", "export", "HKLM", str(reg_file), "/y"], check=False, capture_output=True)
        return reg_file

    def _is_protected_system_target(self, target: str) -> bool:
        """Check whether a target string touches a system-critical path or protected task."""
        lowered = target.lower().replace("\\", "/")
        for pattern in _SYSTEM_BLOCK_PATTERNS:
            if pattern.replace("\\", "/") in lowered:
                return True
        # Also check task whitelist: task actions targeting whitelisted paths are blocked
        if any(wl.replace("\\", "/") in lowered for wl in _TASK_WHITELIST):
            return True
        return False

    def _is_self_protected_action(self, action: ActionPlan) -> bool:
        if action.action_type not in {"delete", "uninstall", "powershell", "reg", "task", "service"}:
            return False

        target = action.target.replace("\\", "/")

        # Check self-protection markers
        if any(marker.replace("\\", "/") in target for marker in self.protected_markers):
            return True

        # Check hard system-critical blocklist
        if self._is_protected_system_target(action.target):
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

    def _save_deferred(self, actions: list[ActionPlan], timing: str) -> Path:
        """Persist deferred actions to a JSON file for later processing."""
        existing: list[dict] = []
        if _DEFERRED_ACTIONS_FILE.exists():
            try:
                existing = json.loads(_DEFERRED_ACTIONS_FILE.read_text(encoding="utf-8"))
            except Exception:
                existing = []
        for action in actions:
            entry = action.model_dump()
            entry["deferred_timing"] = timing
            entry["deferred_at"] = _dt.datetime.now().isoformat()
            existing.append(entry)
        _DEFERRED_ACTIONS_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        return _DEFERRED_ACTIONS_FILE

    def execute(self, dry_run: bool = True) -> list[str]:
        results: list[str] = []
        if not dry_run:
            snapshot = self.create_snapshot()
            results.append(f"✅ Snapshot erstellt: {snapshot.name}")

        deferred_relogin: list[ActionPlan] = []
        deferred_restart: list[ActionPlan] = []

        for action in self.plan:
            try:
                if self._is_self_protected_action(action):
                    results.append(f"🛡️ GEBLOCKT (Self-Protection): {action.description}")
                    continue

                if dry_run:
                    preview = action.dry_run_preview or action.description
                    timing_label = f"[{action.execution_timing}]" if hasattr(action, "execution_timing") else ""
                    results.append(f"[DRY-RUN]{timing_label} {preview}")
                    continue

                # Handle deferred timing
                timing = getattr(action, "execution_timing", ExecutionTiming.NOW.value)
                if timing == ExecutionTiming.AFTER_RELOGIN.value:
                    deferred_relogin.append(action)
                    results.append(f"⏸️ ZURÜCKGESTELLT (nach Re-Login): {action.description}")
                    continue
                if timing == ExecutionTiming.AFTER_RESTART.value:
                    deferred_restart.append(action)
                    results.append(f"⏸️ ZURÜCKGESTELLT (nach Neustart): {action.description}")
                    continue

                # Execute immediately
                if action.action_type in {"powershell", "service", "task", "reg"}:
                    cmd = ["powershell", "-NoProfile", "-Command", action.target]
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
                elif action.action_type == "keep_merged":
                    results.append(f"✅ Merge gespeichert: {action.description}")
                    continue
                else:
                    subprocess.run(action.target, shell=True, check=True, capture_output=True, text=True)
                results.append(f"✅ Erfolgreich: {action.description}")
            except Exception as exc:
                results.append(f"❌ FEHLER: {action.description} → {exc}")

        if deferred_relogin:
            out = self._save_deferred(deferred_relogin, ExecutionTiming.AFTER_RELOGIN.value)
            results.append(f"📋 {len(deferred_relogin)} Aktion(en) nach Re-Login gespeichert → {out.name}")
        if deferred_restart:
            out = self._save_deferred(deferred_restart, ExecutionTiming.AFTER_RESTART.value)
            results.append(f"📋 {len(deferred_restart)} Aktion(en) nach Neustart gespeichert → {out.name}")

        return results

    def undo_last_snapshot(self) -> str:
        snaps = sorted(self.backup_dir.glob("*.reg"))
        if not snaps:
            return "Kein Snapshot gefunden."
        latest = snaps[-1]
        subprocess.run(["reg", "import", str(latest)], check=False, capture_output=True)
        return f"Undo gestartet: {latest.name} (manuelle Prüfung empfohlen)"
