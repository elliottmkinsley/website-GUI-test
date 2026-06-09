"""Single source of truth for the on-disk Radiant website working tree.

Before the GUI was packaged as a standalone application, the path to
the website repo was computed at module-import time as
``Path(__file__).resolve().parent.parent`` - i.e. "two folders up
from this file". That assumption is only valid when the GUI is run
``python -m gui`` from inside the website checkout. Inside a frozen
PyInstaller bundle the same expression resolves to
``dist/RadiantContentGUI/_internal/...``, which contains no website
data at all.

This module replaces the constants with a runtime-resolvable
``Workspace`` value:

* On a developer machine (running from source), ``default_workspace_root()``
  auto-detects the in-repo checkout so iteration is unchanged.
* On an end-user machine (the frozen ``.exe``), it points at
  ``<app-data>/Radiant Center for Remote Sensing/Radiant Content GUI/workspace``
  which is auto-cloned on first launch by ``gui.repo.clone``.
* In either case the workspace can be overridden via the
  ``RADIANT_GUI_WORKSPACE`` environment variable - useful when a
  developer wants to test against a throwaway checkout.

All ``repo/`` and ``deploy/`` modules read paths via :func:`get_workspace`;
they no longer import path constants from :mod:`gui.config`.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

log = logging.getLogger(__name__)

# Highest-priority override. Set this to point the GUI at an arbitrary
# website checkout regardless of where the binary lives.
WORKSPACE_ENV_VAR: Final[str] = "RADIANT_GUI_WORKSPACE"

# Folder name we create under ``user_data_dir()`` to hold the
# auto-cloned working copy.
WORKSPACE_DIR_NAME: Final[str] = "workspace"

# Files we expect to find in a valid Radiant website checkout. Used
# by source-tree auto-detection and by ``is_valid_workspace`` in
# :mod:`gui.repo.clone`.
_WORKSPACE_MARKER_FILES: Final[tuple[str, ...]] = ("index.html",)

# Qt org / app names mirror what ``gui/app.py`` sets on QApplication
# so the user-data path is stable whether or not Qt is initialised
# yet (e.g. inside unit tests).
_ORG_NAME: Final[str] = "Radiant Center for Remote Sensing"
_APP_NAME: Final[str] = "Radiant Content GUI"


# ---------------------------------------------------------------------------
# Workspace dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Workspace:
    """Filesystem layout for one Radiant website working tree.

    Every workspace-relative path used by the GUI is derived from
    :attr:`root`. Construct via :func:`get_workspace` rather than
    instantiating directly so callers always see the singleton.
    """

    root: Path

    # ---- manifests ----
    @property
    def people_manifest(self) -> Path:
        return self.root / "People" / "manifest.json"

    @property
    def projects_manifest(self) -> Path:
        return self.root / "Projects" / "manifest.json"

    @property
    def events_manifest(self) -> Path:
        return self.root / "Events" / "manifest.json"

    @property
    def jobs_manifest(self) -> Path:
        return self.root / "Jobs" / "manifest.json"

    # ---- image folders ----
    @property
    def images_people(self) -> Path:
        return self.root / "Images" / "People"

    @property
    def images_people_variants_card(self) -> Path:
        return self.images_people / "variants" / "card"

    @property
    def images_people_variants_team(self) -> Path:
        return self.images_people / "variants" / "team"

    @property
    def images_news(self) -> Path:
        return self.root / "Images" / "News"

    @property
    def images_events(self) -> Path:
        return self.root / "Images" / "Events"

    # ---- HTML / JS targets the counter + cache-buster touch ----
    @property
    def site_config_js(self) -> Path:
        return self.root / "JS" / "site-config.js"

    @property
    def index_html(self) -> Path:
        return self.root / "index.html"

    # ---- predicates ----
    def is_present(self) -> bool:
        """``True`` if ``root`` looks like a real website checkout."""
        return all((self.root / m).exists() for m in _WORKSPACE_MARKER_FILES)


# ---------------------------------------------------------------------------
# User-data resolution
# ---------------------------------------------------------------------------


def _platform_data_dir() -> Path:
    """Pure-Python AppData resolution that does not require Qt.

    Used as a fallback when ``QStandardPaths`` is not yet available
    (e.g. during early app startup or in unit tests).
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(
            Path.home() / "AppData" / "Roaming"
        )
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(
            Path.home() / ".local" / "share"
        )
    return Path(base) / _ORG_NAME / _APP_NAME


def user_data_dir() -> Path:
    """Return the per-user application data directory for this app.

    Prefers Qt's resolution (which is what QSettings and other Qt
    facilities will use), falling back to a pure-Python computation
    when Qt is not initialised yet.
    """
    try:
        from PySide6.QtCore import QCoreApplication, QStandardPaths
    except Exception:  # noqa: BLE001 - PySide6 missing or broken
        return _platform_data_dir()

    if QCoreApplication.instance() is None:
        return _platform_data_dir()

    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    if base:
        return Path(base)
    return _platform_data_dir()


# ---------------------------------------------------------------------------
# Default-workspace resolution
# ---------------------------------------------------------------------------


def _has_workspace_markers(path: Path) -> bool:
    return all((path / m).exists() for m in _WORKSPACE_MARKER_FILES)


def _source_tree_workspace() -> Path | None:
    """If we are running from a source checkout that contains the
    website data, return its root. Otherwise return ``None``."""
    if getattr(sys, "frozen", False):
        return None
    # ``Path(__file__).resolve().parent.parent`` is the directory that
    # contains the ``gui/`` package - i.e. the website checkout when
    # the GUI lives at ``<repo>/gui/``.
    parent = Path(__file__).resolve().parent.parent
    if _has_workspace_markers(parent):
        return parent
    return None


def default_workspace_root() -> Path:
    """Resolve the workspace root using the documented precedence.

    Order:

      1. ``RADIANT_GUI_WORKSPACE`` env var (developer override).
      2. The source-tree parent of the ``gui/`` package, if it
         contains the website marker files and we are not running
         frozen.
      3. ``user_data_dir() / "workspace"`` - the auto-clone location.
    """
    override = os.environ.get(WORKSPACE_ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()

    source = _source_tree_workspace()
    if source is not None:
        return source

    return user_data_dir() / WORKSPACE_DIR_NAME


# ---------------------------------------------------------------------------
# Singleton accessors
# ---------------------------------------------------------------------------


_current: Workspace | None = None


def get_workspace() -> Workspace:
    """Return the currently-active :class:`Workspace`.

    On first call the workspace is computed from
    :func:`default_workspace_root`. Subsequent calls return the same
    instance until :func:`set_workspace` is called (typically by the
    workspace-bootstrap UI after a successful clone).
    """
    global _current
    if _current is None:
        _current = Workspace(root=default_workspace_root())
    return _current


def set_workspace(root: Path | str | None) -> Workspace:
    """Override the active workspace.

    Pass ``None`` to forget the current value so the next
    :func:`get_workspace` call re-runs the default resolution.
    """
    global _current
    if root is None:
        _current = None
        return get_workspace()
    resolved = Path(root).expanduser().resolve()
    _current = Workspace(root=resolved)
    log.info("Workspace root set to %s", resolved)
    return _current


__all__ = [
    "WORKSPACE_DIR_NAME",
    "WORKSPACE_ENV_VAR",
    "Workspace",
    "default_workspace_root",
    "get_workspace",
    "set_workspace",
    "user_data_dir",
]
