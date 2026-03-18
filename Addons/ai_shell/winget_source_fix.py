from __future__ import annotations

import subprocess


def fix_winget(execute: bool = False) -> None:
    cmds = ["winget source reset --force", "winget source update"]
    for c in cmds:
        if execute:
            subprocess.run(c, shell=True, check=False)
            print("[EXEC]", c)
        else:
            print("[PREVIEW]", c)


if __name__ == "__main__":
    fix_winget(execute=input("Echt ausführen? (j/n): ").lower() == "j")
