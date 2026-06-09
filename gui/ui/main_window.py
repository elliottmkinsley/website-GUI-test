"""Main window with a ``QStackedWidget`` shell.

Pages:
    0 - Setup (first-run / re-configure GitHub OAuth Client ID)
    1 - Login (GitHub Device Flow + access check)
    2 - Workspace (first-launch clone / on-launch pull)
    3 - Dashboard (4 domain tiles + Publish)
    4 - People
    5 - Projects
    6 - Events
    7 - Jobs
    8 - Publish

On first launch (or any launch where no Client ID is resolved), the
window shows the Setup page. Once the user saves a Client ID, the
window advances to Login. After sign-in, the Workspace page makes
sure the website checkout exists and is current before handing off to
the Dashboard. Subsequent launches skip Setup automatically and may
even skip Login entirely if a previous token is still valid.
"""

from __future__ import annotations

import logging
import webbrowser

from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
)

from gui.auth import token_store
from gui.auth.access_check import AccessResult, check_repo_push_access
from gui.config import GITHUB_REPO_FULL, is_github_client_id_configured
from gui.repo.clone import is_valid_workspace
from gui.services.sync_manager import SyncManager
from gui.ui.dashboard_page import DashboardPage
from gui.ui.events_page import EventsPage
from gui.ui.jobs_page import JobsPage
from gui.ui.login_page import LoginPage
from gui.ui.people_page import PeoplePage
from gui.ui.projects_page import ProjectsPage
from gui.ui.publish_page import PublishPage
from gui.ui.setup_page import SetupPage
from gui.ui.widgets.nau_status_indicator import NauStatusIndicator
from gui.ui.widgets.sync_indicator import SyncIndicator
from gui.ui.workspace_page import WorkspacePage
from gui.workspace import default_workspace_root, get_workspace, set_workspace

try:
    from gui.__version__ import __version__ as APP_VERSION
except Exception:  # noqa: BLE001 - version module may be missing in dev
    APP_VERSION = "0.0.0"

log = logging.getLogger(__name__)

RELEASES_URL = f"https://github.com/{GITHUB_REPO_FULL}/releases/latest"

PAGE_SETUP = 0
PAGE_LOGIN = 1
PAGE_WORKSPACE = 2
PAGE_DASHBOARD = 3
PAGE_PEOPLE = 4
PAGE_PROJECTS = 5
PAGE_EVENTS = 6
PAGE_JOBS = 7
PAGE_PUBLISH = 8


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

        # Bottom-right corner: workspace sync indicator + live NAU
        # share reachability indicator. ``addPermanentWidget`` anchors
        # them to the right side of the status bar (transient
        # ``showMessage`` text stays on the left). The sync indicator
        # is added first so it appears to the LEFT of the NAU one.
        self._sync_manager = SyncManager(self)
        self._sync_indicator = SyncIndicator(self._sync_manager, self)
        self._status.addPermanentWidget(self._sync_indicator)

        self._nau_indicator = NauStatusIndicator(self)
        self._status.addPermanentWidget(self._nau_indicator)
        self._nau_indicator.start()

        self._access: AccessResult | None = None

        self._setup = SetupPage(self)
        self._setup.setupComplete.connect(self._on_setup_complete)
        self._setup.cancelled.connect(self._on_setup_cancelled)
        self._stack.addWidget(self._setup)  # 0

        self._login = LoginPage(self)
        self._login.signedIn.connect(self._on_signed_in)
        self._stack.addWidget(self._login)  # 1

        self._workspace = WorkspacePage(self)
        self._workspace.workspaceReady.connect(self._on_workspace_ready)
        self._workspace.cancelled.connect(self._sign_out)
        self._stack.addWidget(self._workspace)  # 2

        self._dashboard = DashboardPage(self)
        self._dashboard.openPeople.connect(lambda: self._stack.setCurrentIndex(PAGE_PEOPLE))
        self._dashboard.openProjects.connect(lambda: self._stack.setCurrentIndex(PAGE_PROJECTS))
        self._dashboard.openEvents.connect(lambda: self._stack.setCurrentIndex(PAGE_EVENTS))
        self._dashboard.openJobs.connect(lambda: self._stack.setCurrentIndex(PAGE_JOBS))
        self._dashboard.openPublish.connect(lambda: self._stack.setCurrentIndex(PAGE_PUBLISH))
        self._dashboard.signOutRequested.connect(self._sign_out)
        self._stack.addWidget(self._dashboard)  # 3

        self._people = PeoplePage(self)
        self._people.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._people)  # 4

        self._projects = ProjectsPage(self)
        self._projects.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._projects)  # 5

        self._events = EventsPage(self)
        self._events.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._events)  # 6

        self._jobs = JobsPage(self)
        self._jobs.backRequested.connect(self._goto_dashboard)
        self._stack.addWidget(self._jobs)  # 7

        self._publish = PublishPage(self)
        self._publish.backRequested.connect(self._goto_dashboard)
        self._publish.publishStarted.connect(self._on_publish_started)
        self._publish.publishFinished.connect(self._on_publish_finished)
        self._stack.addWidget(self._publish)  # 8

        # When the background sync actually pulls new commits, refresh
        # the dashboard and domain pages so the user sees the change
        # without having to navigate away and back.
        self._sync_manager.syncFinished.connect(self._on_background_sync_finished)

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
        self._sync_now_action = QAction("Sync workspace &now", self)
        self._sync_now_action.setShortcut("F5")
        self._sync_now_action.triggered.connect(self._sync_manager.sync_now)
        self._sync_now_action.setEnabled(False)
        help_menu.addAction(self._sync_now_action)
        help_menu.addSeparator()
        check_updates = QAction("Check for &updates...", self)
        check_updates.triggered.connect(self._open_releases_page)
        help_menu.addAction(check_updates)
        help_menu.addSeparator()
        about = QAction("&About", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)

    def _open_releases_page(self) -> None:
        if not QDesktopServices.openUrl(QUrl(RELEASES_URL)):
            # Fall back to stdlib webbrowser if Qt cannot launch a
            # browser (rare; usually only happens in headless envs).
            webbrowser.open(RELEASES_URL)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Radiant Content GUI",
            (
                f"<b>Radiant Content GUI</b> v{APP_VERSION}<br>"
                "Edit People, Projects, Events, and Jobs for the "
                "Radiant Center for Remote Sensing website, then "
                "publish to the NAU server and to GitHub (main + archive). "
                "Other users see your changes on their next workspace sync."
                f"<br><br>Workspace: <code>{get_workspace().root}</code>"
                f"<br>Releases: <a href='{RELEASES_URL}'>{RELEASES_URL}</a>"
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

        # Route through the workspace bootstrap page. It will do a
        # quick pull if the workspace is already healthy or a fresh
        # clone if not. Even when the workspace is valid we go via
        # this page so the user always sees the "syncing..." progress
        # and starts from up-to-date data.
        self._workspace.start(token=token)
        self._stack.setCurrentIndex(PAGE_WORKSPACE)

    def _on_workspace_ready(self, _path) -> None:
        # Re-confirm the workspace before we surface the dashboard,
        # so a partial clone or pull failure can't slip through.
        if not is_valid_workspace(get_workspace().root):
            self._status.showMessage(
                "Workspace is not valid; please sign out and retry."
            )
            return
        self._dashboard.refresh_summary()
        self._stack.setCurrentIndex(PAGE_DASHBOARD)
        # Eagerly load the domain pages so the user never sees an
        # empty list when they click through.
        self._people.refresh()
        self._projects.refresh()
        self._events.refresh()
        self._jobs.refresh()

        # Now that we have a healthy workspace AND a valid token,
        # kick off the background sync so other users' publishes
        # land here automatically.
        self._sync_manager.start(token_provider=token_store.load_token)
        self._sync_now_action.setEnabled(True)

    def _goto_dashboard(self) -> None:
        # Re-load summary in case domain pages changed something.
        self._dashboard.refresh_summary()
        # Returning from Publish is a good moment to re-check NAU
        # reachability - the user may have just mounted the share.
        self._nau_indicator.refresh()
        self._stack.setCurrentIndex(PAGE_DASHBOARD)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._sync_manager.stop()
        self._sync_indicator.stop()
        self._nau_indicator.stop()
        super().closeEvent(event)

    def _sign_out(self) -> None:
        # Stop the background sync first so it can't fire a network
        # request with a stale token after we wipe the keyring.
        self._sync_manager.stop()
        self._sync_now_action.setEnabled(False)
        token_store.clear_token()
        self._access = None
        self._status.showMessage("Signed out.")
        self._sign_out_action.setEnabled(False)
        self._login.reset()
        self._stack.setCurrentIndex(PAGE_LOGIN)

    # ---- publish / sync coordination --------------------------------------

    def _on_publish_started(self) -> None:
        # Block the periodic sync so it cannot race the push.
        self._sync_manager.pause("publish")

    def _on_publish_finished(self) -> None:
        self._sync_manager.resume("publish")
        # Refresh local refs immediately so the indicator updates and
        # the dashboard reflects the just-pushed state.
        self._sync_manager.sync_now()

    def _on_background_sync_finished(self, result) -> None:
        # Only refresh on-screen data when the sync actually advanced
        # the workspace, otherwise we needlessly re-read manifests
        # every five minutes.
        if not getattr(result, "updated", False):
            return
        log.info("Background sync updated workspace; refreshing pages.")
        self._dashboard.refresh_summary()
        self._people.refresh()
        self._projects.refresh()
        self._events.refresh()
        self._jobs.refresh()

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
