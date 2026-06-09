"""Publish the working tree to the NAU SMB share.

The detection logic is conservative: we never *try* to connect to the
share ourselves (no SMB libraries) - we just check whether the
already-mounted target path is reachable as a normal filesystem and
writable. Mounting is the user's responsibility (and the OS-specific
instructions are surfaced from ``gui.config.nau_smb_instructions``).

The actual copy is a ``shutil.copytree(..., dirs_exist_ok=True)`` with
an ignore list so the user's local ``gui/``, ``docs/``, ``.git`` etc.
do not pollute the website server.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from gui.config import SMB_IGNORE_PATTERNS, nau_smb_default_path
from gui.workspace import get_workspace

log = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None]


@dataclass
class ProbeResult:
    reachable: bool
    writable: bool
    target: Path
    error: str | None

    @property
    def ok(self) -> bool:
        return self.reachable and self.writable


def probe_reachable(target: Path | None = None) -> bool:
    """Cheap, non-destructive reachability check for the NAU share.

    Returns ``True`` if the target path exists and is a directory we
    can stat. Does NOT perform a write test - use ``probe()`` for
    the full reachable + writable check before publishing. Suitable
    for periodic status-indicator polling because it never touches
    the file system.
    """
    target_path = Path(target) if target else Path(nau_smb_default_path())
    try:
        return target_path.is_dir()
    except OSError:
        return False


def probe(target: Path | None = None) -> ProbeResult:
    """Confirm the share is mounted and writable."""
    target_path = Path(target) if target else Path(nau_smb_default_path())

    if not target_path.exists():
        return ProbeResult(
            reachable=False,
            writable=False,
            target=target_path,
            error=f"The path '{target_path}' does not exist.",
        )
    if not target_path.is_dir():
        return ProbeResult(
            reachable=False,
            writable=False,
            target=target_path,
            error=f"'{target_path}' is not a directory.",
        )
    test = target_path / ".radiant_publish_test"
    try:
        test.write_text("ok", encoding="utf-8")
    except OSError as exc:
        return ProbeResult(
            reachable=True,
            writable=False,
            target=target_path,
            error=f"Path is reachable but write failed: {exc}",
        )
    finally:
        try:
            test.unlink(missing_ok=True)
        except OSError:
            pass
    return ProbeResult(
        reachable=True, writable=True, target=target_path, error=None
    )


def publish(
    target: Path | None = None,
    *,
    repo_root: Path | None = None,
    progress: ProgressCallback | None = None,
) -> Path:
    """Copy the website tree onto the SMB target.

    Returns the resolved target path on success. Raises ``OSError`` /
    ``RuntimeError`` on failure - the caller is expected to surface
    the mount-help dialog if appropriate.
    """
    result = probe(target)
    if not result.ok:
        raise RuntimeError(result.error or "Could not reach the NAU share.")

    target_path = result.target
    source_root = repo_root if repo_root is not None else get_workspace().root
    ignore = shutil.ignore_patterns(*SMB_IGNORE_PATTERNS)

    if progress:
        progress(f"Copying tree to {target_path} ...")

    shutil.copytree(
        source_root,
        target_path,
        dirs_exist_ok=True,
        ignore=ignore,
    )

    if progress:
        progress(f"Done copying to {target_path}.")

    return target_path
