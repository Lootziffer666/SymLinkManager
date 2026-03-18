from __future__ import annotations

from .models import ActionPlan


def create_telemetry_preset(preset: str) -> list[ActionPlan]:
    keys = {
        "Balanced": [
            (r"HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 1),
            (r"HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 0),
        ],
        "Strict": [
            (r"HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0),
            (r"HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 0),
        ],
        "Paranoid": [
            (r"HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0),
            (r"HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search", "AllowCortana", 0),
            (r"HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 0),
        ],
    }

    plan: list[ActionPlan] = []
    for path, name, value in keys.get(preset, []):
        plan.append(
            ActionPlan(
                action_type="reg",
                target=f'Set-ItemProperty -Path "{path}" -Name "{name}" -Type DWord -Value {value} -Force',
                description=f"Privacy: {name}={value}",
                risk="Low",
                dry_run_preview=f"Würde {path}::{name} auf {value} setzen",
            )
        )
    return plan
