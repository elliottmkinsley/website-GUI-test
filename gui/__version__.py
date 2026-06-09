"""Single source of truth for the application's version string.

CI rewrites this file via :mod:`scripts.stamp_version` immediately
before the release build, so the value committed here only matters
for local dev builds and for the seed of the next release.

The version is also exposed via ``gui.__version__`` (see
:mod:`gui.__init__`) for backward compatibility with anything that
imports it from there. ``packaging/version_info.txt`` (Windows
VERSIONINFO) is regenerated from the same string by the stamp
script so it can never drift.
"""

from __future__ import annotations

import re
from typing import Tuple

__version__: str = "0.1.0"

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def version_tuple() -> Tuple[int, int, int, int]:
    """Return ``(major, minor, patch, 0)``.

    The trailing zero is a build number slot expected by Windows
    ``VS_FIXEDFILEINFO``. We always set it to zero - increments come
    from the patch component instead.
    """
    match = _SEMVER_RE.match(__version__)
    if not match:
        # Defensive fallback - never crash an end-user binary just
        # because of a malformed version string.
        return (0, 0, 0, 0)
    major, minor, patch = (int(g) for g in match.groups())
    return (major, minor, patch, 0)
