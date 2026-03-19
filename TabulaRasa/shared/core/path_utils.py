from __future__ import annotations

import os
from pathlib import Path

PROTECTED_PATHS = [
    os.path.expandvars(r"%WINDIR%"),
    os.path.expandvars(r"%PROGRAMFILES%"),
    os.path.expandvars(r"%PROGRAMFILES(X86)%"),
    os.path.expandvars(r"%SYSTEMROOT%"),
    os.path.expandvars(r"%USERPROFILE%\\Documents"),
]


def expand_windows_path(path: str) -> str:
    expanded = os.path.expandvars(path)
    return os.path.expanduser(expanded)


def is_protected(path: str) -> bool:
    candidate = Path(expand_windows_path(path)).resolve(strict=False)
    for protected in PROTECTED_PATHS:
        if not protected:
            continue
        root = Path(expand_windows_path(protected)).resolve(strict=False)
        try:
            if candidate == root or candidate.is_relative_to(root):
                return True
        except ValueError:
            continue
    return False


def format_bytes(size_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size_bytes} B"


def folder_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return total
    for file_path in path.rglob("*"):
        if file_path.is_file():
            try:
                total += file_path.stat().st_size
            except OSError:
                continue
    return total
