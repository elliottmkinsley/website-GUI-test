"""First-launch workspace bootstrap UI.

Wedged into the navigation stack between Login and Dashboard:

* If the configured workspace already looks like a valid Radiant
  checkout, this page is shown briefly while a background ``git pull``
  brings it up to date.
* If the workspace folder is empty or missing, this page runs
  ``git clone`` instead, with progress text and a retry button.

The actual git work happens on a ``QThread`` worker (see
:mod:`gui.repo.clone`) so the UI never blocks.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.config import GITHUB_REPO_FULL
from gui.repo.clone import (
    clone_workspace,
    is_valid_workspace,
    pull_workspace,
)
from gui.workspace import default_workspace_root, set_workspace

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class _Worker(QObject):
    """Runs clone-or-pull on a background thread."""

    progress = Signal(str)
    success = Signal(str, bool)  # workspace_path, fresh_clone
    failure = Signal(str)

    def __init__(self, target: Path, token: str | None) -> None:
        super().__init__()
        self._target = target
        self._token = token

    def run(self) -> None:
        try:
            if is_valid_workspace(self._target):
                self.progress.emit(
                    f"Workspace found at {self._target}; syncing with origin ..."
                )
                pull = pull_workspace(
                    self._target,
                    token=self._token,
                    progress=self.progress.emit,
                )
                self.progress.emit(pull.message)
                self.success.emit(str(self._target), False)
                return

            self.progress.emit(
                f"No workspace at {self._target}; preparing to clone ..."
            )
            result = clone_workspace(
                self._target,
                token=self._token,
                progress=self.progress.emit,
            )
            self.success.emit(str(result.workspace.root), result.fresh)
        except Exception as exc:  # noqa: BLE001 - surfaced in UI
            log.exception("Workspace bootstrap failed")
            self.failure.emit(str(exc))


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


class WorkspacePage(QWidget):
    """Shown once after sign-in until the workspace is ready."""

    workspaceReady = Signal(Path)  # absolute workspace root
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._token: str | None = None
        self._target: Path = default_workspace_root()
        self._thread: QThread | None = None
        self._worker: _Worker | None = None
        self._build()
        self._reset_ui()

    # ---- build --------------------------------------------------------

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 32, 48, 32)
        outer.setSpacing(16)

        title = QLabel("Setting up your local workspace")
        title.setObjectName("H1")
        outer.addWidget(title)

        self._intro = QLabel()
        self._intro.setObjectName("Muted")
        self._intro.setWordWrap(True)
        self._intro.setTextFormat(Qt.TextFormat.RichText)
        outer.addWidget(self._intro)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        outer.addWidget(self._progress)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText(
            "Progress messages from git will appear here."
        )
        outer.addWidget(self._log, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self._cancel_button = QPushButton("Sign out")
        self._cancel_button.clicked.connect(self.cancelled.emit)
        button_row.addWidget(self._cancel_button)
        self._retry_button = QPushButton("Retry")
        self._retry_button.setObjectName("Primary")
        self._retry_button.clicked.connect(self._kick_worker)
        self._retry_button.setVisible(False)
        button_row.addWidget(self._retry_button)
        outer.addLayout(button_row)

    def _reset_ui(self) -> None:
        self._intro.setText(
            f"The GUI needs a local clone of "
            f"<b>{GITHUB_REPO_FULL}</b> on this machine to edit content. "
            f"It will be stored at:<br><code>{self._target}</code>"
        )
        self._log.clear()
        self._progress.setRange(0, 0)
        self._progress.setVisible(True)
        self._retry_button.setVisible(False)

    # ---- public API ---------------------------------------------------

    def start(self, *, token: str | None) -> None:
        """Begin the bootstrap. Called by ``MainWindow`` after sign-in.

        ``token`` is the OAuth token used to authenticate against
        GitHub for the clone / pull. ``None`` is acceptable for
        public repos but the configured target is private, so a
        token will normally be present.
        """
        self._token = token
        self._target = default_workspace_root()
        self._reset_ui()
        self._kick_worker()

    # ---- internals ----------------------------------------------------

    def _kick_worker(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return  # already in progress
        self._retry_button.setVisible(False)
        self._progress.setRange(0, 0)
        self._progress.setVisible(True)

        self._thread = QThread(self)
        self._worker = _Worker(target=self._target, token=self._token)
        self._worker.moveToThread(self._thread)
        self._worker.progress.connect(self._append_log)
        self._worker.success.connect(self._on_success)
        self._worker.failure.connect(self._on_failure)
        self._thread.started.connect(self._worker.run)
        self._thread.start()

    def _append_log(self, line: str) -> None:
        self._log.appendPlainText(line)

    def _on_success(self, path_str: str, fresh: bool) -> None:
        path = Path(path_str)
        set_workspace(path)
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        if fresh:
            self._append_log("Workspace ready. Continuing to dashboard ...")
        else:
            self._append_log("Workspace verified. Continuing to dashboard ...")
        self._cleanup_thread()
        self.workspaceReady.emit(path)

    def _on_failure(self, message: str) -> None:
        self._append_log(f"ERROR: {message}")
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._retry_button.setVisible(True)
        self._cleanup_thread()

    def _cleanup_thread(self) -> None:
        if self._thread is None:
            return
        self._thread.quit()
        self._thread.wait(2000)
        self._thread = None
        self._worker = None
