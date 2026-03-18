# Tabula – Productization Checklist (v0.2 -> v1.0)

## Kern statt Nice-to-have
- [ ] Core-Profil als Default
- [ ] Add-ons explizit als Nightly
- [ ] Import/Export JSON stabil und rückwärtskompatibel
- [ ] Einheitliches Logging + Action-ID pro Schritt

## Qualität
- [ ] Smoke-Test in CI
- [ ] Mind. 10 End-to-End Windows Testfälle
- [ ] Regressionsliste für kritische Flows (Undo, Reboot, Restore)

## Sicherheit
- [ ] High-Risk Double-Confirm
- [ ] Blockliste für systemkritische Targets
- [ ] Dokumentierte Recovery-Runbooks

## Release readiness
- [ ] Versioniertes Changelog
- [ ] Signierter Release-Build
- [ ] Installierbarer Paketweg (MSIX/Installer)
