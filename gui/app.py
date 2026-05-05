"""QApplication bootstrap.

This module is intentionally tiny - it instantiates QApplication,
loads the QSS theme, builds the main window, and starts the event
loop. Page wiring happens in ``gui.ui.main_window``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from gui.ui.main_window import MainWindow

THEME_QSS = Path(__file__).resolve().parent / "theme.qss"


def run(argv: Sequence[str]) -> int:
    """Entry point used by ``__main__``. Returns the Qt exit code."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(list(argv))
    app.setApplicationName("Radiant Content GUI")
    app.setOrganizationName("Radiant Center for Remote Sensing")
    app.setOrganizationDomain("radiant.nau.edu")

    if THEME_QSS.exists():
        app.setStyleSheet(THEME_QSS.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    return app.exec()
