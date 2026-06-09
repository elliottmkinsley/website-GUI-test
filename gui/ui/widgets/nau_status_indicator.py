"""Bottom-right corner widget that shows whether the NAU SMB share
is currently reachable.

* Green dot + "NAU server active" when the share is reachable.
* Red dot + "NAU server unreachable" + a ``?`` help button that
  pops up an explanation. The most common cause is "you're not on
  an NAU computer", but it can also be a missing share permission
  on the user's account.

Probing runs on a worker ``QThread`` every ``POLL_INTERVAL_MS`` so a
slow / timing-out SMB lookup never freezes the UI. The first probe
fires immediately on ``start()`` so the user sees the real state
within a couple of seconds of launch.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QToolButton,
    QWidget,
)

from gui.config import nau_smb_default_path
from gui.deploy.smb_publisher import probe_reachable

log = logging.getLogger(__name__)

# How often to re-probe the share, in milliseconds. 30 s is gentle
# enough to keep network noise low but quick enough that the user
# sees a state change soon after mounting / unmounting the share.
POLL_INTERVAL_MS = 30_000

# Brand-ish red / green - readable against both light and dark
# status-bar backgrounds.
_GREEN = "#2ea043"
_RED = "#cf222e"
_GRAY = "#8c959f"

_HELP_TITLE = "NAU server unreachable"
_HELP_TEXT_TEMPLATE = (
    "The Radiant Content GUI couldn't reach the NAU file share:\n\n"
    "    {target}\n\n"
    "You'll be able to edit content offline, but the Publish feature "
    "needs the share to be reachable.\n\n"
    "Most common causes:\n\n"
    "\u2022 You're not on an NAU computer. The share is only "
    "accessible from inside the NAU domain - a library workstation, "
    "an NAU-issued laptop on the campus network, or a remote-desktop "
    "session into an NAU machine all work.\n\n"
    "\u2022 You are on NAU but your account doesn't have access. "
    "Contact NAU ITS and ask them to grant your account access to "
    "the Radiant Web share at:\n\n"
    "    \\\\arshares.ucc.nau.edu\\Web\\radiant.nau.edu"
)


class _ProbeOnce(QThread):
    """One-shot worker thread that runs a single reachability check
    and emits the result."""

    finishedWithResult = Signal(bool)

    def run(self) -> None:  # noqa: D401 - QThread API
        try:
            ok = probe_reachable()
        except Exception:  # noqa: BLE001
            log.exception("NAU probe raised; treating as unreachable")
            ok = False
        self.finishedWithResult.emit(ok)


class NauStatusIndicator(QWidget):
    """Compact status indicator suitable for a ``QStatusBar``.

    Layout: ``[dot] <text> [?]``
    The ``?`` button is hidden when the share is reachable.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker: _ProbeOnce | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._kick_probe)
        self._build()
        self._apply_state(None)

    # ---- build ------------------------------------------------------------

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        self._dot = QLabel("\u25cf")  # BLACK CIRCLE
        # We deliberately bypass theme.qss so the indicator stays
        # visible regardless of label-class rules elsewhere.
        self._dot.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._dot.setStyleSheet(
            f"color: {_GRAY}; font-size: 14px; background: transparent;"
        )
        layout.addWidget(self._dot)

        self._text = QLabel("Checking NAU server...")
        self._text.setStyleSheet("background: transparent;")
        layout.addWidget(self._text)

        self._help_button = QToolButton(self)
        self._help_button.setText("?")
        self._help_button.setToolTip("Why is the NAU server unreachable?")
        self._help_button.setCursor(Qt.CursorShape.WhatsThisCursor)
        self._help_button.setStyleSheet(
            "QToolButton {"
            "  background: transparent;"
            "  border: 1px solid #c5cee0;"
            "  border-radius: 8px;"
            "  padding: 0 6px;"
            "  font-weight: 700;"
            f"  color: {_RED};"
            "}"
            "QToolButton:hover {"
            "  background-color: #fbecef;"
            "}"
        )
        self._help_button.clicked.connect(self._show_help)
        self._help_button.setVisible(False)
        layout.addWidget(self._help_button)

    # ---- public API -------------------------------------------------------

    def start(self) -> None:
        """Begin periodic probing. Safe to call multiple times."""
        if not self._timer.isActive():
            self._timer.start()
        self._kick_probe()

    def stop(self) -> None:
        self._timer.stop()
        worker = self._worker
        self._worker = None
        if worker is not None:
            try:
                worker.wait(1000)
            except RuntimeError:
                pass

    def refresh(self) -> None:
        """Run a probe immediately (without waiting for the timer)."""
        self._kick_probe()

    # ---- internal ---------------------------------------------------------

    def _kick_probe(self) -> None:
        # Skip if a previous probe is still running - SMB lookups can
        # block for tens of seconds on a misconfigured Windows
        # network and we don't want a queue of stale workers.
        if self._worker is not None and self._worker.isRunning():
            return
        worker = _ProbeOnce(self)
        worker.finishedWithResult.connect(self._on_probe_result)
        worker.finished.connect(self._on_probe_finished)
        self._worker = worker
        worker.start()

    def _on_probe_result(self, ok: bool) -> None:
        self._apply_state(ok)

    def _on_probe_finished(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()

    def _apply_state(self, ok: bool | None) -> None:
        target = nau_smb_default_path()
        if ok is None:
            self._dot.setStyleSheet(
                f"color: {_GRAY}; font-size: 14px; background: transparent;"
            )
            self._text.setText("Checking NAU server...")
            self._text.setToolTip(target)
            self._help_button.setVisible(False)
            return
        if ok:
            self._dot.setStyleSheet(
                f"color: {_GREEN}; font-size: 14px; background: transparent;"
            )
            self._text.setText("NAU server active")
            self._text.setToolTip(f"Reachable: {target}")
            self._help_button.setVisible(False)
        else:
            self._dot.setStyleSheet(
                f"color: {_RED}; font-size: 14px; background: transparent;"
            )
            self._text.setText("NAU server unreachable")
            self._text.setToolTip(f"Unreachable: {target}")
            self._help_button.setVisible(True)

    def _show_help(self) -> None:
        QMessageBox.information(
            self,
            _HELP_TITLE,
            _HELP_TEXT_TEMPLATE.format(target=nau_smb_default_path()),
        )
