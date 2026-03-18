# Tabula – Windows Live Test Playbook (Safe Mode)

## Ziel
Tabula auf echtem Windows testen, ohne das Hauptsystem zu gefährden.

## 1) Test-Stufen
1. **Stage A – VM first (Pflicht)**
   - Hyper-V/VMware/VirtualBox
   - Snapshot vor jedem Testlauf
2. **Stage B – Secondary machine / Test-Laptop**
   - Kein Daily-Driver
3. **Stage C – Host Canary auf Hauptsystem**
   - Nur Core-Profil
   - Nur Dry-Run + Export
4. **Stage D – Host Execute**
   - Erst nach 3+ erfolgreichen Canary-Zyklen

## 2) Minimal-Sicherheitsregeln
- Immer erst `Dry-Run`
- Vor Execute: Restore Point + Tabula-Snapshot
- High-Risk-Aktionen nur einzeln
- Nach jeder Aktion Verifikation + Reboot-Check

## 3) Empfohlener Start
```powershell
cd Tabula
python scripts/apply_profile.py core_only.modules.json
python tabula.py
```

## 4) Was NICHT live zuerst testen
- Nightly Add-ons
- aggressive Debloat-Presets
- Rekursive ACL-/Registry-Massenänderungen

## 5) Exit-Kriterien
- Kein Boot-/Login-Problem
- Windows Update, Defender, Store, OneDrive funktionieren
- Keine verlorenen Benutzerrechte / keine Profilkorruption
