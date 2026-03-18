from __future__ import annotations

from pathlib import Path
from typing import Dict

import xxhash
from rapidfuzz import fuzz

from .smart_merge import smart_merge_documents


class DuplicateGroup:
    def __init__(self, files: list[Path]):
        self.files = files
        self.best_file: Path | None = None
        self.score_dict: Dict[Path, float] = {}
        self.fusion_possible = False


def _text_content(file: Path) -> str:
    if file.suffix.lower() in {".txt", ".md", ".py"}:
        return file.read_text(encoding="utf-8", errors="ignore")[:5000]
    return ""


def _full_file_digest(file: Path, chunk_size: int = 1024 * 1024) -> str:
    hasher = xxhash.xxh64()
    with file.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_keep_best_scores(files: list[Path]) -> dict[Path, float]:
    scores: dict[Path, float] = {}
    text_cache = {f: _text_content(f) for f in files}

    for file in files:
        try:
            size_kb = file.stat().st_size / 1024
            mtime_score = file.stat().st_mtime / 1e9
            text = text_cache[file]
            word_score = len(text.split()) / 1000 if text else 0.0

            uniqueness = 100.0
            if text:
                for other in files:
                    if other == file:
                        continue
                    other_text = text_cache[other]
                    if other_text:
                        sim = fuzz.token_sort_ratio(text, other_text)
                        uniqueness = min(uniqueness, 100 - sim)

            score = (word_score * 0.30) + (size_kb * 0.25) + (mtime_score * 0.20) + (uniqueness * 0.25)
            scores[file] = round(score, 2)
        except Exception:
            scores[file] = 0.0

    return scores


def scan_duplicates(folder_path: str, similarity_threshold: int = 85) -> list[DuplicateGroup]:
    folder = Path(folder_path)
    if not folder.exists():
        return []

    candidates = {".txt", ".docx", ".pdf", ".jpg", ".png", ".mp3", ".wav"}
    hash_groups: dict[str, list[Path]] = {}

    for file in folder.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in candidates:
            continue
        try:
            digest = _full_file_digest(file)
            hash_groups.setdefault(digest, []).append(file)
        except Exception:
            continue

    groups: list[DuplicateGroup] = []
    for files in hash_groups.values():
        if len(files) < 2:
            continue

        group = DuplicateGroup(files)
        group.score_dict = calculate_keep_best_scores(files)
        group.best_file = max(group.score_dict, key=group.score_dict.get)
        group.fusion_possible = any(f.suffix.lower() in {".txt", ".docx", ".pdf"} for f in files)
        groups.append(group)

    return groups


__all__ = ["DuplicateGroup", "scan_duplicates", "calculate_keep_best_scores", "smart_merge_documents"]
