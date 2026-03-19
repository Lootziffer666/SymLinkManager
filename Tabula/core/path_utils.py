from __future__ import annotations

import os
import re
from pathlib import Path

PROTECTED_TREES = [
    r"%WINDIR%",
    r"%PROGRAMFILES%",
    r"%PROGRAMFILES(X86)%",
    r"%SYSTEMROOT%",
]

PROTECTED_EXACT_PATHS = [
    r"%USERPROFILE%",
    r"%USERPROFILE%\Desktop",
    r"%USERPROFILE%\Documents",
    r"%USERPROFILE%\Pictures",
    r"%USERPROFILE%\Videos",
    r"%USERPROFILE%\Music",
]

_ENV_PATTERN = re.compile(r"%([^%]+)%")


def expand_windows_path(path: str) -> str:
    def replace_var(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    expanded = _ENV_PATTERN.sub(replace_var, path)
    expanded = os.path.expandvars(expanded)
    expanded = expanded.replace("\\", os.sep)
    return os.path.expanduser(expanded)


def is_protected(path: str) -> bool:
    candidate = Path(expand_windows_path(path)).resolve(strict=False)

    for protected in PROTECTED_EXACT_PATHS:
        protected_path = Path(expand_windows_path(protected)).resolve(strict=False)
        if str(protected_path) == protected:
            continue
        if candidate == protected_path:
            return True

    for protected in PROTECTED_TREES:
        root = Path(expand_windows_path(protected)).resolve(strict=False)
        if str(root) == protected:
            continue
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


def folder_size(path: Path) -> tuple[int, int]:
    total = 0
    count = 0
    if not path.exists():
        return total, count
    for file_path in path.rglob("*"):
        if file_path.is_file():
            try:
                total += file_path.stat().st_size
                count += 1
            except OSError:
                continue
    return total, count
