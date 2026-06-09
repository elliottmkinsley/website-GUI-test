"""Bottom-right status indicator for the workspace background sync.

Sits next to :class:`gui.ui.widgets.nau_status_indicator.NauStatusIndicator`
and tells the user when the workspace last successfully fetched
changes from ``origin/main``. Clicking it triggers an immediate
:meth:`gui.services.sync_manager.SyncManager.sync_now`.

States
------
* ``Syncing...`` (gray dot, spinner-ish ellipsis) while a pull is in flight.
* ``Synced just now / 3m ago`` (green dot) after a successful pull.
* ``Sync paused`` (gray dot) when paused (e.g., during a publish).
* ``Sync failed - click to retry`` (red dot) on hard failure.

The "X minutes ago" label is refreshed by an internal timer every
:data:`RELATIVE_TIME_TICK_MS` ms so the label drifts forward without
needing another network round-trip.
"""

from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QToolButton,
    QWidget,
)

from gui.services.sync_manager import SyncManager, SyncResult

log = logging.getLogger(__name__)

RELATIVE_TIME_TICK_MS = 30_000  # refresh "Xm ago" label every 30 s

_GREEN = "#2ea043"
_RED = "#cf222e"
_GRAY = "#8c959f"


class SyncIndicator(QWidget):
    """Compact status indicator for :class:`SyncManager`.

    Layout: ``[dot] <text> [refresh]``
    The refresh button is always visible; clicking it requests an
    immediate sync.
    """

    syncRequested = Signal()

    def __init__(
        self, manager: SyncManager, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._manager = manager
        self._last_result: SyncResult | None = None
        self._is_syncing: bool = False

        self._build()
        self._apply_state()

        # Refresh "Xm ago" labels without needing a new sync.
        self._tick = QTimer(self)
        self._tick.setInterval(RELATIVE_TIME_TICK_MS)
        self._tick.timeout.connect(self._apply_state)
        self._tick.start()

        manager.syncStarted.connect(self._on_sync_started)
        manager.syncFinished.connect(self._on_sync_finished)
        manager.pausedChanged.connect(lambda _paused: self._apply_state())

    # ---- build -----------------------------------------------------------

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        self._dot = QLabel("\u25cf")  # BLACK CIRCLE
        self._dot.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._dot.setStyleSheet(
            f"color: {_GRAY}; font-size: 14px; background: transparent;"
        )
        layout.addWidget(self._dot)

        self._text = QLabel("Workspace: idle")
        self._text.setStyleSheet("background: transparent;")
        layout.addWidget(self._text)

        self._refresh_button = QToolButton(self)
        self._refresh_button.setText("\u21bb")  # CLOCKWISE OPEN CIRCLE ARROW
        self._refresh_button.setToolTip("Sync workspace now")
        self._refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_button.setStyleSheet(
            "QToolButton {"
            "  background: transparent;"
            "  border: 1px solid #c5cee0;"
            "  border-radius: 8px;"
            "  padding: 0 6px;"
            "  font-weight: 700;"
            "}"
            "QToolButton:hover {"
            "  background-color: #eef2f7;"
            "}"
            "QToolButton:disabled {"
            "  color: #c5cee0;"
            "  border-color: #e6e9ef;"
            "}"
        )
        self._refresh_button.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(self._refresh_button)

    # ---- public API ------------------------------------------------------

    def stop(self) -> None:
        """Stop the relative-time ticker. Safe to call from
        ``QMainWindow.closeEvent``."""
        self._tick.stop()

    # ---- signal handlers -------------------------------------------------

    def _on_sync_started(self) -> None:
        self._is_syncing = True
        self._apply_state()

    def _on_sync_finished(self, result: SyncResult) -> None:
        self._is_syncing = False
        self._last_result = result
        self._apply_state()

    def _on_refresh_clicked(self) -> None:
        self.syncRequested.emit()
        self._manager.sync_now()

    # ---- rendering -------------------------------------------------------

    def _apply_state(self) -> None:
        if self._is_syncing:
            self._render(
                color=_GRAY,
                text="Syncing workspace...",
                tooltip="Pulling latest changes from origin/main",
                refresh_enabled=False,
            )
            return

        if self._manager.is_paused():
            reasons = ", ".join(self._manager.pause_reasons())
            self._render(
                color=_GRAY,
                text="Sync paused",
                tooltip=f"Background sync paused while: {reasons}",
                refresh_enabled=False,
            )
            return

        result = self._last_result
        if result is None:
            self._render(
                color=_GRAY,
                text="Workspace: awaiting first sync",
                tooltip="Background sync has not run yet.",
                refresh_enabled=True,
            )
            return

        if not result.success:
            self._render(
                color=_RED,
                text="Sync failed - click to retry",
                tooltip=result.message,
                refresh_enabled=True,
            )
            return

        rel = _format_relative_time(result.at)
        if result.updated:
            text = f"Workspace synced {rel}"
        else:
            text = f"Workspace up to date ({rel})"
        self._render(
            color=_GREEN,
            text=text,
            tooltip=result.message,
            refresh_enabled=True,
        )

    def _render(
        self,
        *,
        color: str,
        text: str,
        tooltip: str,
        refresh_enabled: bool,
    ) -> None:
        self._dot.setStyleSheet(
            f"color: {color}; font-size: 14px; background: transparent;"
        )
        self._text.setText(text)
        self._text.setToolTip(tooltip)
        self._refresh_button.setEnabled(refresh_enabled)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_relative_time(at: datetime) -> str:
    """Render ``at`` as a short relative-time label.

    Examples: ``"just now"``, ``"3m ago"``, ``"1h ago"``, ``"2d ago"``.
    """
    delta = datetime.now() - at
    seconds = int(delta.total_seconds())
    if seconds < 30:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


__all__ = [
    "RELATIVE_TIME_TICK_MS",
    "SyncIndicator",
]
