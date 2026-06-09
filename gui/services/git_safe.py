"""Suppress the ``git.exe`` console window flash on Windows.

``GitPython`` shells out to the system ``git`` binary for every
operation. On Windows that means a black console window flashes for
the duration of each call - very visible during the workspace pull
on every Dashboard entry, and even worse during the snapshot-and-
push flow in :mod:`gui.deploy.git_publisher`.

The fix is to monkey-patch the ``subprocess.Popen`` symbol that
``git.cmd`` imports so it always passes ``creationflags=CREATE_NO_WINDOW``
plus a hidden ``STARTUPINFO``. This module performs the patch at
import time. ``gui/app.py`` imports it once near the top of
``run()`` so the patch is in effect before any GitPython call is
made.

The patch is a no-op on macOS and Linux.
"""

from __future__ import annotations

import logging
import subprocess
import sys

from gui.services._proc import hidden_creation_flags, hidden_startupinfo

log = logging.getLogger(__name__)

_patched = False


def install() -> None:
    """Install the Popen patch. Idempotent."""
    global _patched
    if _patched:
        return
    if sys.platform != "win32":
        # Nothing to suppress on non-Windows platforms.
        _patched = True
        return

    try:
        import git.cmd as git_cmd
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "GitPython not importable; subprocess hardening skipped: %s", exc
        )
        return

    original_popen = git_cmd.Popen

    creation_flags = hidden_creation_flags()
    startupinfo = hidden_startupinfo()

    class _HiddenPopen(original_popen):  # type: ignore[misc, valid-type]
        """Drop-in ``subprocess.Popen`` that always hides its console."""

        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            kwargs.setdefault("creationflags", 0)
            kwargs["creationflags"] = (kwargs["creationflags"] or 0) | creation_flags
            if startupinfo is not None and kwargs.get("startupinfo") is None:
                kwargs["startupinfo"] = startupinfo
            super().__init__(*args, **kwargs)

    git_cmd.Popen = _HiddenPopen  # type: ignore[assignment]
    # GitPython references ``Popen`` via ``subprocess.Popen`` in some
    # internal call sites; rebind defensively. We do NOT touch the
    # global ``subprocess.Popen`` symbol because other libraries may
    # depend on its exact behaviour.
    _patched = True
    log.debug(
        "GitPython Popen patched with creationflags=0x%x", creation_flags
    )


__all__ = ["install"]
