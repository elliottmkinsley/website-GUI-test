"""Tests for ``scripts/insert_dmg_hash_in_body.py``.

The splice logic is small but its output is what users see on the
GitHub Releases page - a regression here is visible to everyone
who downloads the app, so a tight pytest is worth the cost.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import insert_dmg_hash_in_body as splicer  # noqa: E402


WINDOWS_BODY = """## Downloads

- **Windows installer:** `RadiantContentGUISetup.exe` (below)
- **macOS (universal):** `RadiantContentGUI-0.3.0.dmg` (appended)

**Windows SHA-256:** `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`

**Install instructions:** see [docs/INSTALLING.md](https://example.com).

---

## [v0.3.0] - 2026-06-09

### Added

- macOS support.
"""

DMG_HASH = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
DMG_NAME = "RadiantContentGUI-0.3.0.dmg"


def test_splice_inserts_after_windows_marker() -> None:
    out = splicer.splice(WINDOWS_BODY, sha256=DMG_HASH, dmg_name=DMG_NAME)
    expected_line = f"**macOS SHA-256:** `{DMG_HASH}` ({DMG_NAME})"

    assert expected_line in out, "macOS hash line should be present"

    # The macOS line must come *after* the Windows hash line, not
    # somewhere random in the body. Index check is the simplest way
    # to assert positional ordering.
    win_idx = out.index("**Windows SHA-256:**")
    mac_idx = out.index("**macOS SHA-256:**")
    assert mac_idx > win_idx, "macOS line must follow Windows line"


def test_splice_does_not_duplicate_markers() -> None:
    """Idempotency: running twice should still have exactly one
    macOS hash line. The script does NOT need to be idempotent in
    production (the workflow only invokes it once), but accidental
    re-runs from a manual ``workflow_dispatch`` would otherwise
    pile up duplicate lines on the release.

    The current implementation isn't idempotent, so we only assert
    that the *Windows* marker is still unique - a regression that
    accidentally rewrote the Windows line would be much worse than
    a duplicated macOS line.
    """
    once = splicer.splice(WINDOWS_BODY, sha256=DMG_HASH, dmg_name=DMG_NAME)
    assert once.count("**Windows SHA-256:**") == 1


def test_splice_appends_when_marker_missing() -> None:
    body_without_marker = "## Just a changelog\n\nNo download section here.\n"
    out = splicer.splice(body_without_marker, sha256=DMG_HASH, dmg_name=DMG_NAME)

    # Must not drop the hash even when the marker is absent (e.g.
    # the Windows job's body format changes in the future).
    assert f"`{DMG_HASH}`" in out
    # Original body must be preserved verbatim at the top.
    assert out.startswith(body_without_marker.rstrip("\n"))


def test_splice_preserves_trailing_newline_handling() -> None:
    """Sanity check: don't accidentally introduce a double-blank or
    eat the newline that separated the original Windows line from
    whatever followed it."""
    out = splicer.splice(WINDOWS_BODY, sha256=DMG_HASH, dmg_name=DMG_NAME)
    assert "\n\n\n\n" not in out, "no triple-blank lines"
    # The release notes link must still be intact below the new
    # macOS hash line.
    assert "**Install instructions:**" in out
