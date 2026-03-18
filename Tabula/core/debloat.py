from __future__ import annotations

from .models import ActionPlan, UWPEntry
from .scanners import scan_uwp_apps


def get_uwp_list() -> list[UWPEntry]:
    return scan_uwp_apps()


def create_safe_debloat_plan(packages: list[str]) -> list[ActionPlan]:
    plan: list[ActionPlan] = []
    for pkg in packages:
        plan.append(
            ActionPlan(
                action_type="powershell",
                target=f'Remove-AppxPackage -Package "{pkg}" -AllUsers',
                description=f"UWP-App entfernen: {pkg}",
                impact_mb=150.0,
                risk="Medium",
                dry_run_preview=f"Würde UWP entfernen: {pkg}",
            )
        )
    return plan
