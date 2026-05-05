"""Static configuration for the Radiant Content GUI.

Anything that must be customized per-deployment lives here. Only the
GitHub OAuth Client ID is allowed to be overridden via the
``RADIANT_GUI_GITHUB_CLIENT_ID`` env var so that a developer can swap
in their own OAuth App during testing without editing this file.

Per the plan, the Client ID is for a *public* GitHub OAuth App with
Device Flow enabled, so embedding it in source is fine; there is no
client secret involved.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# GitHub OAuth (Device Flow)
# ---------------------------------------------------------------------------

# Public Client ID for the registered GitHub OAuth App. Override with
# the env var below for local testing of a different app. The default
# placeholder must be replaced before the first real release - see
# gui/README.md for the one-time registration steps.
GITHUB_OAUTH_CLIENT_ID: Final[str] = os.environ.get(
    "RADIANT_GUI_GITHUB_CLIENT_ID",
    "Iv1.PLACEHOLDER_REPLACE_ME",
)

# OAuth scope: needs full repo access so the user can push to the
# private gh repo and the access check can read repo permissions.
GITHUB_OAUTH_SCOPE: Final[str] = "repo"

# The repo that gates access. Only users with push permission on this
# repo are allowed past the login screen.
GITHUB_REPO_OWNER: Final[str] = "elliottmkinsley"
GITHUB_REPO_NAME: Final[str] = "website-GUI-test"
GITHUB_REPO_FULL: Final[str] = f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"

# Branch that snapshots are pushed to on every Publish.
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
# Paths inside the working repo.
# ---------------------------------------------------------------------------

# When the GUI is run with ``python -m gui`` from the repo root, the
# repo root resolves to the parent directory of this file's package.
# The plan calls for the GUI living *inside* the website repo, so this
# is the canonical way to get the working tree.
GUI_PACKAGE_DIR: Final[Path] = Path(__file__).resolve().parent
REPO_ROOT: Final[Path] = GUI_PACKAGE_DIR.parent

# The four manifests.
PEOPLE_MANIFEST: Final[Path] = REPO_ROOT / "People" / "manifest.json"
PROJECTS_MANIFEST: Final[Path] = REPO_ROOT / "Projects" / "manifest.json"
EVENTS_MANIFEST: Final[Path] = REPO_ROOT / "Events" / "manifest.json"
JOBS_MANIFEST: Final[Path] = REPO_ROOT / "Jobs" / "manifest.json"

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

# Image folders.
IMAGES_PEOPLE: Final[Path] = REPO_ROOT / "Images" / "People"
IMAGES_PEOPLE_VARIANTS_CARD: Final[Path] = IMAGES_PEOPLE / "variants" / "card"
IMAGES_PEOPLE_VARIANTS_TEAM: Final[Path] = IMAGES_PEOPLE / "variants" / "team"
IMAGES_NEWS: Final[Path] = REPO_ROOT / "Images" / "News"
IMAGES_EVENTS: Final[Path] = REPO_ROOT / "Images" / "Events"

# Asset version + counter targets.
SITE_CONFIG_JS: Final[Path] = REPO_ROOT / "JS" / "site-config.js"
INDEX_HTML: Final[Path] = REPO_ROOT / "index.html"

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
