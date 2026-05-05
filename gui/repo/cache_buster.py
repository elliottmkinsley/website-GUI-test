"""Bump ``assetVersion`` in ``JS/site-config.js``.

``CONVENTIONS.md`` allows JSON-only changes to skip cache-buster work,
but recommends bumping ``assetVersion`` in ``site-config.js`` so
visitors immediately see new content. We do that automatically after
every save.

Format: ``YYYY-MM-DD-N``. We bump ``N`` if the date matches today,
otherwise we restart at ``1`` for today's date.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

from gui.config import SITE_CONFIG_JS

log = logging.getLogger(__name__)

# Captures the assetVersion line - allows single or double quotes,
# with or without trailing comma/semicolon.
_ASSET_VERSION_RE = re.compile(
    r'(assetVersion\s*:\s*)(["\'])(\d{4}-\d{2}-\d{2}-\d+)\2'
)


def _next_version(current: str | None) -> str:
    today = date.today().isoformat()  # YYYY-MM-DD
    if current and current.startswith(today + "-"):
        try:
            n = int(current.rsplit("-", 1)[-1])
        except ValueError:
            n = 1
        else:
            n += 1
        return f"{today}-{n}"
    return f"{today}-1"


def bump_asset_version(path: Path = SITE_CONFIG_JS) -> tuple[str, str] | None:
    """Bump ``assetVersion`` in-place. Returns ``(old, new)`` or ``None``
    if no change was made (e.g. file missing)."""
    if not path.exists():
        log.warning("site-config.js not found at %s; skipping bump", path)
        return None
    text = path.read_text(encoding="utf-8")
    match = _ASSET_VERSION_RE.search(text)
    if not match:
        log.warning("assetVersion not found in %s; skipping bump", path)
        return None
    current = match.group(3)
    new = _next_version(current)
    if new == current:
        return None
    new_text = (
        text[: match.start()]
        + f"{match.group(1)}{match.group(2)}{new}{match.group(2)}"
        + text[match.end():]
    )
    path.write_text(new_text, encoding="utf-8")
    return current, new
