"""Subprocess-hardening tests (playbook §3.1).

These tests prove that:

* ``hidden_creation_flags()`` returns ``CREATE_NO_WINDOW`` on Windows
  and ``0`` everywhere else.
* ``hidden_startupinfo()`` is a no-op on non-Windows and a proper
  ``STARTUPINFO`` on Windows.
* The GitPython monkey-patch in :mod:`gui.services.git_safe` replaces
  ``git.cmd.Popen`` with a subclass that adds the hidden flags.

The Windows-specific assertions are guarded with ``sys.platform``
checks so the tests pass on macOS/Linux CI too.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from gui.services import _proc, git_safe


def test_hidden_creation_flags_includes_create_no_window_on_windows() -> None:
    flags = _proc.hidden_creation_flags()
    if sys.platform == "win32":
        assert flags & _proc.CREATE_NO_WINDOW == _proc.CREATE_NO_WINDOW
    else:
        assert flags == 0


def test_hidden_startupinfo_returns_none_off_windows() -> None:
    info = _proc.hidden_startupinfo()
    if sys.platform != "win32":
        assert info is None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only API")
def test_hidden_startupinfo_hides_window_on_windows() -> None:
    info = _proc.hidden_startupinfo()
    assert info is not None
    assert info.dwFlags & subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
    assert info.wShowWindow == subprocess.SW_HIDE  # type: ignore[attr-defined]


def test_git_safe_install_is_idempotent() -> None:
    git_safe.install()
    git_safe.install()


@pytest.mark.skipif(sys.platform != "win32", reason="GitPython patch is Windows-only")
def test_git_safe_replaces_git_popen_class() -> None:
    """After install, ``git.cmd.Popen`` is no longer the stock
    ``subprocess.Popen`` - it's a subclass that injects the hidden
    flags before forwarding to ``subprocess.Popen.__init__``."""
    git_safe.install()
    import git.cmd as git_cmd

    assert git_cmd.Popen is not subprocess.Popen
    assert issubclass(git_cmd.Popen, subprocess.Popen)
    assert git_cmd.Popen.__name__ == "_HiddenPopen"


@pytest.mark.skipif(sys.platform != "win32", reason="GitPython patch is Windows-only")
def test_git_safe_injects_creation_flag_on_real_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: spawn a child via the patched class and verify
    the kwargs reaching ``subprocess.Popen.__init__`` include
    ``CREATE_NO_WINDOW``. We instrument at the lowest level
    (``subprocess.Popen.__init__``) so the assertion measures the
    actual behaviour rather than test scaffolding."""
    git_safe.install()
    import git.cmd as git_cmd

    seen: dict = {}
    original_init = subprocess.Popen.__init__

    def _spy(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        seen.update(kwargs)
        return original_init(self, *args, **kwargs)

    monkeypatch.setattr(subprocess.Popen, "__init__", _spy)

    p = git_cmd.Popen(
        [sys.executable, "-c", "import sys; sys.exit(0)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    p.communicate(timeout=10)

    flags = seen.get("creationflags", 0)
    assert flags & _proc.CREATE_NO_WINDOW == _proc.CREATE_NO_WINDOW
