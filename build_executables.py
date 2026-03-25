"""Build Tabula and TabulaRasa into standalone executables using PyInstaller.

Usage
-----
    python build_executables.py              # build both
    python build_executables.py tabula       # build only Tabula
    python build_executables.py tabularasa   # build only TabulaRasa
    python build_executables.py --onefile    # use single-file mode (slower startup)

Requirements
------------
    pip install -r Tabula/requirements/build.txt
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DIST_DIR = REPO_ROOT / "dist"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], label: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}\n")
    print(f"  > {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        print(f"\n❌ {label} failed (exit code {result.returncode})")
        sys.exit(result.returncode)
    print(f"\n✅ {label} succeeded")


def _collect_datas(entries: list[tuple[str, str]]) -> list[str]:
    """Convert (src, dest) tuples into PyInstaller --add-data arguments."""
    sep = ";" if sys.platform == "win32" else ":"
    args: list[str] = []
    for src, dest in entries:
        full = REPO_ROOT / src
        if full.exists():
            args += ["--add-data", f"{full}{sep}{dest}"]
        else:
            print(f"  ⚠ skipping missing data: {full}")
    return args


def _collect_hidden_imports(modules: list[str]) -> list[str]:
    args: list[str] = []
    for mod in modules:
        args += ["--hidden-import", mod]
    return args


# ---------------------------------------------------------------------------
# Build: Tabula
# ---------------------------------------------------------------------------

def build_tabula(*, onefile: bool = False) -> Path:
    entry = REPO_ROOT / "Tabula" / "tabula.py"

    datas = _collect_datas([
        ("Tabula/modules.json",           "."),
        ("Tabula/profiles",               "profiles"),
        ("Tabula/micro_apps",             "micro_apps"),
        ("rules",                         "rules"),
        ("schemas",                       "schemas"),
    ])

    hidden = _collect_hidden_imports([
        "core",
        "core.models",
        "core.planner",
        "core.scanners",
        "core.execution",
        "core.history",
        "core.logging_utils",
        "core.path_utils",
        "core.ai_protection",
        "core.benchmarks",
        "core.debloat",
        "core.duplicate_finder",
        "core.privacy",
        "core.services",
        "core.smart_merge",
        "gui",
        "gui.main_window",
        "gui.module_api",
        "gui.module_registry",
        "gui.modules.archive_module",
        "gui.modules.duplicates_module",
        "gui.modules.micro_apps_module",
        "gui.modules.module_manager_module",
        "gui.modules.plan_execute_module",
        "gui.modules.privacy_module",
        "gui.modules.programs_module",
        "gui.modules.tasks_services_module",
        "gui.modules.uwp_ai_module",
        "links.link_manager",
        "relocate.relocator",
        "ai_companion.tabula_ai_companion_ollama",
    ])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "Tabula",
        "--onefile" if onefile else "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--paths", str(REPO_ROOT / "Tabula"),
        *datas,
        *hidden,
        str(entry),
    ]
    _run(cmd, "Building Tabula")

    if onefile:
        return DIST_DIR / "Tabula.exe"
    return DIST_DIR / "Tabula"


# ---------------------------------------------------------------------------
# Build: TabulaRasa
# ---------------------------------------------------------------------------

def build_tabula_rasa(*, onefile: bool = False) -> Path:
    entry = REPO_ROOT / "TabulaRasa" / "tabula_rasa.py"

    datas = _collect_datas([
        ("TabulaRasa/shared/rule_packs", "shared/rule_packs"),
        ("TabulaRasa/backups",           "backups"),
    ])

    hidden = _collect_hidden_imports([
        "scanners",
        "scanners.known_paths",
        "scanners.rule_based",
        "shared",
        "shared.core",
        "shared.core.models",
        "shared.core.path_utils",
        "shared.engine",
        "shared.engine.execution",
        "shared.engine.history",
        "gui",
        "gui.main_window",
        "yaml",
    ])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "TabulaRasa",
        "--onefile" if onefile else "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--paths", str(REPO_ROOT / "TabulaRasa"),
        *datas,
        *hidden,
        str(entry),
    ]
    _run(cmd, "Building TabulaRasa")

    if onefile:
        return DIST_DIR / "TabulaRasa.exe"
    return DIST_DIR / "TabulaRasa"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Tabula / TabulaRasa executables with PyInstaller",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["all", "tabula", "tabularasa"],
        help="Which application to build (default: all)",
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Create a single .exe instead of a directory bundle",
    )
    args = parser.parse_args()

    # Ensure PyInstaller is available
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller not found. Installing …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"])

    results: list[str] = []

    if args.target in ("all", "tabula"):
        out = build_tabula(onefile=args.onefile)
        results.append(f"Tabula     → {out}")

    if args.target in ("all", "tabularasa"):
        out = build_tabula_rasa(onefile=args.onefile)
        results.append(f"TabulaRasa → {out}")

    print(f"\n{'=' * 60}")
    print("  Build Summary")
    print(f"{'=' * 60}")
    for line in results:
        print(f"  {line}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
