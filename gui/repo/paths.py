"""Path helpers for converting between repo-relative POSIX paths and
filesystem ``Path``s.

The website's manifests use forward-slash, repo-relative strings like
``"People/Core Researchers/kristen-bennett.json"``. The GUI works in
real ``Path`` objects, but always *writes* the manifest using the
POSIX form so the JSON stays portable between Windows and Linux/macOS
collaborators.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path, PurePosixPath

from gui.config import REPO_ROOT


def repo_relative(path: Path) -> str:
    """Return ``path`` as a forward-slash, repo-relative string."""
    return PurePosixPath(path.relative_to(REPO_ROOT)).as_posix()


def from_repo_relative(rel: str) -> Path:
    """Resolve a repo-relative POSIX string to an absolute ``Path``."""
    parts = PurePosixPath(rel).parts
    return REPO_ROOT.joinpath(*parts)


_SLUG_DIACRITIC_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Kebab-case slug as used for entry filenames.

    Strips honorifics like "Dr ", lower-cases, removes diacritics,
    collapses runs of non-alphanumeric chars to a single hyphen.
    """
    normalized = unicodedata.normalize("NFKD", name)
    no_marks = "".join(c for c in normalized if not unicodedata.combining(c))
    lower = no_marks.lower()
    lower = re.sub(r"^(dr|prof|mr|ms|mrs|mx)\.?\s+", "", lower)
    slug = _SLUG_DIACRITIC_RE.sub("-", lower).strip("-")
    return slug or "entry"


_FILESAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def filesafe_basename(name: str) -> str:
    """Like ``slugify`` but preserves case and underscores.

    Used for image basenames where the existing repo style is
    ``First_Last`` rather than ``first-last``.
    """
    cleaned = _FILESAFE_RE.sub("_", name).strip("_")
    return cleaned or "image"
