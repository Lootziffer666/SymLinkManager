from __future__ import annotations

import sys
from pathlib import Path

# Ensure TabulaRasa root is in the module search path when launched directly
_ROOT = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import logging  # noqa: E402

from gui.main_window import TabulaRasaApp  # noqa: E402


def _setup_logging() -> None:
    base_dir = _ROOT / "logs"
    base_dir.mkdir(parents=True, exist_ok=True)
    log_file = base_dir / "tabula_rasa.log"
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        logger.addHandler(sh)


if __name__ == "__main__":
    _setup_logging()
    app = TabulaRasaApp()
    app.mainloop()
