from __future__ import annotations

from .models import ActionPlan


def create_recall_protection_plan() -> list[ActionPlan]:
    return [
        ActionPlan(
            action_type="powershell",
            target='Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI" -Name "DisableRecall" -Type DWord -Value 1 -Force',
            description="Recall deaktivieren",
            risk="High",
            requires_reboot=True,
            dry_run_preview="Würde Windows Recall per Policy deaktivieren",
        ),
        ActionPlan(
            action_type="powershell",
            target='Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI" -Name "NpuUsageLimit" -Type DWord -Value 0 -Force',
            description="NPU-Nutzung für Copilot begrenzen",
            risk="Medium",
            dry_run_preview="Würde NPU-Usage-Limit setzen",
        ),
    ]
