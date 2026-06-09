"""Publish page: SMB copy, then GitHub push to main, then snapshot to archive.

All three phases run on a worker thread so the UI stays responsive
while shutil and git do their thing. ``publishStarted`` /
``publishFinished`` signals let :class:`gui.ui.main_window.MainWindow`
pause the background :mod:`gui.services.sync_manager` while a publish
is in flight (so a periodic pull cannot race the push).
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.auth import token_store
from gui.auth.access_check import check_repo_push_access
from gui.config import GITHUB_REPO_FULL, nau_smb_default_path, nau_smb_instructions
from gui.deploy import git_publisher, smb_publisher
from gui.deploy.git_publisher import GitPublishError

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class _PublishWorker(QObject):
    progress = Signal(str)
    smbDone = Signal(str)  # target path
    smbFailed = Signal(str)
    mainDone = Signal(str)  # short SHA on origin/main
    mainFailed = Signal(str)
    archiveDone = Signal(str)  # short SHA on origin/archive
    archiveSkipped = Signal(str)  # warning text - non-fatal
    finished = Signal()

    def __init__(self, *, token: str, github_username: str | None) -> None:
        super().__init__()
        self._token = token
        self._username = github_username

    def run_publish(self) -> None:
        # ---- Step 1: SMB copy ------------------------------------------
        try:
            target = smb_publisher.publish(progress=self.progress.emit)
            self.smbDone.emit(str(target))
        except Exception as exc:  # noqa: BLE001
            log.exception("SMB publish failed")
            self.smbFailed.emit(str(exc))
            self.finished.emit()
            return

        # ---- Step 2: push main -----------------------------------------
        try:
            main_sha = git_publisher.publish_to_main(
                github_username=self._username,
                token=self._token,
                progress=self.progress.emit,
            )
            self.mainDone.emit(main_sha)
        except GitPublishError as exc:
            log.exception("Push to main failed")
            self.mainFailed.emit(str(exc))
            self.finished.emit()
            return
        except Exception as exc:  # noqa: BLE001
            log.exception("Push to main failed unexpectedly")
            self.mainFailed.emit(str(exc))
            self.finished.emit()
            return

        # ---- Step 3: archive snapshot (best-effort) ---------------------
        try:
            archive_sha = git_publisher.publish_to_archive(
                github_username=self._username,
                token=self._token,
                progress=self.progress.emit,
            )
            self.archiveDone.emit(archive_sha)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "Archive snapshot push failed (non-fatal): %s", exc
            )
            self.archiveSkipped.emit(
                f"Main is up to date; archive snapshot can be retried "
                f"next publish ({exc})."
            )

        self.finished.emit()


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


class PublishPage(QWidget):
    backRequested = Signal()
    publishStarted = Signal()
    publishFinished = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: _PublishWorker | None = None
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 24, 36, 24)
        outer.setSpacing(16)

        header = QHBoxLayout()
        back = QPushButton("\u2190 Back")
        back.clicked.connect(self.backRequested.emit)
        header.addWidget(back)
        title = QLabel("Publish to website")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)
        outer.addLayout(header)

        intro = QLabel(
            "<b>Step 1.</b> Copy the website tree to the NAU file share at "
            f"<code>{nau_smb_default_path()}</code>.<br>"
            f"<b>Step 2.</b> Commit and push the same content to "
            f"<code>main</code> on <b>{GITHUB_REPO_FULL}</b> so other "
            "GUI users see your changes on their next sync.<br>"
            f"<b>Step 3.</b> Snapshot the same content to <code>archive</code> "
            "as a history record.<br><br>"
            "If Step 1 fails, you'll get OS-specific instructions for "
            "mounting the share - then click <b>Publish</b> again."
        )
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.TextFormat.RichText)
        outer.addWidget(intro)

        # Per-step status indicators.
        self._smb_status = QLabel(
            "Step 1 \u2014 Copy to NAU share: not started."
        )
        self._smb_status.setObjectName("Muted")
        self._smb_status.setWordWrap(True)
        outer.addWidget(self._smb_status)

        self._main_status = QLabel(
            "Step 2 \u2014 Push to main (content sync): not started."
        )
        self._main_status.setObjectName("Muted")
        self._main_status.setWordWrap(True)
        outer.addWidget(self._main_status)

        self._archive_status = QLabel(
            "Step 3 \u2014 Snapshot to archive (history): not started."
        )
        self._archive_status.setObjectName("Muted")
        self._archive_status.setWordWrap(True)
        outer.addWidget(self._archive_status)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Progress messages will appear here.")
        outer.addWidget(self._log, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self._publish_button = QPushButton("Publish")
        self._publish_button.setObjectName("Primary")
        self._publish_button.clicked.connect(self._start)
        button_row.addWidget(self._publish_button)
        outer.addLayout(button_row)

    # ----------------------------------------------------------- helpers

    def _set_status(
        self, label: QLabel, text: str, ok: bool | None = None
    ) -> None:
        label.setText(text)
        name = "StatusOk" if ok else ("StatusErr" if ok is False else "Muted")
        label.setObjectName(name)
        self.style().unpolish(label)
        self.style().polish(label)

    def _append_log(self, line: str) -> None:
        self._log.appendPlainText(line)

    # -------------------------------------------------------------- run

    def _start(self) -> None:
        token = token_store.load_token()
        if not token:
            QMessageBox.warning(
                self,
                "Not signed in",
                "Your GitHub token is not available. Sign out and back in, "
                "then try again.",
            )
            return
        try:
            access = check_repo_push_access(token)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Access check failed", str(exc))
            return
        if not access.allowed:
            QMessageBox.critical(self, "Access denied", access.message)
            return

        self._set_status(
            self._smb_status,
            "Step 1 \u2014 Copy to NAU share: in progress...",
            None,
        )
        self._set_status(
            self._main_status,
            "Step 2 \u2014 Push to main (content sync): waiting...",
            None,
        )
        self._set_status(
            self._archive_status,
            "Step 3 \u2014 Snapshot to archive (history): waiting...",
            None,
        )
        self._log.clear()
        self._publish_button.setEnabled(False)
        self.publishStarted.emit()

        self._thread = QThread(self)
        self._worker = _PublishWorker(
            token=token, github_username=access.username
        )
        self._worker.moveToThread(self._thread)
        self._worker.progress.connect(self._append_log)
        self._worker.smbDone.connect(self._on_smb_done)
        self._worker.smbFailed.connect(self._on_smb_failed)
        self._worker.mainDone.connect(self._on_main_done)
        self._worker.mainFailed.connect(self._on_main_failed)
        self._worker.archiveDone.connect(self._on_archive_done)
        self._worker.archiveSkipped.connect(self._on_archive_skipped)
        self._worker.finished.connect(self._on_worker_finished)
        self._thread.started.connect(self._worker.run_publish)
        self._thread.start()

    # ----------------------------------------------------------- handlers

    def _on_smb_done(self, target: str) -> None:
        self._set_status(
            self._smb_status,
            f"Step 1 \u2014 Copied to {target}.",
            ok=True,
        )
        self._set_status(
            self._main_status,
            "Step 2 \u2014 Push to main (content sync): in progress...",
            None,
        )

    def _on_smb_failed(self, message: str) -> None:
        self._set_status(
            self._smb_status, f"Step 1 failed: {message}", ok=False
        )
        QMessageBox.warning(
            self,
            "Could not reach the NAU share",
            f"{message}\n\n{nau_smb_instructions()}",
        )

    def _on_main_done(self, sha: str) -> None:
        self._set_status(
            self._main_status,
            f"Step 2 \u2014 Pushed commit {sha} to origin/main.",
            ok=True,
        )
        self._set_status(
            self._archive_status,
            "Step 3 \u2014 Snapshot to archive (history): in progress...",
            None,
        )

    def _on_main_failed(self, message: str) -> None:
        self._set_status(
            self._main_status,
            f"Step 2 failed: {message}",
            ok=False,
        )

    def _on_archive_done(self, sha: str) -> None:
        self._set_status(
            self._archive_status,
            f"Step 3 \u2014 Pushed snapshot {sha} to origin/archive.",
            ok=True,
        )

    def _on_archive_skipped(self, warning: str) -> None:
        # Non-fatal: main already updated. Render in the warning-ish
        # "not started" style (Muted) with a clear note, not the
        # red error style.
        self._set_status(
            self._archive_status,
            f"Step 3 \u2014 Skipped: {warning}",
            ok=None,
        )

    def _on_worker_finished(self) -> None:
        if self._thread:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
        self._worker = None
        self._publish_button.setEnabled(True)
        self.publishFinished.emit()
