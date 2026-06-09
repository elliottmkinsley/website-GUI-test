"""Subprocess-flag helpers that suppress Windows console flashes.

Every ``subprocess.Popen`` or ``subprocess.run`` call on Windows pops
a black console window for the duration of the call. With a few git
operations per launch, that's a few flashes per launch - jarring
enough that users will think the app is glitching.

This module centralises the two pieces of magic that prevent the
flash:

* ``hidden_creation_flags()`` returns ``CREATE_NO_WINDOW`` on
  Windows, ``0`` elsewhere.
* ``hidden_startupinfo()`` returns a ``STARTUPINFO`` configured to
  hide any window the child might try to show, ``None`` elsewhere.

Pass *both* into every subprocess invocation. The GitPython monkey-
patch in :mod:`gui.services.git_safe` does this transparently for
the library calls we make at runtime.

The module is a no-op on macOS and Linux, where consoles only spawn
on explicit ``shell=True`` calls anyway.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Optional

# Documented Windows process-creation flag from
# https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags
# Embedded literally so this module has no Windows-only imports.
CREATE_NO_WINDOW = 0x08000000


def hidden_creation_flags() -> int:
    """Return the ``creationflags`` value to pass to ``subprocess``.

    Returns ``CREATE_NO_WINDOW`` on Windows so the child never shows a
    console, and ``0`` everywhere else (no-op).
    """
    if sys.platform == "win32":
        return CREATE_NO_WINDOW
    return 0


def hidden_startupinfo() -> Optional[subprocess.STARTUPINFO]:  # type: ignore[name-defined]
    """Return a ``STARTUPINFO`` configured to hide any subprocess
    window.

    Defence in depth alongside :func:`hidden_creation_flags`: some
    child processes (notably ones launched via ``cmd.exe /c``) ignore
    ``CREATE_NO_WINDOW`` but respect ``STARTF_USESHOWWINDOW``. On
    non-Windows platforms returns ``None``.
    """
    if sys.platform != "win32":
        return None
    info = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
    info.wShowWindow = subprocess.SW_HIDE  # type: ignore[attr-defined]
    return info


__all__ = [
    "CREATE_NO_WINDOW",
    "hidden_creation_flags",
    "hidden_startupinfo",
]
