"""Tests for :mod:`gui.services.sync_manager`.

The tests stub :func:`gui.repo.clone.pull_workspace` so they never
touch git, the filesystem, or the network. ``pytest-qt`` provides
the ``qtbot`` fixture that runs the Qt event loop so signals,
timers, and ``QThread`` work as in the real app.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from gui.repo.clone import PullResult
from gui.services import sync_manager as sm
from gui.services.sync_manager import SyncManager, SyncResult


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Make ``sync_manager.is_valid_workspace`` always say yes and
    ``get_workspace().root`` return our temp path, so sync_now does
    not bail out before reaching the (stubbed) pull."""
    class _FakeWorkspace:
        root = tmp_path

    monkeypatch.setattr(sm, "is_valid_workspace", lambda _path: True)
    monkeypatch.setattr(sm, "get_workspace", lambda: _FakeWorkspace())
    return tmp_path


@pytest.fixture
def stub_pull(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Replace ``pull_workspace`` with a controllable stub.

    The returned dict carries:
      * ``call_count``: int incremented on every invocation
      * ``next_result``: ``PullResult`` returned by the next call
      * ``raise_next``: exception to raise instead of returning (or None)
    """
    state: dict = {
        "call_count": 0,
        "next_result": PullResult(updated=False, message="Up to date"),
        "raise_next": None,
    }

    def _stub(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        state["call_count"] += 1
        exc = state["raise_next"]
        if exc is not None:
            state["raise_next"] = None
            raise exc
        return state["next_result"]

    monkeypatch.setattr(sm, "pull_workspace", _stub)
    return state


def _wait_for_finished(qtbot, manager: SyncManager, timeout_ms: int = 5000) -> SyncResult:
    """Spin until SyncManager emits ``syncFinished`` (or raise on timeout)."""
    with qtbot.waitSignal(manager.syncFinished, timeout=timeout_ms) as blocker:
        pass
    return blocker.args[0]


# ---------------------------------------------------------------------------
# Lifecycle and basic dispatch
# ---------------------------------------------------------------------------


def test_sync_now_invokes_pull_and_emits_result(
    qtbot, fake_workspace: Path, stub_pull: dict
) -> None:
    stub_pull["next_result"] = PullResult(
        updated=True, message="Pulled main from origin."
    )
    manager = SyncManager()
    qtbot.addWidget = None  # SyncManager isn't a QWidget; suppress accidental misuse
    manager.start(token_provider=lambda: "token-abc")

    with qtbot.waitSignal(manager.syncStarted, timeout=2000):
        manager.sync_now()
    result: SyncResult = _wait_for_finished(qtbot, manager)

    assert stub_pull["call_count"] == 1
    assert result.success is True
    assert result.updated is True
    assert "Pulled main" in result.message
    assert manager.last_result() is result

    manager.stop()


def test_pull_exception_becomes_failed_sync_result(
    qtbot, fake_workspace: Path, stub_pull: dict
) -> None:
    stub_pull["raise_next"] = RuntimeError("boom")
    manager = SyncManager()
    manager.start(token_provider=lambda: "token-abc")

    manager.sync_now()
    result = _wait_for_finished(qtbot, manager)

    assert result.success is False
    assert "boom" in result.message
    manager.stop()


def test_sync_now_is_noop_when_not_started(
    qtbot, fake_workspace: Path, stub_pull: dict
) -> None:
    manager = SyncManager()
    # Never call start(); sync_now should silently no-op.
    manager.sync_now()
    qtbot.wait(50)
    assert stub_pull["call_count"] == 0
    manager.stop()


def test_sync_now_is_noop_without_token_provider(
    qtbot, fake_workspace: Path, stub_pull: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = SyncManager()
    # Skip start() so token_provider stays None; mark running manually
    # via start() with a None-returning provider to differentiate "no
    # provider" from "provider returned None token".
    manager._token_provider = None  # type: ignore[attr-defined]
    manager._running = True  # type: ignore[attr-defined]
    manager.sync_now()
    qtbot.wait(50)
    assert stub_pull["call_count"] == 0
    manager.stop()


# ---------------------------------------------------------------------------
# Pause / resume reference counting
# ---------------------------------------------------------------------------


def test_pause_and_resume_are_reference_counted(
    qtbot, fake_workspace: Path, stub_pull: dict
) -> None:
    manager = SyncManager()
    manager.start(token_provider=lambda: "t")
    assert not manager.is_paused()

    manager.pause("publish")
    manager.pause("dialog")
    assert manager.is_paused()
    assert set(manager.pause_reasons()) == {"publish", "dialog"}

    manager.resume("publish")
    assert manager.is_paused(), "still paused while 'dialog' guard is active"

    manager.resume("dialog")
    assert not manager.is_paused()
    assert manager.pause_reasons() == ()

    manager.stop()


def test_unbalanced_resume_is_logged_and_ignored(
    qtbot, fake_workspace: Path, stub_pull: dict
) -> None:
    manager = SyncManager()
    manager.start(token_provider=lambda: "t")
    manager.pause("publish")
    # Spurious resume for an unknown reason - should NOT pop "publish".
    manager.resume("never-paused")
    assert manager.is_paused()
    assert manager.pause_reasons() == ("publish",)
    manager.resume("publish")
    assert not manager.is_paused()
    manager.stop()


def test_pause_requires_non_empty_reason(qtbot, fake_workspace: Path, stub_pull: dict) -> None:
    manager = SyncManager()
    with pytest.raises(ValueError):
        manager.pause("")
    manager.stop()


# ---------------------------------------------------------------------------
# Coalescing
# ---------------------------------------------------------------------------


def test_sync_now_is_coalesced_while_a_sync_is_in_flight(
    qtbot, fake_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two rapid sync_now calls must result in ONE pull. We hold the
    pull inside the worker thread by blocking on a threading Event
    so the second call lands while the first is still running."""
    import threading

    release = threading.Event()
    calls = {"count": 0}

    def _slow_pull(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        if not release.wait(timeout=2.0):
            raise TimeoutError("Test release event never fired")
        return PullResult(updated=False, message="ok")

    monkeypatch.setattr(sm, "pull_workspace", _slow_pull)

    manager = SyncManager()
    manager.start(token_provider=lambda: "t")
    manager.sync_now()
    # Second call should be coalesced - worker is still blocked.
    manager.sync_now()
    manager.sync_now()
    # Let the worker finish.
    release.set()
    _wait_for_finished(qtbot, manager)

    assert calls["count"] == 1
    manager.stop()


# ---------------------------------------------------------------------------
# Timer-driven path
# ---------------------------------------------------------------------------


def test_timer_tick_drives_a_sync(
    qtbot, fake_workspace: Path, stub_pull: dict
) -> None:
    """With a tiny interval, the QTimer should fire on its own and
    trigger a pull without anyone calling sync_now."""
    manager = SyncManager()
    manager.start(token_provider=lambda: "t", interval_ms=1_000)
    # Wait through one tick (interval is clamped to >=1000 ms).
    _wait_for_finished(qtbot, manager, timeout_ms=5000)
    assert stub_pull["call_count"] >= 1
    manager.stop()


def test_timer_does_not_tick_while_paused(
    qtbot, fake_workspace: Path, stub_pull: dict
) -> None:
    manager = SyncManager()
    manager.start(token_provider=lambda: "t", interval_ms=1_000)
    manager.pause("publish")
    # Wait longer than one tick and assert no pull happened.
    qtbot.wait(1_500)
    assert stub_pull["call_count"] == 0
    manager.resume("publish")
    _wait_for_finished(qtbot, manager, timeout_ms=5000)
    assert stub_pull["call_count"] >= 1
    manager.stop()


# ---------------------------------------------------------------------------
# Stop semantics
# ---------------------------------------------------------------------------


def test_stop_is_idempotent_and_safe_without_start(
    qtbot, fake_workspace: Path, stub_pull: dict
) -> None:
    manager = SyncManager()
    manager.stop()
    manager.stop()
    # Now start + stop should still work.
    manager.start(token_provider=lambda: "t")
    manager.stop()
    manager.stop()
