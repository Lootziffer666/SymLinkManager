from __future__ import annotations

import argparse
import json
from pathlib import Path

TABULA_ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = TABULA_ROOT / "profiles"
MODULES_FILE = TABULA_ROOT / "modules.json"


def list_profiles() -> list[str]:
    return sorted(p.name for p in PROFILES_DIR.glob("*.modules.json"))


def apply_profile(profile_name: str) -> Path:
    source = PROFILES_DIR / profile_name
    if not source.exists():
        available = ", ".join(list_profiles())
        raise FileNotFoundError(f"Profile '{profile_name}' nicht gefunden. Verfügbar: {available}")

    data = json.loads(source.read_text(encoding="utf-8"))
    MODULES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return MODULES_FILE


def main() -> int:
    parser = argparse.ArgumentParser(description="Tabula Modulprofil anwenden")
    parser.add_argument("profile", nargs="?", default="core_only.modules.json", help="Dateiname unter Tabula/profiles")
    parser.add_argument("--list", action="store_true", help="Verfügbare Profile anzeigen")
    args = parser.parse_args()

    if args.list:
        for profile in list_profiles():
            print(profile)
        return 0

    target = apply_profile(args.profile)
    print(f"✅ Profil angewendet: {args.profile} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
