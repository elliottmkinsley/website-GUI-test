"""Main window with a ``QStackedWidget`` shell.

Pages:
    0 - Setup (first-run / re-configure GitHub OAuth Client ID)
    1 - Login (GitHub Device Flow + access check)
    2 - Dashboard (4 domain tiles + Publish)
    3 - People
    4 - Projects
    5 - Events
    6 - Jobs
    7 - Publish

On first launch (or any launch where no Client ID is resolved), the
window shows the Setup page. Once the user saves a Client ID, the
window advances to Login. Subsequent launches skip Setup automatically
and may even skip Login entirely if a previous token is still valid.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from gui.auth import token_store
from gui.auth.access_check import AccessResult, check_repo_push_access
from gui.config import REPO_ROOT, is_github_client_id_configured
from gui.ui.dashboard_page import DashboardPage
from gui.ui.events_page import EventsPage
from gui.ui.jobs_page import JobsPage
from gui.ui.login_page import LoginPage
from gui.ui.people_page import PeoplePage
from gui.ui.projects_page import ProjectsPage
from gui.ui.publish_page import PublishPage
from gui.ui.setup_page import SetupPage

log = logging.getLogger(__name__)

PAGE_SETUP = 0
PAGE_LOGIN = 1
PAGE_DASHBOARD = 2
PAGE_PEOPLE = 3
PAGE_PROJECTS = 4
PAGE_EVENTS = 5
PAGE_JOBS = 6
PAGE_PUBLISH = 7


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Radiant Content GUI")
        self.resize(1180, 780)

        self._stack = QStackedWidget(self)
        self.setCentralWidget(self._stack)

        self._status = QStatusBar(self)
        self.setStatusBar(self._status)
        self._status.showMessage("Not signed in.")

        self._access: AccessResult | None = None

        self._setup = SetupPage(self)
        self._setup.setupComplete.connect(self._on_setup_complete)
        self._setup.cancelled.connect(self._on_setup_cancelled)
        self._stack.addWidget(self._setup)  # 0

        self._login = LoginPage(self)
        self._login.signedIn.connect(self._on_signed_in)
        self._stack.addWidget(self._login)  # 1

        self._dashboard = DashboardPage(self)
        self._dashboard.openPeople.connect(lambda: self._stack.setCurrentIndex(PAGE_PEOPLE))
        self._dashboard.openProjects.connect(lambda: self._stack.setCurrentIndex(PAGE_PROJECTS))
        self._dashboard.openEvents.connect(lambda: self._stack.setCurrentIndex(PAGE_EVENTS))
        self._dashboard.openJobs.connect(lambda: self._stack.setCurrentIndex(PAGE_JOBS))
        self._dashboard.openPublish.connect(lambda: self._stack.setCurrentIndex(PAGE_PUBLISH))
        self._dashboard.signOutRequested.connect(self._sign_out)
        self._stack.addWidget(self._dashboard)  # 2

        self._people = PeoplePage(self)
        self._people.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._people)  # 3

        self._projects = ProjectsPage(self)
        self._projects.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._projects)  # 4

        self._events = EventsPage(self)
        self._events.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._events)  # 5

        self._jobs = JobsPage(self)
        self._jobs.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._jobs)  # 6

        self._publish = PublishPage(self)
        self._publish.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._publish)  # 7

        self._build_menu()

        # Pick the right entry point.
        if is_github_client_id_configured():
            self._stack.setCurrentIndex(PAGE_LOGIN)
            # Try a silent re-login using a previously-saved token.
            self._try_silent_login()
        else:
            self._setup.open_for_first_run()
            self._stack.setCurrentIndex(PAGE_SETUP)
            self._status.showMessage("First-time setup required.")

    # ---- menu / toolbar ----------------------------------------------------

    def _build_menu(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")

        self._sign_out_action = QAction("Sign &Out", self)
        self._sign_out_action.triggered.connect(self._sign_out)
        self._sign_out_action.setEnabled(False)
        file_menu.addAction(self._sign_out_action)

        file_menu.addSeparator()
        settings_action = QAction("GitHub OAuth Client &ID...", self)
        settings_action.triggered.connect(self._open_setup)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = bar.addMenu("&Help")
        about = QAction("&About", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Radiant Content GUI",
            (
                "<b>Radiant Content GUI</b><br>"
                "Edit People, Projects, Events, and Jobs for the "
                "Radiant Center for Remote Sensing website, then "
                "publish to the NAU server and a GitHub archive branch."
                f"<br><br>Repo root: <code>{REPO_ROOT}</code>"
            ),
        )

    # ---- silent re-login ---------------------------------------------------

    def _try_silent_login(self) -> None:
        token = token_store.load_token()
        if not token:
            return
        try:
            access = check_repo_push_access(token)
        except Exception as exc:  # noqa: BLE001 - intentional broad catch
            log.warning("Silent re-login failed: %s", exc)
            return
        if access.allowed:
            self._on_signed_in(token, access)
        else:
            # Stale or revoked token. Clear it; user must log in again.
            token_store.clear_token()

    # ---- signed-in handoff -------------------------------------------------

    def _on_signed_in(self, token: str, access: AccessResult) -> None:
        token_store.save_token(token)
        self._access = access
        self._status.showMessage(access.message)
        self._sign_out_action.setEnabled(True)
        self._dashboard.set_user(access.username or "")
        self._dashboard.refresh_summary()
        self._stack.setCurrentIndex(PAGE_DASHBOARD)
        # Eagerly load the domain pages on first sign-in so the user
        # never sees an empty list.
        self._people.refresh()
        self._projects.refresh()
        self._events.refresh()
        self._jobs.refresh()

    def _goto_dashboard(self) -> None:
        # Re-load summary in case domain pages changed something.
        self._dashboard.refresh_summary()
        self._stack.setCurrentIndex(PAGE_DASHBOARD)

    def _sign_out(self) -> None:
        token_store.clear_token()
        self._access = None
        self._status.showMessage("Signed out.")
        self._sign_out_action.setEnabled(False)
        self._login.reset()
        self._stack.setCurrentIndex(PAGE_LOGIN)

    # ---- setup-page handlers ----------------------------------------------

    def _open_setup(self) -> None:
        """Re-enter the Setup screen from the menu."""
        self._setup.open_for_reconfigure()
        self._stack.setCurrentIndex(PAGE_SETUP)

    def _on_setup_complete(self) -> None:
        # If the user was previously signed in, we keep their token
        # but the Client ID change means we should re-verify access.
        token = token_store.load_token()
        self._login.reset()
        self._stack.setCurrentIndex(PAGE_LOGIN)
        if token:
            self._try_silent_login()
        self._status.showMessage("GitHub OAuth Client ID saved.")

    def _on_setup_cancelled(self) -> None:
        """Only fired when Setup is opened via the menu after initial setup."""
        if not is_github_client_id_configured():
            # User hit Cancel during a re-config attempt while no
            # value was set - that should not normally happen because
            # open_for_first_run() hides the Cancel button, but be
            # defensive: stay on Setup until they save.
            return
        # If signed in, go back to dashboard; else back to login.
        token = token_store.load_token()
        if token and self._access and self._access.allowed:
            self._stack.setCurrentIndex(PAGE_DASHBOARD)
        else:
            self._stack.setCurrentIndex(PAGE_LOGIN)
