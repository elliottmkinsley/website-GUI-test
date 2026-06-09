"""Static configuration for the Radiant Content GUI.

Anything that must be customised per-deployment lives here. Only the
GitHub OAuth Client ID is allowed to be overridden via the
``RADIANT_GUI_GITHUB_CLIENT_ID`` env var so that a developer can swap
in their own OAuth App during testing without editing this file.

Per the plan, the Client ID is for a *public* GitHub OAuth App with
Device Flow enabled, so embedding it in source is fine; there is no
client secret involved.

Filesystem paths for the website working tree are NOT defined here.
They depend on whether the GUI is running from a developer source
checkout or a packaged ``.exe``, so they are resolved at runtime via
:mod:`gui.workspace` (see ``get_workspace()``).
"""

from __future__ import annotations

import os
import sys
from typing import Final

# ---------------------------------------------------------------------------
# GitHub OAuth (Device Flow)
# ---------------------------------------------------------------------------

# Optional shipped default - leave empty in distributed builds so the
# first-run GUI Setup screen is the canonical way to configure the
# Client ID. A developer can hard-code a default here for their own
# local testing if they really want to, but the GUI Setup flow will
# still take priority once the user enters a value (it gets stored in
# QSettings, see ``gui/settings.py``).
GITHUB_OAUTH_CLIENT_ID_DEFAULT: Final[str] = ""

# Env-var override - lets a developer point the app at a different
# OAuth App without touching code or the GUI. Highest priority.
GITHUB_OAUTH_CLIENT_ID_ENV_VAR: Final[str] = "RADIANT_GUI_GITHUB_CLIENT_ID"

# Substrings that signal "not really configured" - any resolved value
# starting with one of these is treated as missing.
_PLACEHOLDER_PREFIXES: Final[tuple[str, ...]] = (
    "Iv1.PLACEHOLDER",
    "REPLACE_ME",
)


def resolve_github_client_id() -> str:
    """Return the active GitHub OAuth Client ID.

    Resolution order (first non-empty, non-placeholder wins):
      1. ``RADIANT_GUI_GITHUB_CLIENT_ID`` env var
      2. Value the user entered through the GUI Setup screen
         (persisted via ``QSettings`` in ``gui/settings.py``)
      3. ``GITHUB_OAUTH_CLIENT_ID_DEFAULT`` from this module

    Returns an empty string if nothing is configured - the caller
    should then prompt the user (Login + Publish do this).
    """
    env_value = (os.environ.get(GITHUB_OAUTH_CLIENT_ID_ENV_VAR) or "").strip()
    if env_value and not env_value.startswith(_PLACEHOLDER_PREFIXES):
        return env_value
    # Lazy import to avoid pulling Qt into this module's import graph
    # for headless callers.
    try:
        from gui.settings import get_github_client_id

        stored = get_github_client_id()
    except Exception:  # noqa: BLE001 - QSettings/Qt unavailable
        stored = ""
    if stored and not stored.startswith(_PLACEHOLDER_PREFIXES):
        return stored
    default = (GITHUB_OAUTH_CLIENT_ID_DEFAULT or "").strip()
    if default and not default.startswith(_PLACEHOLDER_PREFIXES):
        return default
    return ""


def is_github_client_id_configured() -> bool:
    return bool(resolve_github_client_id())


# OAuth scope: needs full repo access so the user can push to the
# private gh repo and the access check can read repo permissions.
GITHUB_OAUTH_SCOPE: Final[str] = "repo"

# The repo that gates access. Only users with push permission on this
# repo are allowed past the login screen.
GITHUB_REPO_OWNER: Final[str] = "elliottmkinsley"
GITHUB_REPO_NAME: Final[str] = "website-GUI-test"
GITHUB_REPO_FULL: Final[str] = f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"

# Branch GUI users clone, pull from, and commit their content edits to.
# Every successful Publish lands here so other GUI users see the change
# on their next sync.
MAIN_BRANCH: Final[str] = "main"

# Branch that snapshots are also pushed to on every Publish - keeps a
# per-publish history independent of main's normal commit history.
ARCHIVE_BRANCH: Final[str] = "archive"

# keyring service identifier - all GUI tokens live under this name.
KEYRING_SERVICE: Final[str] = "radiant-content-gui"
KEYRING_TOKEN_KEY: Final[str] = "github-oauth-token"


# ---------------------------------------------------------------------------
# NAU SMB share - per-OS default mount paths.
# ---------------------------------------------------------------------------

# These match the share/folder the user described. They can be
# overridden at runtime via the env var ``RADIANT_GUI_SMB_PATH`` for
# users with a non-standard mount setup.
NAU_SMB_PATHS: Final[dict[str, str]] = {
    "win32": r"\\arshares.ucc.nau.edu\Web\radiant.nau.edu",
    "darwin": "/Volumes/radiant.nau.edu",
    "linux": "/www/radiant.nau.edu",
}

NAU_SMB_MOUNT_INSTRUCTIONS: Final[dict[str, str]] = {
    "win32": (
        "Open File Explorer, paste this into the address bar, and sign in "
        "with your NAU credentials when prompted:\n\n"
        r"\\arashres.ucc.nau.edu\Web\radiant.nau.edu"
        "\n\nThen click Retry."
    ),
    "darwin": (
        "In Finder choose Go > Connect to Server (Cmd+K), enter:\n\n"
        "smb://arshares.ucc.nau.edu/Web/radiant.nau.edu\n\n"
        "Sign in with your NAU credentials. Once Finder opens the share, "
        "click Retry."
    ),
    "linux": (
        "Open your file manager and navigate to:\n\n"
        "/www/radiant.nau.edu\n\n"
        "If the path is not available, mount the NAU share via "
        "Files > Other Locations > Connect to Server. Then click Retry."
    ),
}


def nau_smb_default_path() -> str:
    """Return the default SMB mount path for the current OS."""
    override = os.environ.get("RADIANT_GUI_SMB_PATH")
    if override:
        return override
    return NAU_SMB_PATHS.get(sys.platform, NAU_SMB_PATHS["linux"])


def nau_smb_instructions() -> str:
    """Return the OS-specific mount-help text shown on publish failure."""
    return NAU_SMB_MOUNT_INSTRUCTIONS.get(
        sys.platform, NAU_SMB_MOUNT_INSTRUCTIONS["linux"]
    )


# ---------------------------------------------------------------------------
# Domain configuration that has nothing to do with the workspace path.
# ---------------------------------------------------------------------------

# The People sub-folders (six groups) mapped to their manifest keys.
# Order here matches the order shown in the GUI's section dropdown.
PEOPLE_GROUPS: Final[list[tuple[str, str, str]]] = [
    # (manifest_key, display_label, sub_folder_under_People/)
    ("leadership", "Leadership", "Leadership"),
    ("faculty", "Core Researchers", "Core Researchers"),
    ("affiliation", "Affiliate Researchers", "Affiliation"),
    ("staff", "Staff", "Staff"),
    ("postdocs", "Postdoctoral Scholars", "Postdoctoral Scholars"),
    ("graduate", "Graduate Students & Assistants", "Graduate Students & Assistants"),
]

# WebP variant target dimensions per docs/guides/create-image-variants.md.
WEBP_CARD_SIZE: Final[tuple[int, int]] = (360, 420)
WEBP_CARD_QUALITY: Final[int] = 80
WEBP_TEAM_SIZE: Final[tuple[int, int]] = (600, 720)
WEBP_TEAM_QUALITY: Final[int] = 82

# Files/dirs to skip when copying the working tree to the SMB share.
SMB_IGNORE_PATTERNS: Final[tuple[str, ...]] = (
    ".git",
    ".github",
    ".vscode",
    ".venv",
    "venv",
    "gui",
    "docs",
    "__pycache__",
    "*.pyc",
    ".DS_Store",
    "Thumbs.db",
    ".radiant_publish_test",
)
