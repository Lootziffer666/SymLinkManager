from __future__ import annotations

import sys
from pathlib import Path

try:
    from Tabula.core.duplicate_finder import scan_duplicates
    from Tabula.core.smart_merge import smart_merge_documents
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from Tabula.core.duplicate_finder import scan_duplicates
    from Tabula.core.smart_merge import smart_merge_documents


def to_long_path(path: Path) -> str:
    s = str(path.resolve())
    return s if s.startswith("\\\\?\\") else f"\\\\?\\{s}"


def main() -> None:
    folder = Path(input("Ordner für Duplikatscan: ").strip() or ".")
    groups = scan_duplicates(str(folder))
    if not groups:
        print("Keine Duplikatgruppen gefunden.")
        return

    for i, g in enumerate(groups, 1):
        best = g.best_file.name if g.best_file else "-"
        print(f"[{i}] {len(g.files)} Dateien | Keep Best: {best} | Fusion: {g.fusion_possible}")
        for f in g.files:
            print("   -", to_long_path(f))

    if input("Fusion der ersten Gruppe testen? (j/n): ").lower() == "j" and groups[0].fusion_possible:
        out, msg = smart_merge_documents(groups[0].files[0], groups[0].files[1])
        print("✅", msg, out)


if __name__ == "__main__":
    main()
