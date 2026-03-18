from __future__ import annotations

import subprocess


def npu_guard(execute: bool = False) -> None:
    cmds = [
        'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI" /v DisableNPU /t REG_DWORD /d 1 /f',
        'taskkill /f /im Copilot.exe',
    ]
    for c in cmds:
        if execute:
            subprocess.run(c, shell=True, check=False)
            print("[EXEC]", c)
        else:
            print("[PREVIEW]", c)


if __name__ == "__main__":
    npu_guard(execute=input("Echt ausführen? (j/n): ").lower() == "j")
