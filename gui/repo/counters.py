"""Maintain the hard-coded metric counters embedded in ``index.html``.

The site has three counters in the "Radiant's Impact" panel; only the
"Core Researchers" one is derived from data we own (the ``faculty``
section of ``People/manifest.json``). The other two ("Academic
Disciplines", "Active Grants") are out of scope and left untouched.

We use ``BeautifulSoup`` for safety - regex on HTML is fragile.
``html.parser`` keeps the rest of the file byte-for-byte intact.
"""

from __future__ import annotations

import logging
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

from gui.repo import manifest
from gui.workspace import get_workspace

log = logging.getLogger(__name__)

CORE_RESEARCHERS_LABEL = "Core Researchers"


def _find_metric_value_for_label(soup: BeautifulSoup, label: str):
    """Locate the ``<span class="metric-value">N</span>`` that sits
    immediately before the ``<span class="metric-label">label</span>``
    inside the same ``.metric-box``."""
    for label_span in soup.select("span.metric-label"):
        if label_span.get_text(strip=True) == label:
            box = label_span.find_parent(class_="metric-box")
            if box is None:
                continue
            value_span = box.find("span", class_="metric-value")
            if value_span is not None:
                return value_span
    return None


def update_core_researchers_count(
    *,
    html_path: Path | None = None,
    manifest_path: Path | None = None,
) -> tuple[int, int] | None:
    """Sync the "Core Researchers" metric in ``index.html`` with the
    current length of the manifest's ``faculty`` array.

    Returns ``(old, new)`` if the file was modified, ``None`` if the
    counter was already correct (or could not be found).
    """
    ws = get_workspace()
    if html_path is None:
        html_path = ws.index_html
    if manifest_path is None:
        manifest_path = ws.people_manifest

    if not html_path.exists():
        log.warning("index.html not found at %s; skipping counter update", html_path)
        return None

    new_count = len(manifest.get_section(manifest_path, "faculty"))

    raw = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    target = _find_metric_value_for_label(soup, CORE_RESEARCHERS_LABEL)
    if target is None:
        log.warning(
            "Could not locate the '%s' metric in %s",
            CORE_RESEARCHERS_LABEL,
            html_path,
        )
        return None

    current_text = target.get_text(strip=True)
    try:
        current_value = int(current_text)
    except ValueError:
        log.warning(
            "'%s' metric value is not an integer (%r); refusing to overwrite",
            CORE_RESEARCHERS_LABEL,
            current_text,
        )
        return None

    if current_value == new_count:
        return None

    target.clear()
    target.append(NavigableString(str(new_count)))
    html_path.write_text(str(soup), encoding="utf-8")
    return current_value, new_count
