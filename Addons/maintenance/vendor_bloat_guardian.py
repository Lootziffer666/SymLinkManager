from __future__ import annotations

import subprocess

OEM_TRIGGERS = {
    "HP": ["HPAppHelperCap", "HPSupportAssistantService", "HPSystemInfoCap"],
    "Lenovo": ["LenovoVantageService", "ImControllerService"],
    "Dell": ["SupportAssistAgent", "DellClientManagementService"],
}


def service_exists(name: str) -> bool:
    res = subprocess.run(["sc", "query", name], capture_output=True, text=True)
    return "SERVICE_NAME" in res.stdout


def run_ps(script: str, execute: bool) -> None:
    if not execute:
        print("[PREVIEW]", script)
        return
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=False)


def scan_and_block_oem(execute: bool = False) -> None:
    for vendor, services in OEM_TRIGGERS.items():
        for svc in services:
            if service_exists(svc):
                print(f"🛡️  {vendor} Trigger gefunden: {svc}")
                run_ps(f'Set-Service -Name "{svc}" -StartupType Disabled', execute)
                run_ps(f'Stop-Service -Name "{svc}" -Force', execute)
    print("✅ Fertig (Preview oder Apply).")


if __name__ == "__main__":
    execute = input("Echte Ausführung? (j/n): ").lower() == "j"
    scan_and_block_oem(execute=execute)
