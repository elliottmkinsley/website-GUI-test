"""Per-user GUI settings, persisted via ``QSettings``.

``QSettings`` chooses the native storage backend for each OS:
* Windows: ``HKEY_CURRENT_USER\\Software\\<Org>\\<App>``
* macOS:   ``~/Library/Preferences/<bundle>.plist``
* Linux:   ``~/.config/<Org>/<App>.conf``

This module is the *only* place that knows the storage key names so we
can rename them later without grepping the UI code.

The module is safe to import without a running ``QApplication`` - we
pass the organization/app names explicitly to ``QSettings`` so it does
not have to read them off the global app instance.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

# These two strings must match what ``gui/app.py`` passes to the
# QApplication so per-user settings written through either route end
# up at the same location on disk.
SETTINGS_ORG = "Radiant Center for Remote Sensing"
SETTINGS_APP = "Radiant Content GUI"

KEY_GITHUB_CLIENT_ID = "github/client_id"


def _settings() -> QSettings:
    return QSettings(
        QSettings.Format.NativeFormat,
        QSettings.Scope.UserScope,
        SETTINGS_ORG,
        SETTINGS_APP,
    )


# ---------------------------------------------------------------------------
# GitHub OAuth Client ID
# ---------------------------------------------------------------------------


def get_github_client_id() -> str:
    """Return the stored Client ID, or an empty string if unset."""
    value = _settings().value(KEY_GITHUB_CLIENT_ID, "", str)
    return (value or "").strip()


def set_github_client_id(value: str) -> None:
    s = _settings()
    s.setValue(KEY_GITHUB_CLIENT_ID, value.strip())
    s.sync()


def clear_github_client_id() -> None:
    s = _settings()
    s.remove(KEY_GITHUB_CLIENT_ID)
    s.sync()
