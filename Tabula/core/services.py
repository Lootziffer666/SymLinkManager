from __future__ import annotations

from .models import ActionPlan


def create_service_preset(mode: str) -> list[ActionPlan]:
    presets = {
        "Gaming": ["DiagTrack", "SysMain"],
        "Minimal": ["DiagTrack", "SysMain", "WSearch", "XblAuthManager"],
    }

    plan: list[ActionPlan] = []
    for svc in presets.get(mode, []):
        plan.append(
            ActionPlan(
                action_type="service",
                target=f'Set-Service -Name "{svc}" -StartupType Disabled; Stop-Service -Name "{svc}" -Force',
                description=f"Service deaktivieren: {svc}",
                impact_mb=5.0,
                risk="Medium",
                requires_reboot=False,
                dry_run_preview=f"Würde Service {svc} deaktivieren/stoppen",
            )
        )
    return plan
