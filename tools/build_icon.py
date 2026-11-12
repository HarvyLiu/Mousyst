"""Generate the placeholder black/white calligraphic application icon."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6.QtWidgets import QApplication

from tray import app_icon

app = QApplication([])
assert (
    app_icon()
    .pixmap(256, 256)
    .save(str(Path(__file__).resolve().parents[1] / "src/ui/mousyst.ico"), "ICO")
)
