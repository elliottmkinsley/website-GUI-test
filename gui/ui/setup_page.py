"""First-run / re-configuration setup screen.

Asks the user for the GitHub OAuth Client ID and persists it via
``QSettings``. Also provides one-click access to the GitHub OAuth App
registration page and shows the exact values to enter on the GitHub
form, so the user never has to leave the GUI to get started.
"""

from __future__ import annotations

import logging
import webbrowser

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui import settings
from gui.config import (
    GITHUB_OAUTH_CLIENT_ID_ENV_VAR,
    GITHUB_REPO_FULL,
    resolve_github_client_id,
)

log = logging.getLogger(__name__)

GITHUB_OAUTH_NEW_APP_URL = "https://github.com/settings/applications/new"
GITHUB_OAUTH_APPS_URL = "https://github.com/settings/developers"


class SetupPage(QWidget):
    """One screen, two buttons: register / paste / save / continue.

    Emits ``setupComplete()`` when the user saves a valid-looking
    Client ID. The main window switches to the login page in
    response.
    """

    setupComplete = Signal()
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._allow_cancel = False
        self._build()

    # ---- layout -----------------------------------------------------------

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(64, 36, 64, 36)
        outer.setSpacing(14)

        title = QLabel("First-time setup")
        title.setObjectName("H1")
        outer.addWidget(title)

        subtitle = QLabel(
            "The Radiant Content GUI uses a GitHub OAuth App so you can "
            "sign in with your GitHub account. Paste the App's "
            "<b>Client ID</b> below and click <b>Save &amp; Continue</b>."
        )
        subtitle.setObjectName("Muted")
        subtitle.setTextFormat(Qt.TextFormat.RichText)
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        # ---- Step 1 card: register the OAuth App
        outer.addWidget(self._step_one_card())

        # ---- Step 2 card: paste the Client ID
        outer.addWidget(self._step_two_card())

        # ---- Status line
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        outer.addWidget(self._status_label)

        # ---- Buttons row
        button_row = QHBoxLayout()
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.clicked.connect(self.cancelled.emit)
        button_row.addWidget(self._cancel_button)
        button_row.addStretch(1)
        self._save_button = QPushButton("Save && Continue")
        self._save_button.setObjectName("Primary")
        self._save_button.setDefault(True)
        self._save_button.clicked.connect(self._save)
        button_row.addWidget(self._save_button)
        outer.addLayout(button_row)

        outer.addStretch(1)

    def _step_one_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        heading = QLabel("Step 1 \u2014 Create a GitHub OAuth App")
        heading.setObjectName("H2")
        layout.addWidget(heading)

        body = QLabel(
            "If your team already has one, skip to Step 2. Otherwise, click "
            "the button below and fill out the form with these values:"
        )
        body.setObjectName("Muted")
        body.setWordWrap(True)
        layout.addWidget(body)

        # The exact GitHub form values, presented as a borderless mini-table.
        values = QLabel(
            "<table cellspacing='2' cellpadding='2'>"
            "<tr><td><b>Application name</b></td>"
            "<td>Radiant Content GUI</td></tr>"
            "<tr><td><b>Homepage URL</b></td>"
            f"<td><code>https://github.com/{GITHUB_REPO_FULL}</code></td></tr>"
            "<tr><td><b>Authorization callback URL</b></td>"
            f"<td><code>https://github.com/{GITHUB_REPO_FULL}</code></td></tr>"
            "<tr><td><b>Enable Device Flow</b></td>"
            "<td>checked</td></tr>"
            "</table>"
        )
        values.setTextFormat(Qt.TextFormat.RichText)
        values.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(values)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        open_existing = QPushButton("Open my OAuth Apps")
        open_existing.clicked.connect(
            lambda: self._open_url(GITHUB_OAUTH_APPS_URL)
        )
        button_row.addWidget(open_existing)
        register = QPushButton("Register new OAuth App on GitHub")
        register.setObjectName("Primary")
        register.clicked.connect(
            lambda: self._open_url(GITHUB_OAUTH_NEW_APP_URL)
        )
        button_row.addWidget(register)
        layout.addLayout(button_row)

        return card

    def _step_two_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        heading = QLabel("Step 2 \u2014 Paste your Client ID")
        heading.setObjectName("H2")
        layout.addWidget(heading)

        body = QLabel(
            "On the OAuth App settings page, copy the <b>Client ID</b> "
            "(it looks like <code>Ov23li...</code> or <code>Iv1....</code>). "
            "You do <b>not</b> need a client secret \u2014 Device Flow does "
            "not use one."
        )
        body.setObjectName("Muted")
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setWordWrap(True)
        layout.addWidget(body)

        self._client_id_input = QLineEdit()
        self._client_id_input.setPlaceholderText("e.g. Ov23liLuhcFdIRBPGT4a")
        self._client_id_input.returnPressed.connect(self._save)
        layout.addWidget(self._client_id_input)

        helper = QLabel(
            "Your Client ID is saved in your user profile - it never "
            "leaves your computer except to authenticate you with GitHub. "
            "You can change it later from <b>File \u203a Settings</b>."
        )
        helper.setObjectName("Muted")
        helper.setWordWrap(True)
        helper.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(helper)

        return card

    # ---- behavior --------------------------------------------------------

    def open_for_first_run(self) -> None:
        """Initial appearance: no Cancel button (user must save to leave)."""
        self._allow_cancel = False
        self._cancel_button.setVisible(False)
        # Pre-fill with whatever is already stored so a re-open shows
        # the current value (env-var case included).
        self._client_id_input.setText(settings.get_github_client_id())
        self._set_status("", ok=None)
        self._client_id_input.setFocus()

    def open_for_reconfigure(self) -> None:
        """Re-opened from a menu: show Cancel so the user can back out."""
        self._allow_cancel = True
        self._cancel_button.setVisible(True)
        self._client_id_input.setText(settings.get_github_client_id())
        self._set_status("", ok=None)
        self._client_id_input.setFocus()

    def _set_status(self, text: str, *, ok: bool | None) -> None:
        self._status_label.setText(text)
        name = "StatusOk" if ok else ("StatusErr" if ok is False else "Muted")
        self._status_label.setObjectName(name)
        self.style().unpolish(self._status_label)
        self.style().polish(self._status_label)

    def _save(self) -> None:
        value = self._client_id_input.text().strip()
        if not value:
            self._set_status(
                "Please paste a GitHub Client ID before continuing.",
                ok=False,
            )
            return
        if value.startswith("Iv1.PLACEHOLDER") or value.startswith("REPLACE_ME"):
            self._set_status(
                "That looks like the placeholder value, not a real Client ID.",
                ok=False,
            )
            return
        try:
            settings.set_github_client_id(value)
        except Exception as exc:  # noqa: BLE001
            log.exception("Could not save Client ID")
            self._set_status(f"Could not save settings: {exc}", ok=False)
            return

        # Sanity check the resolution path - if an env var is set to a
        # different value, surface that loud and clear so the user
        # isn't confused when login uses the env override.
        active = resolve_github_client_id()
        if active != value:
            self._set_status(
                f"Saved, but the {GITHUB_OAUTH_CLIENT_ID_ENV_VAR} env var "
                f"is currently overriding your value with '{active}'. "
                "Unset that env var to use the value you just entered.",
                ok=False,
            )
            # Still emit complete - the user can sign in with the env value.
        else:
            self._set_status("Saved. Continuing to sign-in...", ok=True)
        self.setupComplete.emit()

    def _open_url(self, url: str) -> None:
        if not QDesktopServices.openUrl(QUrl(url)):
            try:
                webbrowser.open(url)
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not open browser to %s: %s", url, exc)
                self._set_status(
                    f"Could not open browser. Visit {url} manually.",
                    ok=False,
                )
