from __future__ import annotations

import importlib
import json
import os
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent


def print_result(ok: bool, label: str, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    suffix = f" :: {detail}" if detail else ""
    print(f"[{status}] {label}{suffix}")


def syntax_check() -> bool:
    ok = True
    for file_path in sorted(ROOT.rglob("*.py")):
        if "__pycache__" in file_path.parts:
            continue
        try:
            py_compile.compile(str(file_path), doraise=True)
        except Exception as exc:  # pragma: no cover
            ok = False
            print_result(False, f"syntax:{file_path.relative_to(ROOT)}", str(exc))
    if ok:
        print_result(True, "syntax", "all python files compiled")
    return ok


def json_and_catalog_check() -> bool:
    ok = True
    json_files = [Path("modules.json"), Path("micro_apps/catalog.json")]
    parsed: dict[str, dict] = {}
    for rel in json_files:
        try:
            parsed[str(rel)] = json.loads((ROOT / rel).read_text(encoding="utf-8"))
            print_result(True, f"json:{rel}")
        except Exception as exc:
            ok = False
            print_result(False, f"json:{rel}", str(exc))

    catalog = parsed.get("micro_apps/catalog.json", {})
    for app in catalog.get("apps", []):
        script = app.get("script", "")
        if not script:
            ok = False
            print_result(False, "catalog:script", f"missing script for {app.get('name', 'unknown')}")
            continue
        script_path = REPO_ROOT / script
        if script_path.exists():
            print_result(True, f"catalog:path:{app.get('name', script)}")
        else:
            ok = False
            print_result(False, f"catalog:path:{app.get('name', script)}", f"not found: {script}")

    return ok


def requirements_layout_check() -> bool:
    expected = [
        ROOT / "requirements.txt",
        ROOT / "requirements/base.txt",
        ROOT / "requirements/gui.txt",
        ROOT / "requirements/core.txt",
        ROOT / "requirements/ai_companion.txt",
        ROOT / "requirements/windows.txt",
        ROOT / "requirements/dev-smoke.txt",
    ]
    ok = True
    for file_path in expected:
        if file_path.exists():
            print_result(True, f"requirements:{file_path.relative_to(ROOT)}")
        else:
            ok = False
            print_result(False, f"requirements:{file_path.relative_to(ROOT)}", "missing")
    return ok



def profiles_check() -> bool:
    expected = [
        ROOT / "profiles/core_only.modules.json",
        ROOT / "profiles/full.modules.json",
    ]
    ok = True
    for file_path in expected:
        if file_path.exists():
            print_result(True, f"profiles:{file_path.relative_to(ROOT)}")
        else:
            ok = False
            print_result(False, f"profiles:{file_path.relative_to(ROOT)}", "missing")
    return ok

def dependency_check() -> bool:
    deps = [
        "customtkinter",
        "psutil",
        "py7zr",
        "pydantic",
        "PIL",
        "rapidfuzz",
        "xxhash",
        "docx",
        "fitz",
        "ollama",
    ]
    ok = True
    for dep in deps:
        try:
            importlib.import_module(dep)
            print_result(True, f"dep:{dep}")
        except Exception as exc:
            ok = False
            print_result(False, f"dep:{dep}", str(exc))

    if os.name == "nt":
        try:
            importlib.import_module("winreg")
            importlib.import_module("win32api")
            print_result(True, "dep:pywin32")
        except Exception as exc:
            ok = False
            print_result(False, "dep:pywin32", str(exc))
    else:
        print_result(True, "dep:pywin32", "skipped on non-Windows host")

    return ok


def import_check() -> bool:
    sys.path.insert(0, str(ROOT))
    modules = [
        "core.models",
        "core.planner",
        "core.scanners",
        "core.duplicate_finder",
        "gui.main_window",
        "gui.module_registry",
        "gui.modules.programs_module",
        "gui.modules.archive_module",
        "gui.modules.uwp_ai_module",
        "gui.modules.tasks_services_module",
        "gui.modules.privacy_module",
        "gui.modules.duplicates_module",
        "gui.modules.micro_apps_module",
        "gui.modules.plan_execute_module",
        "gui.modules.module_manager_module",
        "ai_companion.tabula_ai_companion_ollama",
    ]

    ok = True
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            print_result(True, f"import:{module_name}")
        except Exception as exc:
            ok = False
            print_result(False, f"import:{module_name}", str(exc))
    return ok


def gui_bootstrap_check() -> bool:
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        print_result(True, "gui-bootstrap", "skipped (headless environment)")
        return True

    try:
        from gui.main_window import TabulaApp

        app = TabulaApp()
        app.update_idletasks()
        app.destroy()
        print_result(True, "gui-bootstrap")
        return True
    except Exception as exc:
        print_result(False, "gui-bootstrap", str(exc))
        return False


def main() -> int:
    checks = [
        ("syntax", syntax_check),
        ("json-catalog", json_and_catalog_check),
        ("requirements", requirements_layout_check),
        ("profiles", profiles_check),
        ("deps", dependency_check),
        ("imports", import_check),
        ("gui", gui_bootstrap_check),
    ]

    results = [fn() for _, fn in checks]
    passed = sum(1 for result in results if result)
    total = len(results)
    print(f"\nSmoke summary: {passed}/{total} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
