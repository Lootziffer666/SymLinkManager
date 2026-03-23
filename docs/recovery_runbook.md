# Tabula Suite – Recovery Runbook

> **Audience:** Power users and administrators who need to reverse, repair, or audit Tabula Suite actions.

---

## 1. Before You Start

- Always verify your current system state before using any recovery procedure.
- If Tabula produced a snapshot (`.reg` file in `tabula_backups/`), use it **before** making further changes.
- When in doubt, run in **Dry-Run** mode first and read the output carefully.

---

## 2. Registry Snapshot Restore

Tabula's `SafePlanner` creates a registry snapshot before every live execution run.

**Location:** `tabula_backups/snapshot_<YYYYMMDD_HHMMSS>.reg`

**To restore the last snapshot:**

```powershell
# List available snapshots
Get-ChildItem tabula_backups\*.reg | Sort-Object Name

# Import the latest snapshot (run as Administrator)
$latest = (Get-ChildItem tabula_backups\*.reg | Sort-Object Name -Descending | Select-Object -First 1).FullName
reg import $latest
```

> ⚠️ Registry imports are additive by default. Deleted keys are NOT automatically re-created. Manually verify critical keys after import.

---

## 3. Deferred Actions File

When actions are scheduled for "After Relogin" or "After Restart", they are saved to `tabula_deferred_actions.json`.

**To review deferred actions without executing:**

```powershell
Get-Content tabula_deferred_actions.json | ConvertFrom-Json | Format-Table description, risk, execution_timing
```

**To discard all deferred actions:**

```powershell
Remove-Item tabula_deferred_actions.json
```

**To execute deferred actions manually (PowerShell):**

```powershell
$actions = (Get-Content tabula_deferred_actions.json | ConvertFrom-Json)
foreach ($action in $actions) {
    Write-Host "Would run: $($action.target)" -ForegroundColor Cyan
    # Remove Write-Host and uncomment below to actually execute:
    # Invoke-Expression $action.target
}
```

---

## 4. Undo a Purge Plan (Tabula Rasa)

Tabula Rasa in `DryRun` and `RecycleBinPreferred` (Safe) modes does **not** permanently delete files.

- **DryRun:** No files were modified. Check `TabulaRasa/backups/logs/` for what would have been deleted.
- **Safe mode (Recycle Bin):** Restore deleted items from the Windows Recycle Bin (`Win + R → shell:RecycleBinFolder`).
- **PermanentDelete (Aggressive):** Files are unrecoverable via standard means. Use a file-recovery tool (e.g., Recuva) immediately, before the disk sectors are overwritten.

**Ledger file location:** `TabulaRasa/backups/history.json`

---

## 5. Undo a Relocation (Tabula)

Relocations are recorded in `Tabula/backups/relocations.json` but are **planned only** (no physical files are moved in the current build).

**To review planned relocations:**

```powershell
Get-Content Tabula\backups\relocations.json | ConvertFrom-Json | Format-Table source_path, target_path, status
```

---

## 6. UWP / AppX Restore

If a UWP package was removed via the `Remove-AppxPackage` command:

```powershell
# Re-install from the Microsoft Store (most apps)
# Open Microsoft Store and search for the app name

# Or re-provision system apps (Administrator):
Get-AppxPackage -AllUsers | Where-Object {$_.Name -like "*<PackageName>*"} | Add-AppxPackage -DisableDevelopmentMode
```

---

## 7. Service Re-enable

If a Windows service was disabled via the Gaming/Minimal preset:

```powershell
# Re-enable a service (example: SysMain / Superfetch)
Set-Service -Name "SysMain" -StartupType Automatic
Start-Service -Name "SysMain"

# Common services disabled by Tabula presets:
# DiagTrack   – Connected User Experiences and Telemetry
# SysMain     – Superfetch (memory pre-loading)
# WSearch     – Windows Search indexer
# XblAuthManager – Xbox Live authentication
```

---

## 8. Privacy / Registry Preset Undo

Privacy presets write `DWORD` values to policy registry paths. To reverse:

```powershell
# Re-enable telemetry (AllowTelemetry = 1)
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection" -Name "AllowTelemetry" -Type DWord -Value 1

# Re-enable advertising ID
Set-ItemProperty -Path "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo" -Name "Enabled" -Type DWord -Value 1

# Re-enable Cortana
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search" -Name "AllowCortana" -ErrorAction SilentlyContinue
```

---

## 9. Windows Recall / NPU Guard Undo

```powershell
# Re-enable Windows Recall
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsAI" -Name "DisableRecall" -ErrorAction SilentlyContinue

# Remove NPU limit
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsAI" -Name "NpuUsageLimit" -ErrorAction SilentlyContinue
```

---

## 10. Log Files

| Tool | Log Location |
|------|-------------|
| Tabula | `Tabula/logs/tabula.log` |
| Tabula Rasa | `TabulaRasa/logs/tabula_rasa.log` |
| Action audit | `Tabula/backups/actions.json` |
| Purge history | `TabulaRasa/backups/history.json` |
| Relocation ledger | `Tabula/backups/relocations.json` |
| Deferred actions | `tabula_deferred_actions.json` (working directory) |

---

## 11. Escalation Path

If you cannot recover using the above procedures:

1. Boot into Windows Recovery Environment (WinRE) – press **F8** or hold Shift while clicking Restart.
2. Use **System Restore** to roll back to a restore point prior to the Tabula run.
3. If registry damage is suspected, use `sfc /scannow` and `DISM /Online /Cleanup-Image /RestoreHealth` from an elevated PowerShell prompt.
