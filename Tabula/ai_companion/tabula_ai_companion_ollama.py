from __future__ import annotations

import json
from pathlib import Path

import ollama

PROMPT_TEMPLATE = """
Du bist Tabula AI Companion. Arbeite konservativ und sicher.

Tabula Export (gekürzt):
{export_payload}

Aktive Module:
{active_modules}

User-Profil:
{profile_payload}

Regeln:
- Nur Aktionen für aktive Module vorschlagen.
- Wenn ein Modul fehlt/deaktiviert ist: stattdessen Hinweis in notes.

Erzeuge exakt dieses JSON-Format:
{{
  "plan_name": "Tabula Smart Profile",
  "module_scope": ["programs", "privacy"],
  "actions": [{{
    "action_type": "remove_appx|uninstall|disable_task|reg_set|keep_merged|investigate",
    "target": "...",
    "description": "...",
    "risk": "Low|Medium|High|Critical",
    "requires_reboot": false
  }}],
  "recommended_presets": ["..."],
  "notes": "..."
}}
"""


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def ask_profile() -> dict:
    return {
        "usage": input("Nutzung (Gamer/Creator/Office/Developer/Minimal): ").strip(),
        "never_remove": [x.strip() for x in input("Nie entfernen (kommagetrennt): ").split(",") if x.strip()],
        "ai_features": input("AI Features behalten? (ja/nein): ").strip(),
        "privacy": input("Privacy (Balanced/Strict/Paranoid): ").strip(),
        "priority": input("Priorität (Akku/Performance/Balanced): ").strip(),
    }


def active_module_ids(module_cfg: dict) -> list[str]:
    return [module_id for module_id, enabled in module_cfg.items() if enabled]


def generate_plan(export_data: dict, profile: dict, modules_cfg: dict, model: str = "llama3.2") -> dict:
    prompt = PROMPT_TEMPLATE.format(
        export_payload=json.dumps(export_data, ensure_ascii=False)[:5000],
        profile_payload=json.dumps(profile, ensure_ascii=False),
        active_modules=json.dumps(active_module_ids(modules_cfg), ensure_ascii=False),
    )
    response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return json.loads(response["message"]["content"])


def main() -> None:
    export_path = Path(input("Pfad zu Tabula-Export JSON: ").strip())
    modules_path_raw = input("Pfad zu modules.json (leer = ../modules.json): ").strip()
    modules_path = Path(modules_path_raw) if modules_path_raw else (Path(__file__).resolve().parents[1] / "modules.json")

    export_data = load_json(export_path)
    modules_cfg = load_json(modules_path)
    profile = ask_profile()
    plan = generate_plan(export_data, profile, modules_cfg)

    out = Path("tabula_import_plan.json")
    out.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Plan gespeichert: {out}")


if __name__ == "__main__":
    main()
