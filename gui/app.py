"""QApplication bootstrap.

This module is intentionally tiny - it installs subprocess
hardening, instantiates QApplication, loads the QSS theme, builds
the main window, and starts the event loop. Page wiring happens in
``gui.ui.main_window``.

Special argv handling:

* ``--selftest`` runs a smoke test of all top-level modules and
  exits 0 without ever calling ``app.exec()``. Used by CI and by the
  Inno Setup post-install ``[Run]`` step to surface hidden-import
  failures inside the frozen binary (see packaging playbook §3.1).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# Install GitPython console-flash suppression as early as possible -
# *before* any module that uses GitPython is imported. This means
# importing ``gui.deploy.git_publisher`` / ``gui.repo.clone`` later
# in the import chain already benefits from the patch.
from gui.services import git_safe

git_safe.install()

from gui.ui.main_window import MainWindow  # noqa: E402

THEME_QSS = Path(__file__).resolve().parent / "theme.qss"

log = logging.getLogger(__name__)


def _selftest() -> int:
    """Import every top-level GUI module and exercise QApplication
    construction. Returns 0 on success, non-zero on any failure.

    The goal is to catch PyInstaller hidden-import misses inside the
    frozen ``.exe`` before users see a crash. ``MainWindow`` is
    deliberately *not* built here because its constructor spawns
    background QThreads (workspace pull, NAU indicator) that don't
    have time to settle in a non-event-loop selftest. Module imports
    plus QApplication creation already prove every binary dependency
    is bundled.

    Used both as a CI step and as the Inno Setup post-install
    ``[Run]`` verification step.
    """
    logging.basicConfig(level=logging.WARNING)
    try:
        # Auth subsystem
        import gui.auth.access_check  # noqa: F401
        import gui.auth.device_flow  # noqa: F401
        import gui.auth.token_store  # noqa: F401

        # Data models
        import gui.models.event  # noqa: F401
        import gui.models.job  # noqa: F401
        import gui.models.person  # noqa: F401
        import gui.models.project  # noqa: F401

        # Repo layer
        import gui.repo.cache_buster  # noqa: F401
        import gui.repo.clone  # noqa: F401
        import gui.repo.counters  # noqa: F401
        import gui.repo.entries  # noqa: F401
        import gui.repo.images  # noqa: F401
        import gui.repo.manifest  # noqa: F401
        import gui.repo.paths  # noqa: F401

        # Deploy
        import gui.deploy.git_publisher  # noqa: F401
        import gui.deploy.smb_publisher  # noqa: F401

        # UI - importing these proves PySide6 + its plugin discovery
        # work inside the frozen bundle. We deliberately do NOT
        # construct any of them; instantiation kicks off threads and
        # signals that need a running event loop.
        import gui.ui.dashboard_page  # noqa: F401
        import gui.ui.events_page  # noqa: F401
        import gui.ui.jobs_page  # noqa: F401
        import gui.ui.login_page  # noqa: F401
        import gui.ui.main_window  # noqa: F401
        import gui.ui.people_page  # noqa: F401
        import gui.ui.projects_page  # noqa: F401
        import gui.ui.publish_page  # noqa: F401
        import gui.ui.setup_page  # noqa: F401
        import gui.ui.widgets.image_picker  # noqa: F401
        import gui.ui.widgets.nau_status_indicator  # noqa: F401
        import gui.ui.widgets.reorder_list  # noqa: F401
        import gui.ui.workspace_page  # noqa: F401

        # Exercise QApplication construction (proves Qt plugins are
        # bundled and discoverable). We don't run the event loop.
        app = QApplication.instance() or QApplication([])
        app.setApplicationName("Radiant Content GUI")
        app.setOrganizationName("Radiant Center for Remote Sensing")
    except Exception:  # noqa: BLE001 - we want any failure surfaced
        log.exception("selftest failed")
        return 1
    print("Radiant Content GUI: selftest OK")
    return 0


def run(argv: Sequence[str]) -> int:
    """Entry point used by ``__main__``. Returns the Qt exit code."""
    argv_list = list(argv)
    if any(a == "--selftest" for a in argv_list):
        return _selftest()

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv_list)
    app.setApplicationName("Radiant Content GUI")
    app.setOrganizationName("Radiant Center for Remote Sensing")
    app.setOrganizationDomain("radiant.nau.edu")

    if THEME_QSS.exists():
        app.setStyleSheet(THEME_QSS.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    return app.exec()
