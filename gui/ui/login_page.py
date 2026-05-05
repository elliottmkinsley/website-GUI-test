"""Login screen: GitHub OAuth Device Flow + access verification."""

from __future__ import annotations

import logging
import webbrowser

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QClipboard, QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.auth.access_check import AccessResult, check_repo_push_access
from gui.auth.device_flow import DeviceCode, DeviceFlowWorker
from gui.config import GITHUB_REPO_FULL

log = logging.getLogger(__name__)


class LoginPage(QWidget):
    """Two-state screen.

    State 1 (initial / try again): Big "Sign in with GitHub" button.
    State 2 (in progress): User code shown + Open GitHub button + status.
    Emits ``signedIn(token, AccessResult)`` on success.
    """

    signedIn = Signal(str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker: DeviceFlowWorker | None = None
        self._verification_uri = "https://github.com/login/device"
        self._build()
        self.reset()

    # ---- layout -----------------------------------------------------------

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(64, 48, 64, 48)
        layout.setSpacing(20)
        layout.addStretch(1)

        title = QLabel("Radiant Content GUI")
        title.setObjectName("H1")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(
            "Sign in with GitHub to manage People, Projects, Events, and Jobs."
        )
        subtitle.setObjectName("Muted")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        self._gating_repo = QLabel(
            f"You must have push access to <b>{GITHUB_REPO_FULL}</b>."
        )
        self._gating_repo.setObjectName("Muted")
        self._gating_repo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gating_repo.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._gating_repo)

        layout.addSpacing(16)

        # Big sign-in button (initial state)
        self._sign_in_button = QPushButton("Sign in with GitHub")
        self._sign_in_button.setObjectName("Primary")
        self._sign_in_button.setFixedHeight(44)
        self._sign_in_button.clicked.connect(self._begin_flow)
        layout.addWidget(self._sign_in_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Code panel (visible during flow)
        self._code_label = QLabel("")
        self._code_label.setObjectName("DeviceCode")
        self._code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._code_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self._code_label, alignment=Qt.AlignmentFlag.AlignCenter)

        helper = QLabel("Enter the code above on GitHub:")
        helper.setObjectName("Muted")
        helper.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(helper)
        self._helper_label = helper

        button_row = QHBoxLayout()
        button_row.setSpacing(12)
        button_row.addStretch(1)
        self._open_button = QPushButton("Open GitHub")
        self._open_button.setObjectName("Primary")
        self._open_button.clicked.connect(self._open_browser)
        button_row.addWidget(self._open_button)
        self._copy_button = QPushButton("Copy code")
        self._copy_button.clicked.connect(self._copy_code)
        button_row.addWidget(self._copy_button)
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setObjectName("Danger")
        self._cancel_button.clicked.connect(self._cancel_flow)
        button_row.addWidget(self._cancel_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch(2)

    # ---- state machine ----------------------------------------------------

    def reset(self) -> None:
        """Return to the initial 'Sign in' state."""
        self._stop_worker()
        self._sign_in_button.setVisible(True)
        self._sign_in_button.setEnabled(True)
        self._code_label.setVisible(False)
        self._code_label.setText("")
        self._helper_label.setVisible(False)
        self._open_button.setVisible(False)
        self._copy_button.setVisible(False)
        self._cancel_button.setVisible(False)
        self._status_label.setObjectName("")
        self._status_label.setText("")
        self.style().unpolish(self._status_label)
        self.style().polish(self._status_label)

    def _show_in_progress(self, code: DeviceCode) -> None:
        self._verification_uri = code.verification_uri
        self._sign_in_button.setVisible(False)
        self._code_label.setText(code.user_code)
        self._code_label.setVisible(True)
        self._helper_label.setVisible(True)
        self._open_button.setVisible(True)
        self._copy_button.setVisible(True)
        self._cancel_button.setVisible(True)
        self._set_status("Waiting for you to authorize the app on GitHub...", ok=None)

    def _set_status(self, text: str, *, ok: bool | None) -> None:
        self._status_label.setText(text)
        name = "StatusOk" if ok else ("StatusErr" if ok is False else "Muted")
        self._status_label.setObjectName(name)
        self.style().unpolish(self._status_label)
        self.style().polish(self._status_label)

    # ---- worker plumbing --------------------------------------------------

    def _begin_flow(self) -> None:
        self._stop_worker()
        self._sign_in_button.setEnabled(False)
        self._set_status("Requesting a login code from GitHub...", ok=None)
        self._worker = DeviceFlowWorker(self)
        self._worker.codeIssued.connect(self._show_in_progress)
        self._worker.succeeded.connect(self._on_token)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _stop_worker(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            try:
                worker.cancel()
                worker.wait(2000)
            except RuntimeError:
                pass

    def _cancel_flow(self) -> None:
        self._stop_worker()
        self.reset()
        self._set_status("Login cancelled.", ok=False)

    # ---- handlers ---------------------------------------------------------

    def _open_browser(self) -> None:
        try:
            webbrowser.open(self._verification_uri)
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not open browser: %s", exc)
            self._set_status(
                f"Could not open browser. Visit {self._verification_uri} manually.",
                ok=False,
            )

    def _copy_code(self) -> None:
        clipboard: QClipboard = QGuiApplication.clipboard()
        clipboard.setText(self._code_label.text())
        self._set_status("Code copied to clipboard.", ok=True)

    def _on_token(self, token: str) -> None:
        self._set_status("Verifying repository access...", ok=None)
        try:
            access = check_repo_push_access(token)
        except Exception as exc:  # noqa: BLE001
            log.exception("Access check raised")
            self._set_status(f"Access check failed: {exc}", ok=False)
            self._sign_in_button.setText("Try Again")
            self._sign_in_button.setEnabled(True)
            self._sign_in_button.setVisible(True)
            self._code_label.setVisible(False)
            self._helper_label.setVisible(False)
            self._open_button.setVisible(False)
            self._copy_button.setVisible(False)
            self._cancel_button.setVisible(False)
            return

        if not access.allowed:
            self._set_status(access.message, ok=False)
            self._sign_in_button.setText("Try Again")
            self._sign_in_button.setEnabled(True)
            self._sign_in_button.setVisible(True)
            self._code_label.setVisible(False)
            self._helper_label.setVisible(False)
            self._open_button.setVisible(False)
            self._copy_button.setVisible(False)
            self._cancel_button.setVisible(False)
            return

        self._set_status(access.message, ok=True)
        self.signedIn.emit(token, access)

    def _on_failed(self, message: str) -> None:
        self._set_status(message, ok=False)
        self._sign_in_button.setText("Try Again")
        self._sign_in_button.setEnabled(True)
        self._sign_in_button.setVisible(True)
        self._code_label.setVisible(False)
        self._helper_label.setVisible(False)
        self._open_button.setVisible(False)
        self._copy_button.setVisible(False)
        self._cancel_button.setVisible(False)
