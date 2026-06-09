"""Background workspace sync.

Periodically runs :func:`gui.repo.clone.pull_workspace` on a worker
thread so changes published by other GUI users (or anyone pushing to
``origin/main``) land in this user's workspace without requiring a
manual restart.

Design notes
------------
* The pull always goes through :func:`pull_workspace` which is
  fast-forward only. A dirty working tree (the user is mid-edit) or
  a non-ff remote (concurrent publish) becomes a soft skip - we log
  and emit a result, never raise.
* :meth:`SyncManager.pause` / :meth:`SyncManager.resume` are
  reference-counted. Callers pass a string ``reason`` so multiple
  guards (Publish in flight, dialog open, etc.) can stack safely.
  A paused timer is *also* stopped; resuming starts it again and
  optionally triggers an immediate sync.
* :meth:`SyncManager.sync_now` is the manual / one-shot trigger
  used by the status-bar indicator and the Help menu. It is also
  called after a successful publish to refresh local refs.
* The manager coalesces - if a sync is already in flight, additional
  triggers are ignored. The next scheduled tick still fires.
* :meth:`SyncManager.stop` is idempotent and safe to call from
  ``QMainWindow.closeEvent``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from gui.repo.clone import PullResult, is_valid_workspace, pull_workspace
from gui.workspace import get_workspace

log = logging.getLogger(__name__)

DEFAULT_INTERVAL_MS = 5 * 60 * 1000  # 5 minutes
"""Default background-sync cadence. ``MainWindow`` can override."""

TokenProvider = Callable[[], str | None]


@dataclass(frozen=True)
class SyncResult:
    """Outcome of one sync cycle, surfaced via :attr:`SyncManager.syncFinished`."""

    success: bool
    """``True`` if the pull ran cleanly (whether or not it actually
    advanced HEAD). ``False`` for soft skips and hard failures alike;
    the indicator widget decides how prominently to surface this."""

    updated: bool
    """``True`` if the workspace HEAD advanced as a result of this sync."""

    message: str
    """Human-readable status, suitable for tooltips and logs."""

    at: datetime
    """When the sync finished."""


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class _PullWorker(QObject):
    """One-shot worker that runs ``pull_workspace`` and emits the result."""

    done = Signal(object)  # SyncResult

    def __init__(
        self,
        *,
        workspace_root: Path,
        token: str | None,
    ) -> None:
        super().__init__()
        self._workspace_root = workspace_root
        self._token = token

    def run(self) -> None:
        try:
            result: PullResult = pull_workspace(
                self._workspace_root, token=self._token
            )
            sync_result = SyncResult(
                success=True,
                updated=result.updated,
                message=result.message,
                at=datetime.now(),
            )
        except Exception as exc:  # noqa: BLE001 - boundary
            log.exception("Background sync raised")
            sync_result = SyncResult(
                success=False,
                updated=False,
                message=f"Sync failed: {exc}",
                at=datetime.now(),
            )
        self.done.emit(sync_result)


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class SyncManager(QObject):
    """Owns the periodic sync timer and exposes pause / sync-now controls.

    Lifecycle:

        manager = SyncManager(parent)
        manager.start(token_provider=token_store.load_token)
        # ... later, around publish:
        manager.pause("publish")
        # ... after publish:
        manager.resume("publish")
        # ... on app close:
        manager.stop()
    """

    syncStarted = Signal()
    syncFinished = Signal(object)  # SyncResult
    pausedChanged = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self._on_tick)

        self._token_provider: TokenProvider | None = None
        self._interval_ms: int = DEFAULT_INTERVAL_MS
        self._running: bool = False  # ``start()`` was called and ``stop()`` was not.
        self._pause_reasons: list[str] = []

        self._worker_thread: QThread | None = None
        self._worker: _PullWorker | None = None
        self._last_result: SyncResult | None = None

    # ---- public API ------------------------------------------------------

    def start(
        self,
        *,
        token_provider: TokenProvider,
        interval_ms: int = DEFAULT_INTERVAL_MS,
        run_immediately: bool = False,
    ) -> None:
        """Begin periodic sync. Safe to call multiple times - calling
        ``start`` again updates the token provider / interval and
        resumes the timer if it was stopped."""
        self._token_provider = token_provider
        self._interval_ms = max(1_000, int(interval_ms))
        self._timer.setInterval(self._interval_ms)
        self._running = True
        if not self._is_paused():
            self._timer.start()
            if run_immediately:
                # Defer to the next event-loop tick so callers that
                # call start() from inside __init__ don't trigger a
                # sync before the rest of their setup completes.
                QTimer.singleShot(0, self.sync_now)

    def stop(self) -> None:
        """Stop the timer and release the worker thread (if any).

        Safe to call repeatedly and from ``closeEvent``.
        """
        self._running = False
        self._timer.stop()
        self._teardown_worker(wait_ms=2000)

    def pause(self, reason: str) -> None:
        """Reference-counted pause. Each ``pause(reason)`` must be
        matched with a ``resume(reason)`` to actually resume."""
        if not reason:
            raise ValueError("pause(reason) requires a non-empty reason")
        was_paused = self._is_paused()
        self._pause_reasons.append(reason)
        if not was_paused:
            self._timer.stop()
            self.pausedChanged.emit(True)
            log.debug("SyncManager paused (reason=%s)", reason)

    def resume(self, reason: str) -> None:
        """Drop one ``pause(reason)`` reference. The timer restarts
        when the last reason clears."""
        try:
            self._pause_reasons.remove(reason)
        except ValueError:
            log.warning(
                "SyncManager.resume(%r) called with no matching pause; "
                "ignoring.",
                reason,
            )
            return
        if not self._is_paused():
            if self._running:
                self._timer.start(self._interval_ms)
            self.pausedChanged.emit(False)
            log.debug("SyncManager resumed (last reason=%s)", reason)

    def sync_now(self) -> None:
        """Trigger an immediate sync (subject to coalescing).

        Safe to call from the UI thread; the actual pull runs on a
        worker thread.
        """
        if not self._running:
            log.debug("sync_now() ignored: manager not started")
            return
        if self._worker_thread is not None:
            log.debug("sync_now() coalesced: a sync is already in flight")
            return
        if not self._token_provider:
            log.debug("sync_now() ignored: no token provider configured")
            return

        try:
            workspace_root = get_workspace().root
        except Exception:  # noqa: BLE001
            log.exception("sync_now() could not resolve workspace")
            return
        if not is_valid_workspace(workspace_root):
            log.debug("sync_now() ignored: workspace at %s is not valid yet",
                      workspace_root)
            return

        token = self._token_provider()
        self._spawn_worker(workspace_root=workspace_root, token=token)

    def last_result(self) -> SyncResult | None:
        """Most recent result, or ``None`` if no sync has finished yet."""
        return self._last_result

    def is_paused(self) -> bool:
        return self._is_paused()

    def pause_reasons(self) -> tuple[str, ...]:
        return tuple(self._pause_reasons)

    # ---- internals -------------------------------------------------------

    def _is_paused(self) -> bool:
        return bool(self._pause_reasons)

    def _on_tick(self) -> None:
        if not self._running or self._is_paused():
            return
        self.sync_now()

    def _spawn_worker(
        self, *, workspace_root: Path, token: str | None
    ) -> None:
        thread = QThread(self)
        worker = _PullWorker(workspace_root=workspace_root, token=token)
        worker.moveToThread(thread)
        worker.done.connect(self._on_worker_done)
        thread.started.connect(worker.run)
        self._worker_thread = thread
        self._worker = worker
        self.syncStarted.emit()
        thread.start()

    def _on_worker_done(self, result: SyncResult) -> None:
        self._last_result = result
        thread = self._worker_thread
        worker = self._worker
        self._worker_thread = None
        self._worker = None

        if thread is not None:
            # Tell the worker thread's event loop to exit, then block
            # briefly on the UI thread until the worker's ``run()``
            # has fully returned. This is short (the slot is invoked
            # right after ``emit`` so ``run`` is at most one frame
            # away from finishing) and keeps us free of use-after-
            # free during teardown.
            thread.quit()
            if not thread.wait(2000):
                log.warning("Worker thread did not exit within 2s")

        if worker is not None:
            worker.deleteLater()
        if thread is not None:
            thread.deleteLater()

        log.debug(
            "Sync finished: success=%s updated=%s message=%s",
            result.success, result.updated, result.message,
        )
        self.syncFinished.emit(result)

    def _teardown_worker(self, *, wait_ms: int) -> None:
        thread = self._worker_thread
        worker = self._worker
        self._worker_thread = None
        self._worker = None
        if thread is None:
            return
        try:
            thread.quit()
            thread.wait(wait_ms)
            if worker is not None:
                worker.deleteLater()
            thread.deleteLater()
        except RuntimeError:
            # Already deleted - safe to ignore.
            pass


__all__ = [
    "DEFAULT_INTERVAL_MS",
    "SyncManager",
    "SyncResult",
    "TokenProvider",
]
