from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path


def setup_logging(log_dir: Path | None = None) -> Path:
    base_dir = log_dir or (Path(__file__).resolve().parents[1] / "logs")
    base_dir.mkdir(parents=True, exist_ok=True)
    log_file = base_dir / "tabula.log"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if not any(isinstance(handler, logging.FileHandler) and Path(getattr(handler, "baseFilename", "")) == log_file for handler in logger.handlers):
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return log_file


def install_global_excepthook() -> None:
    def _hook(exc_type, exc_value, exc_tb):
        logging.getLogger("tabula.crash").critical(
            "Unhandled exception: %s\n%s",
            exc_value,
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )

    sys.excepthook = _hook
