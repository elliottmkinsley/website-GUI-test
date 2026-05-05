"""Main window with a ``QStackedWidget`` shell.

Pages:
    0 - Login (GitHub Device Flow + access check)
    1 - Dashboard (4 domain tiles + Publish)
    2 - People
    3 - Projects
    4 - Events
    5 - Jobs
    6 - Publish

Pages are constructed lazily for the four domain pages and Publish so
the app shows the login screen instantly.
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
from gui.config import REPO_ROOT
from gui.ui.dashboard_page import DashboardPage
from gui.ui.events_page import EventsPage
from gui.ui.jobs_page import JobsPage
from gui.ui.login_page import LoginPage
from gui.ui.people_page import PeoplePage
from gui.ui.projects_page import ProjectsPage
from gui.ui.publish_page import PublishPage

log = logging.getLogger(__name__)

PAGE_LOGIN = 0
PAGE_DASHBOARD = 1
PAGE_PEOPLE = 2
PAGE_PROJECTS = 3
PAGE_EVENTS = 4
PAGE_JOBS = 5
PAGE_PUBLISH = 6


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

        self._login = LoginPage(self)
        self._login.signedIn.connect(self._on_signed_in)
        self._stack.addWidget(self._login)  # 0

        self._dashboard = DashboardPage(self)
        self._dashboard.openPeople.connect(lambda: self._stack.setCurrentIndex(PAGE_PEOPLE))
        self._dashboard.openProjects.connect(lambda: self._stack.setCurrentIndex(PAGE_PROJECTS))
        self._dashboard.openEvents.connect(lambda: self._stack.setCurrentIndex(PAGE_EVENTS))
        self._dashboard.openJobs.connect(lambda: self._stack.setCurrentIndex(PAGE_JOBS))
        self._dashboard.openPublish.connect(lambda: self._stack.setCurrentIndex(PAGE_PUBLISH))
        self._dashboard.signOutRequested.connect(self._sign_out)
        self._stack.addWidget(self._dashboard)  # 1

        self._people = PeoplePage(self)
        self._people.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._people)  # 2

        self._projects = ProjectsPage(self)
        self._projects.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._projects)  # 3

        self._events = EventsPage(self)
        self._events.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._events)  # 4

        self._jobs = JobsPage(self)
        self._jobs.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._jobs)  # 5

        self._publish = PublishPage(self)
        self._publish.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._publish)  # 6

        self._build_menu()

        self._stack.setCurrentIndex(PAGE_LOGIN)

        # Try a silent re-login using a previously-saved token.
        self._try_silent_login()

    # ---- menu / toolbar ----------------------------------------------------

    def _build_menu(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")

        self._sign_out_action = QAction("Sign &Out", self)
        self._sign_out_action.triggered.connect(self._sign_out)
        self._sign_out_action.setEnabled(False)
        file_menu.addAction(self._sign_out_action)

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
