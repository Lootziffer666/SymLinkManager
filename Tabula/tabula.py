from __future__ import annotations

import sys
from pathlib import Path

# Ensure Tabula root is in the module search path when launched directly
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.logging_utils import install_global_excepthook, setup_logging  # noqa: E402
from gui.main_window import TabulaApp  # noqa: E402

if __name__ == "__main__":
    setup_logging()
    install_global_excepthook()
    app = TabulaApp()
    app.mainloop()
