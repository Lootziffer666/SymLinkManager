from __future__ import annotations

import logging

from core.logging_utils import install_global_excepthook, setup_logging
from gui.main_window import TabulaApp


if __name__ == "__main__":
    log_path = setup_logging()
    install_global_excepthook()
    logger = logging.getLogger("tabula.bootstrap")
    logger.info("Tabula start requested")
    logger.info("Crash logs: %s", log_path)

    try:
        app = TabulaApp()
        app.mainloop()
    except Exception:
        logger.exception("Fatal crash during startup/mainloop")
        raise
